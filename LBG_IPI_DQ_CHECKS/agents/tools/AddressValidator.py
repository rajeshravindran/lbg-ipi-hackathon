import sqlite3
from pydantic import BaseModel, Field
from typing import List, Optional
from postal.parser import parse_address
from google.cloud import bigquery
from pathlib import Path
import re
import sys
import random

try:
    # This works when running through the Agent (adk run)
    from .schemas import CustomerAddressDQ, address_not_found_response
    from .createAddressDB import initialize_database
except (ImportError, ValueError):
    # This works when running 'python AddressValidator.py' directly
    # We add the current directory to sys.path to find the siblings
    current_dir = Path(__file__).resolve().parent
    if str(current_dir) not in sys.path:
        sys.path.append(str(current_dir))
    
    from schemas import CustomerAddressDQ, address_not_found_response
    from createAddressDB import initialize_database

class AddressAgent:
    def __init__(self, db_path='uk_validation.db'):
        script_dir = Path(__file__).resolve().parent
        base_dir = script_dir.parent

        db_filename = Path(db_path).name 
        
        # 2. Force it to be an absolute Path object inside the Data folder
        self.db_path = base_dir / "Data" / db_filename

        self.header_path = base_dir / "Data/Doc/OS_Open_Names_Header.csv"
        self.data_path = base_dir / "Data/csv"

        # Ensure the directory for the DB exists before trying to open/create it
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        print(db_path)
       
        if not self.db_path.exists():
            print(f"Database not found at {self.db_path}. Initializing...")
            initialize_database(
                header_path=self.header_path, 
                data_folder_path=self.data_path, 
                db_path=self.db_path
            ) 
        else:
            print(f"Using existing database at {self.db_path}") 

    def _is_duplicate(self, use_input: str) -> bool:
        _is_duplicate = random.random() < 0.20
        return _is_duplicate

    def validate(self, user_input: str) -> CustomerAddressDQ:
        # 1. Parse with libpostal
        parsed = parse_address(user_input)
        addr = {label: value.upper() for value, label in parsed}
        
        user_area_context = addr.get('city') or addr.get('suburb') or addr.get('state_district')
        
        # Component assembly for search
        geo_labels = ['road', 'suburb', 'city', 'neighborhood', 'village', 'hamlet', 'state_district']
        search_components = [val.upper() for val, label in parsed if label in geo_labels]
        search_term = " ".join(search_components).strip()

        if not search_term:
            search_term = user_input.split(',')[0].strip().upper() if "," in user_input else user_input.split()[0].strip().upper()

        postcode_parts = [value.upper() for value, label in parsed if label == 'postcode']
        postcode = " ".join(postcode_parts).strip()
        
        # FIX: Added safety check for empty postcode splits
        input_district = postcode.split()[0] if (postcode and len(postcode.split()) > 0) else None
        
        # 2. Database Search
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        db_match = None
        if search_term:
            if input_district:
                query = "SELECT * FROM os_data WHERE upper(NAME1) LIKE ? AND upper(POSTCODE_DISTRICT) LIKE ? LIMIT 1"
                cursor.execute(query, (f"{search_term}%", f"{input_district}%"))
                db_match = cursor.fetchone()
            
            if not db_match:
                query = "SELECT * FROM os_data WHERE upper(NAME1) = ? LIMIT 1"
                cursor.execute(query, (search_term,))
                db_match = cursor.fetchone()
        conn.close()

        # 3. Validation Logic & Risk Scoring
        is_valid = db_match is not None
        risk_flags = []
        risk_score = 0
        confidence_level = "LOW"
        classification = "UNKNOWN"
        
        if is_valid:
            # Safe access within the is_valid block
            residential_types = ['Postcode', 'Named Road', 'Hamlet', 'Village', 'Other Settlement']
            classification = "RESIDENTIAL" if db_match['LOCAL_TYPE'] in residential_types else "BUSINESS"
            
            db_city = (db_match['POPULATED_PLACE'] or "").upper()
            db_borough = (db_match['DISTRICT_BOROUGH'] or "").upper()
            if user_area_context and not any(loc == user_area_context for loc in [db_city, db_borough] if loc):
                risk_flags.append("GEOGRAPHIC_AREA_MISMATCH")
                risk_score += 40

            # Postcode Patterns
            if re.match(r"^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$", postcode):
                confidence_level = "HIGH"
            elif input_district or (not postcode and db_match['POSTCODE_DISTRICT']):
                risk_flags.append("PARTIAL_POSTCODE_DISTRICT")
                risk_score += 10
                confidence_level = "MEDIUM"
            else:
                risk_flags.append("MISSING_OR_INVALID_POSTCODE")
                risk_score += 30
        else:
            risk_flags.append("ADDRESS_NOT_IN_DATABASE")
            risk_score = 90

        # 4. Final Construction (Safe checks for db_match)
        house_no = addr.get('house_number', '').strip()
        final_road = db_match['NAME1'] if is_valid else search_term
        final_pc = postcode if postcode else (db_match['POSTCODE_DISTRICT'] if is_valid else "UNKNOWN")
        full_std_addr = f"{house_no} {final_road}, {final_pc}".strip(", ").upper()

        is_duplicate = self._is_duplicate(full_std_addr)
        if is_duplicate:
            risk_flags.append('DUPLICATE ADDRESSES TRACKED')
            risk_score = min(risk_score + 30, 100)

        return CustomerAddressDQ(
            is_valid=is_valid,
            standardized_address=full_std_addr,
            classification=classification,
            is_duplicate=is_duplicate,
            populated_place=db_match['POPULATED_PLACE'] if is_valid else None,
            district_borough=db_match['DISTRICT_BOROUGH'] if is_valid else None,
            county=db_match['COUNTY_UNITARY'] if is_valid else None,
            risk_score=min(risk_score, 100),
            risk_flags=risk_flags,
            confidence_level=confidence_level,
            provider_metadata={
                "os_id": db_match['ID'] if is_valid else None,
                "local_type": db_match['LOCAL_TYPE'] if is_valid else "N/A",
                "country": db_match['COUNTRY'] if is_valid else "UK"
            }
        )

    from google.cloud import bigquery
import re
from postal.parser import parse_address

# Assuming CustomerAddressDQ is already imported/defined

def validate_bigquery(self, user_input: str) -> CustomerAddressDQ:
    # --- 1. SETUP BIGQUERY CLIENT ---
    # These should ideally be defined in your class __init__
    project_id = "dbs-data-ai-ai-core"
    dataset_id = "lbg_ipi_digitalwallet"
    table_id = f"{project_id}.{dataset_id}.os_data"
    client = bigquery.Client(project=project_id)

    # --- 2. PARSE WITH LIBPOSTAL ---
    parsed = parse_address(user_input)
    addr = {label: value.upper() for value, label in parsed}
    
    user_area_context = addr.get('city') or addr.get('suburb') or addr.get('state_district')
    
    geo_labels = ['road', 'suburb', 'city', 'neighborhood', 'village', 'hamlet', 'state_district']
    search_components = [val.upper() for val, label in parsed if label in geo_labels]
    search_term = " ".join(search_components).strip()

    if not search_term:
        search_term = user_input.split(',')[0].strip().upper() if "," in user_input else user_input.split()[0].strip().upper()

    postcode_parts = [value.upper() for value, label in parsed if label == 'postcode']
    postcode = " ".join(postcode_parts).strip()
    input_district = postcode.split()[0] if (postcode and len(postcode.split()) > 0) else None
    
    # --- 3. BIGQUERY SEARCH ---
    db_match = None
    if search_term:
        # We use Parameterized Queries for security and performance
        params = [bigquery.ScalarQueryParameter("search_term", "STRING", search_term)]
        
        if input_district:
            # Query 1: Refined search with Postcode District
            query = f"""
                SELECT * FROM `{table_id}` 
                WHERE NAME1 LIKE @search_term_like 
                AND POSTCODE_DISTRICT LIKE @district_like 
                LIMIT 1
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("search_term_like", "STRING", f"{search_term}%"),
                    bigquery.ScalarQueryParameter("district_like", "STRING", f"{input_district}%")
                ]
            )
            query_job = client.query(query, job_config=job_config)
            rows = list(query_job.result())
            if rows:
                db_match = rows[0]

        if not db_match:
            # Query 2: Fallback to Name only
            query = f"SELECT * FROM `{table_id}` WHERE NAME1 = @search_term LIMIT 1"
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            query_job = client.query(query, job_config=job_config)
            rows = list(query_job.result())
            if rows:
                db_match = rows[0]

    # --- 4. VALIDATION LOGIC & RISK SCORING ---
    is_valid = db_match is not None
    risk_flags = []
    risk_score = 0
    confidence_level = "LOW"
    classification = "UNKNOWN"
    
    if is_valid:
        residential_types = ['Postcode', 'Named Road', 'Hamlet', 'Village', 'Other Settlement']
        classification = "RESIDENTIAL" if db_match['LOCAL_TYPE'] in residential_types else "BUSINESS"
        
        db_city = (db_match['POPULATED_PLACE'] or "").upper()
        db_borough = (db_match['DISTRICT_BOROUGH'] or "").upper()
        if user_area_context and not any(loc == user_area_context for loc in [db_city, db_borough] if loc):
            risk_flags.append("GEOGRAPHIC_AREA_MISMATCH")
            risk_score += 40

        if re.match(r"^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$", postcode):
            confidence_level = "HIGH"
        elif input_district or (not postcode and db_match['POSTCODE_DISTRICT']):
            risk_flags.append("PARTIAL_POSTCODE_DISTRICT")
            risk_score += 10
            confidence_level = "MEDIUM"
        else:
            risk_flags.append("MISSING_OR_INVALID_POSTCODE")
            risk_score += 30
    else:
        risk_flags.append("ADDRESS_NOT_IN_DATABASE")
        risk_score = 90

    # --- 5. FINAL CONSTRUCTION ---
    house_no = addr.get('house_number', '').strip()
    final_road = db_match['NAME1'] if is_valid else search_term
    final_pc = postcode if postcode else (db_match['POSTCODE_DISTRICT'] if is_valid else "UNKNOWN")
    full_std_addr = f"{house_no} {final_road}, {final_pc}".strip(", ").upper()

    is_duplicate = self._is_duplicate(full_std_addr)
    if is_duplicate:
        risk_flags.append('DUPLICATE ADDRESSES TRACKED')
        risk_score = min(risk_score + 30, 100)

    return CustomerAddressDQ(
        is_valid=is_valid,
        standardized_address=full_std_addr,
        classification=classification,
        is_duplicate=is_duplicate,
        populated_place=db_match['POPULATED_PLACE'] if is_valid else None,
        district_borough=db_match['DISTRICT_BOROUGH'] if is_valid else None,
        county=db_match['COUNTY_UNITARY'] if is_valid else None,
        risk_score=min(risk_score, 100),
        risk_flags=risk_flags,
        confidence_level=confidence_level,
        provider_metadata={
            "os_id": db_match['ID'] if is_valid else None,
            "local_type": db_match['LOCAL_TYPE'] if is_valid else "N/A",
            "country": db_match['COUNTRY'] if is_valid else "UK"
        }
    )

if __name__ == "__main__":
    # 1. Initialize the agent
    print("--- Starting Agent Test ---")
    agent = AddressAgent(db_path="Data/uk_validation.db")

    #test_address = "Melby Road, ZE2 9PL"

    test_addresses = [
        "Upper Thurnham, LA2",  
        "Woodend, WF10",        
        "Darrington, WF8",         
        "York Road , GU22",            
        "Dragon Breath Lane, ZZ9 9ZZ", #invalid
    ]

    for addr in test_addresses:
        print(f"Validating: {addr}")
        result = agent.validate(addr)
        print("\n--- Result ---")
        print(result.model_dump_json(indent=2))
