import sqlite3
from pydantic import BaseModel, Field
from typing import List, Optional
from postal.parser import parse_address
from pathlib import Path
import re
import sys

try:
    # This works when running through the Agent (adk run)
    from .schemas import CustomerAddressProfile
    from .createAddressDB import initialize_database
except (ImportError, ValueError):
    # This works when running 'python AddressValidator.py' directly
    # We add the current directory to sys.path to find the siblings
    current_dir = Path(__file__).resolve().parent
    if str(current_dir) not in sys.path:
        sys.path.append(str(current_dir))
    
    from schemas import CustomerAddressProfile
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
       
        if not self.db_path.exists():
            print(f"Database not found at {self.db_path}. Initializing...")
            initialize_database(
                header_path=self.header_path, 
                data_folder_path=self.data_path, 
                db_path=self.db_path
            ) 
        else:
            print(f"Using existing database at {self.db_path}") 

    
    def validate(self, user_input: str) -> CustomerAddressProfile:
        # 1. Parse with libpostal
        parsed = parse_address(user_input)
        addr = {label: value.upper() for value, label in parsed}
        
        # Capture what the user thinks the City/Borough is
        user_area_context = addr.get('city') or addr.get('suburb') or addr.get('state_district')
        
        # Components for searching the road/feature name
        geo_labels = ['road', 'suburb', 'city', 'neighborhood', 'village', 'hamlet', 'state_district']
        search_components = [val.upper() for val, label in parsed if label in geo_labels]
        search_term = " ".join(search_components).strip()

        # Fallbacks for short strings
        if not search_term and "," in user_input:
            search_term = user_input.split(',')[0].strip().upper()
        elif not search_term:
            search_term = user_input.split()[0].strip().upper()

        postcode_parts = [value.upper() for value, label in parsed if label == 'postcode']
        postcode = " ".join(postcode_parts).strip()
        
        # Regex for District extraction (e.g. LA2)
        input_district = postcode.split()[0] if postcode else None
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 2. Strict Database Search
        db_match = None
        if search_term:
            # We search based on NAME1. The new columns help us verify if the context is correct.
            if input_district:
                query = "SELECT * FROM os_data WHERE upper(NAME1) LIKE ? AND upper(POSTCODE_DISTRICT) like ? LIMIT 1"
                cursor.execute(query, (f"{search_term}%", f"{input_district}%"))
                db_match = cursor.fetchone()
            
            if not db_match:
                query = "SELECT * FROM os_data WHERE upper(NAME1) = ? LIMIT 1"
                cursor.execute(query, (search_term,))
                db_match = cursor.fetchone()
        
        conn.close()

        # 3. UK Postcode Patterns
        full_pc_pattern = r"^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$"
        dist_pc_pattern = r"^[A-Z]{1,2}[0-9][A-Z0-9]?$"

        # 4. Automated Heuristic Engine
        is_valid = db_match is not None
        risk_flags = []
        risk_score = 0
        confidence_level = "LOW"
        residential_types = ['Postcode', 'Named Road', 'Hamlet', 'Village', 'Other Settlement']
        
        if is_valid:
            classification = "RESIDENTIAL" if db_match['LOCAL_TYPE'] in residential_types else "BUSINESS"
            
            # --- AUTOMATED AREA CROSS-CHECK ---
            # We check if the City/Borough in the DB matches the context provided by the user
            db_city = (db_match['POPULATED_PLACE'] or "").upper()
            db_borough = (db_match['DISTRICT_BOROUGH'] or "").upper()

            if user_area_context:
                # If user provided an area name that is neither the DB's city nor the DB's borough
                valid_locations = [db_city, db_borough]

                if not any(loc == user_area_context for loc in valid_locations if loc):
                    risk_flags.append("GEOGRAPHIC_AREA_MISMATCH")
                    risk_score += 40

            # Postcode Validation
            if re.match(full_pc_pattern, postcode):
                confidence_level = "HIGH"
            elif re.match(dist_pc_pattern, postcode) or (not postcode and db_match['POSTCODE_DISTRICT']):
                risk_flags.append("PARTIAL_POSTCODE_DISTRICT")
                risk_score += 10
                confidence_level = "MEDIUM"
            else:
                risk_flags.append("MISSING_OR_INVALID_POSTCODE")
                risk_score += 30
                confidence_level = "LOW"
        else:
            risk_flags.append("ADDRESS_NOT_IN_DATABASE")
            risk_score = 90
            classification = "UNKNOWN"

        # 5. Construction of Final Profile
        house_no = addr.get('house_number', '').strip()
        if is_valid:
            final_road = db_match['NAME1'] if is_valid else search_term
            final_pc = postcode if postcode else (db_match['POSTCODE_DISTRICT'] if is_valid else "")
        else:
            final_road = search_term if search_term else "UNKNOWN ROAD"
            final_pc = postcode if postcode else "UNKNOWN POSTCODE"
        
        full_std_addr = f"{house_no} {final_road}, {final_pc}".strip(", ").upper()

        return CustomerAddressProfile(
            is_valid=is_valid,
            standardized_address=full_std_addr,
            classification=classification,
            populated_place=db_match['POPULATED_PLACE'] if is_valid else None,
            district_borough=db_match['DISTRICT_BOROUGH'] if is_valid else None,
            county=db_match['COUNTY_UNITARY'] if is_valid else None,
            risk_score=min(risk_score, 100),
            risk_flags=risk_flags,
            confidence_level=confidence_level,
            provider_metadata={
                "os_id": db_match['ID'] if is_valid else None,
                "local_type": db_match['LOCAL_TYPE'] if is_valid else None,
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
