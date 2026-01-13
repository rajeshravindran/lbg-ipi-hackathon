import pandas as pd
import sqlite3
from postal.parser import parse_address
from google.cloud import bigquery, storage
from google.cloud import bigquery
import glob
import os
from dotenv import load_dotenv
import io

load_dotenv(override=True)

PROJECT_ID = "dbs-data-ai-ai-core"
DATASET_ID = "lbg_ipi_digitalwallet "
TABLE_ID = "os_data"
BUCKET_NAME = 'lbg-ipi-digitalwallet'
client_bq = bigquery.Client(project=PROJECT_ID)
client_gcs = storage.Client(project=PROJECT_ID)

# 1. SETUP: Load Data and Build Search Index

def initialize_bigquery_from_local(header_path, data_folder_path):
    # 1. Setup Configuration
    project_id = "dbs-data-ai-ai-core"
    dataset_id = "lbg_ipi_digitalwallet"
    table_name = "os_data"
    table_id = f"{project_id}.{dataset_id}.{table_name}"
    
    client = bigquery.Client(project=project_id)

    # 2. ENSURE DATASET EXISTS (The Fix)
    try:
        client.get_dataset(dataset_id)
        print(f"✅ Dataset {dataset_id} found.")
    except NotFound:
        print(f"Empty dataset {dataset_id} not found. Creating it now...")
        dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
        dataset.location = "EU"  # Ensure this matches your data residency requirements
        client.create_dataset(dataset, timeout=30)
        print(f"✅ Dataset {dataset_id} created successfully.")

    # 3. Handle Header and Columns
    header_df = pd.read_csv(header_path)
    column_names = header_df.columns.tolist()
    
    cols_to_keep = [
        'ID', 'NAME1', 'LOCAL_TYPE', 'POSTCODE_DISTRICT', 
        'POPULATED_PLACE', 'DISTRICT_BOROUGH', 'COUNTY_UNITARY', 'COUNTRY'
    ]
    valid_types = ['Postcode', 'Named Road', 'Village', 'Hamlet']

    # 2. DELETE THE TABLE IF IT ALREADY EXISTS (To fix the partitioning mismatch)
    client.delete_table(table_id, not_found_ok=True)
    print(f"🗑️ Old table deleted (to refresh clustering spec).")

    # 4. Configure Load Job
    # Using WRITE_TRUNCATE to clear any old data on the first run
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        clustering_fields=["NAME1"], # Optimizes for address searches
        schema=[bigquery.SchemaField(col, "STRING") for col in cols_to_keep]
    )

    csv_files = glob.glob(os.path.join(data_folder_path, "*.csv"))
    
    for i, file_path in enumerate(csv_files):
        if "header" in file_path.lower(): continue
        
        print(f"🚀 Processing: {os.path.basename(file_path)}")
        
        # Read and filter locally
        df = pd.read_csv(file_path, names=column_names, header=None, low_memory=False)
        clean_df = df[df['LOCAL_TYPE'].isin(valid_types)][cols_to_keep]

        # Convert to CSV buffer
        buffer = io.StringIO()
        clean_df.to_csv(buffer, index=False)
        buffer.seek(0)

        # Load to BigQuery
        load_job = client.load_table_from_file(
            io.BytesIO(buffer.getvalue().encode()), 
            table_id, 
            job_config=job_config
        )
        load_job.result() # Wait for completion
        
        # Switch to APPEND and skip headers for subsequent files
        job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND
        job_config.skip_leading_rows = 1 

    print(f"\n✨ Success! Data fully uploaded to {table_id}")

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

def validate_uk_input_bq(user_input):
    # 1. Setup BigQuery Client and Table Path
    project_id = "dbs-data-ai-ai-core"
    dataset_id = "lbg_ipi_digitalwallet"
    table_id = f"{project_id}.{dataset_id}.os_data"
    
    client = bigquery.Client(project=project_id)
    
    # 2. Parse the messy user input
    parsed = parse_address(user_input)
    addr = {label: value.upper() for value, label in parsed}
    
    user_road = addr.get('road')
    user_postcode = addr.get('postcode')
    
    results = {"valid_road": False, "valid_postcode": False, "matches": []}

    # 3. Check Postcode
    if user_postcode:
        # Clustered search on NAME1 is very fast here
        postcode_query = f"""
            SELECT * FROM `{table_id}` 
            WHERE NAME1 = @postcode AND LOCAL_TYPE = 'Postcode'
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("postcode", "STRING", user_postcode)
            ]
        )
        postcode_results = client.query(postcode_query, job_config=job_config).result()
        if list(postcode_results):
            results["valid_postcode"] = True

    # 4. Check Road/Street
    if user_road:
        # Partial match using LIKE
        road_query = f"""
            SELECT * FROM `{table_id}` 
            WHERE NAME1 LIKE @road AND LOCAL_TYPE = 'Named Road'
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("road", "STRING", f"%{user_road}%")
            ]
        )
        road_results = client.query(road_query, job_config=job_config).result()
        
        # Convert Row objects to dictionaries/lists for the response
        for row in road_results:
            results["valid_road"] = True
            results["matches"].append(dict(row))

    return results

# --- EXECUTION ---

if __name__ == '__main__':

    header_path="/Users/mia/myprojects/uv_projects/lbg-ipi-hackathon/AddressValidator_Agent/Data/Doc/OS_Open_Names_Header.csv"
    data_path="/Users/mia/myprojects/uv_projects/lbg-ipi-hackathon/AddressValidator_Agent/Data/csv"
    db_path ="/Users/mia/myprojects/uv_projects/lbg-ipi-hackathon/AddressValidator_Agent/Data/uk_validation.db"

    # Initialize once
    #initialize_database(header_path, data_path, db_path)
    initialize_bigquery_from_local(header_path, data_path)
    # Test Validation
    test_address = "Melby Road, ZE2 9PL"
    report = validate_uk_input_bq(test_address)

    print(f"\nValidation Report for: {test_address}")
    print(f"Postcode Valid: {report['valid_postcode']}")
    print(f"Road Valid: {report['valid_road']}")
    if report['matches']:
        print(f"Official Match: {report['matches'][0][0]}")