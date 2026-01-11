import sqlite3
from pydantic import BaseModel, Field
from typing import List, Optional
from postal.parser import parse_address
from schemas import CustomerAddressProfile
from createAddressDB import initialize_database
from pathlib import Path
import re

class AddressAgent:
    def __init__(self, db_path='uk_validation.db'):
        base_dir = Path(__file__).resolve().parent.parent
        self.db_path = base_dir / db_path
        self.header_path = base_dir / "Data/Doc/OS_Open_Names_Header.csv"
        self.data_path = base_dir / "Data/csv"
        self.db_path = base_dir / db_path
        if not self.db_path.exists():
            print("Database not found. Initializing (this may take a minute)...")
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
        
        # IMPROVEMENT: Expanded labels to catch Hamlets/Villages like Bleasdale
        geo_labels = ['road', 'suburb', 'city', 'neighborhood', 'village', 'hamlet', 'state_district']
        search_components = [val.upper() for val, label in parsed if label in geo_labels]
        search_term = " ".join(search_components).strip()

        # FALLBACK: If libpostal is confused by the short string, take the first part
        if not search_term and "," in user_input:
            search_term = user_input.split(',')[0].strip().upper()
        elif not search_term:
            search_term = user_input.split()[0].strip().upper()

        # Postcode extraction
        postcode_parts = [value.upper() for value, label in parsed if label == 'postcode']
        postcode = " ".join(postcode_parts).strip()
        
        # If libpostal didn't label the postcode, check if the last word looks like one
        if not postcode and len(user_input.split()) > 1:
            last_word = user_input.split()[-1].upper()
            if re.match(r"^[A-Z]{1,2}[0-9][A-Z0-9]?$", last_word):
                postcode = last_word

        input_district = postcode.split()[0] if postcode else None
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 2. Strict Database Search
        db_match = None
        if search_term:
            if input_district:
                # Match name AND district (Bleasdale in PR3)
                query = "SELECT * FROM os_data WHERE NAME1 LIKE ? AND POSTCODE_DISTRICT = ? LIMIT 1"
                cursor.execute(query, (f"{search_term}%", input_district))
                db_match = cursor.fetchone()
            
            # Secondary fallback: If no match with district, try name only
            if not db_match:
                query = "SELECT * FROM os_data WHERE NAME1 = ? LIMIT 1"
                cursor.execute(query, (search_term,))
                db_match = cursor.fetchone()
        
        conn.close()

        # 3. UK Postcode Regex
        full_pc_pattern = r"^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$"
        dist_pc_pattern = r"^[A-Z]{1,2}[0-9][A-Z0-9]?$"

        # 4. Heuristic Engine
        is_valid = db_match is not None
        risk_flags = []
        risk_score = 0
        confidence_level = "LOW"
        residential_types = ['Postcode', 'Named Road', 'Hamlet', 'Village', 'Other Settlement']
        
        if is_valid:
            classification = "RESIDENTIAL" if db_match['LOCAL_TYPE'] in residential_types else "BUSINESS"
            
            if re.match(full_pc_pattern, postcode):
                confidence_level = "HIGH"
            elif re.match(dist_pc_pattern, postcode) or (not postcode and db_match['POSTCODE_DISTRICT']):
                risk_flags.append("PARTIAL_POSTCODE_DISTRICT")
                risk_score = 10
                confidence_level = "MEDIUM"
            else:
                risk_flags.append("MISSING_OR_INVALID_POSTCODE")
                risk_score = 30
        else:
            risk_flags.append("ADDRESS_NOT_IN_DATABASE")
            risk_score = 90
            classification = "UNKNOWN"

        # 5. Construction
        house_no = addr.get('house_number', '').strip()
        final_road = db_match['NAME1'] if is_valid else search_term
        final_pc = postcode if postcode else (db_match['POSTCODE_DISTRICT'] if is_valid else "")
        
        main_addr = f"{house_no} {final_road}".strip()
        std_addr = f"{main_addr}, {final_pc}".strip(", ")

        return CustomerAddressProfile(
            is_valid=is_valid,
            standardized_address=std_addr.upper(),
            classification=classification,
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
        "Upper Thurnham, LA2",   # Hamlet
        "Gostagert Road, ZE2",        # Named Road
        "Sandness, ZE2",         # Other Settlement
        "Melby, ZE2 9PN",            # Village
        "Dragon Breath Lane, ZZ9 9ZZ", #invalid
    ]

    for addr in test_addresses:
        print(f"Validating: {addr}")
        result = agent.validate(addr)
        print("\n--- Result ---")
        print(result.model_dump_json(indent=2))
