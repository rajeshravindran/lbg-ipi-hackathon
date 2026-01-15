import pandas as pd
import pandas_gbq
import glob

project_id = "dbs-data-ai-ai-core"
dataset_id = "lbg_ipi_digitalwallet"
table_id = f"{dataset_id}.os_data"

headerpath = "./Doc/OS_Open_Names_Header.csv"
csv_files = glob.glob("./csv/*.csv")

cols_to_keep = [
    'ID', 'NAME1', 'LOCAL_TYPE', 'POSTCODE_DISTRICT', 
    'POPULATED_PLACE', 'DISTRICT_BOROUGH', 'COUNTY_UNITARY', 'COUNTRY'
]
valid_types = ['Postcode', 'Named Road', 'Village', 'Hamlet']

# Load headers once
header_df = pd.read_csv(headerpath)
column_names = header_df.columns.tolist()

# List to store dataframes for efficient merging
df_list = []

for i, file in enumerate(csv_files):
    print(f"Processing {i}: {file}")
    # Read only necessary columns to save memory
    df = pd.read_csv(file, names=column_names, header=None, low_memory=False)
    
    # Filter rows and select columns
    clean_df = df[df['LOCAL_TYPE'].isin(valid_types)][cols_to_keep]
    df_list.append(clean_df)

# Concatenate all at once
final_df = pd.concat(df_list, ignore_index=True)

print(f"Total rows to upload: {len(final_df)}")

# Upload to BigQuery
# Note: 'replace' will overwrite the table every time the script runs. 
# Use 'append' if you are processing files in batches over time.
pandas_gbq.to_gbq(final_df, table_id, project_id=project_id, if_exists='replace')