import sqlite3
from pydantic import BaseModel, Field
from typing import List, Optional
from postal.parser import parse_address
from schemas import CustomerAddressProfile

class AddressAgent:
    def __init__(self, db_path='uk_validation.db'):
        self.db_path = db_path

    def validate(self, user_input: str) -> CustomerAddressProfile:
        # 1. Parse with libpostal
        parsed = parse_address(user_input)
        addr = {label: value.upper() for value, label in parsed}
        
        street = addr.get('road')
        postcode = addr.get('postcode')
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # Allows accessing columns by name
        cursor = conn.cursor()
        
        # 2. Search Logic
        # We search for the road specifically within that postcode district for accuracy
        query = "SELECT * FROM os_data WHERE NAME1 LIKE ? LIMIT 1"
        cursor.execute(query, (f"%{street}%",))
        db_match = cursor.fetchone()
        conn.close()

        # 3. Heuristic Engine (Risk & Classification)
        is_valid = db_match is not None
        risk_flags = []
        risk_score = 0
        
        # Default classification
        classification = "UNKNOWN"
        
        if is_valid:
            # Classification Heuristic based on OS LOCAL_TYPE
            # Named Roads are usually neutral, but "Other Settlement" or specific local types 
            # can help us guess.
            if db_match['LOCAL_TYPE'] in ['Postcode', 'Named Road']:
                classification = "RESIDENTIAL" # Default assumption for open data
            
            # Risk Scoring Logic
            if not postcode:
                risk_flags.append("MISSING_POSTCODE")
                risk_score += 30
            
            # Check for generic/empty road names
            if street and len(street) < 3:
                risk_flags.append("SHORT_ROAD_NAME")
                risk_score += 20
        else:
            risk_flags.append("ADDRESS_NOT_IN_DATABASE")
            risk_score = 90
            classification = "UNKNOWN"

        # 4. Constructing the Standardized String
        std_addr = f"{addr.get('house_number', '')} {street or ''}, {postcode or ''}".strip(", ")

        return CustomerAddressProfile(
            is_valid=is_valid,
            standardized_address=std_addr.upper(),
            classification=classification,
            risk_score=min(risk_score, 100),
            risk_flags=risk_flags,
            confidence_level="HIGH" if is_valid and postcode else "LOW",
            provider_metadata={
                "os_id": db_match['ID'] if db_match else None,
                "local_type": db_match['LOCAL_TYPE'] if db_match else None,
                "country": db_match['COUNTRY'] if db_match else "UK"
            }
        )