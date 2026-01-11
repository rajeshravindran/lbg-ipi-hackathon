import pandas as pd
import sqlite3
from postal.parser import parse_address
import glob
import os


# 1. SETUP: Load Data and Build Search Index
def initialize_database(header_path, data_folder_path, db_path='uk_validation.db'):
    header_df = pd.read_csv(header_path)
    column_names = header_df.columns.tolist()

    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS os_data")

    csv_files = glob.glob(os.path.join(data_folder_path, "*.csv"))
    
    for file in csv_files:
        if "header" in file.lower(): continue
        
        df = pd.read_csv(file, names=column_names, header=None, low_memory=False)
        
        # ADD 'ID' HERE 
        cols_to_keep = [
            'ID', 
            'NAME1', 
            'LOCAL_TYPE', 
            'POSTCODE_DISTRICT', 
            'POPULATED_PLACE', 
            'DISTRICT_BOROUGH',
            'COUNTY_UNITARY', 
            'COUNTRY'
        ]
        
        valid_types = ['Postcode', 'Named Road', 'Village', 'Hamlet']
        clean_df = df[df['LOCAL_TYPE'].isin(valid_types)][cols_to_keep]

        clean_df.to_sql('os_data', conn, if_exists='append', index=False)

    conn.execute("CREATE INDEX idx_name ON os_data (NAME1)")
    conn.close()
    print(f"Success! Database {db_path} is ready.")

# 2. VALIDATION LOGIC
def validate_uk_input(user_input, db_path='uk_validation.db'):
    # Parse the messy user input
    parsed = parse_address(user_input)
    addr = {label: value.upper() for value, label in parsed}
    
    user_road = addr.get('road')
    user_postcode = addr.get('postcode')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    results = {"valid_road": False, "valid_postcode": False, "matches": []}

    # Check Postcode
    if user_postcode:
        cursor.execute("SELECT * FROM os_data WHERE NAME1 = ? AND LOCAL_TYPE = 'Postcode'", (user_postcode,))
        if cursor.fetchone():
            results["valid_postcode"] = True

    # Check Road/Street
    if user_road:
        # Use LIKE for partial matches (e.g., 'Main St' vs 'Main Street')
        cursor.execute("SELECT * FROM os_data WHERE NAME1 LIKE ? AND LOCAL_TYPE = 'Named Road'", (f"%{user_road}%",))
        match = cursor.fetchone()
        if match:
            results["valid_road"] = True
            results["matches"].append(match)

    conn.close()
    return results

# --- EXECUTION ---

if __name__ == '__main__':

    header_path="/Users/mia/myprojects/uv_projects/lbg-ipi-hackathon/AddressValidator_Agent/Data/Doc/OS_Open_Names_Header.csv"
    data_path="/Users/mia/myprojects/uv_projects/lbg-ipi-hackathon/AddressValidator_Agent/Data/csv"
    db_path ="/Users/mia/myprojects/uv_projects/lbg-ipi-hackathon/AddressValidator_Agent/Data/uk_validation.db"

    # Initialize once
    initialize_database(header_path, data_path, db_path)
    # Test Validation
    test_address = "Melby Road, ZE2 9PL"
    report = validate_uk_input(test_address)

    print(f"\nValidation Report for: {test_address}")
    print(f"Postcode Valid: {report['valid_postcode']}")
    print(f"Road Valid: {report['valid_road']}")
    if report['matches']:
        print(f"Official Match: {report['matches'][0][0]}")