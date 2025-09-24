import pandas as pd
import numpy as np
from datetime import datetime
import random

def create_unique_ids(df):
    """
    Create unique IDs for documents based on sector and chronological order.
    
    Step 1: Create an ID for each Sector
    Step 2: For each sector, create an ID that increases with the date order 
            and then increases randomly for the non-date documents
    Step 3: The Final ID will be SectorID.2ndID
    
    Args:
        df: DataFrame with columns ['Sector', 'Project Name', 'Type', 'URL', 'Date', 'File Size']
    
    Returns:
        DataFrame with additional 'Document_ID' column
    """
    
    # Step 1: Define sector mapping (SectorID)
    sector_mapping = {
        'Doprava': 1,
        'Informatizacia': 2, 
        'Budovy': 3,
        'Obrana': 4,
        'Ostatne': 5
    }
    
    # Convert Date column to datetime, handling NaN values
    def parse_date(date_str):
        if pd.isna(date_str) or date_str == '':
            return None
        try:
            # Handle Slovak date format DD.MM.YYYY
            return datetime.strptime(str(date_str), '%d.%m.%Y')
        except:
            return None
    
    df['Date_parsed'] = df['Date'].apply(parse_date)
    
    # Create a copy to work with
    df_with_ids = df.copy()
    df_with_ids['Document_ID'] = ''
    
    # Process each sector separately
    for sector, sector_id in sector_mapping.items():
        print(f"Processing sector: {sector} (SectorID: {sector_id})")
        
        # Filter dataframe to only this sector
        sector_df = df_with_ids[df_with_ids['Sector'] == sector].copy()
        
        if len(sector_df) == 0:
            print(f"  No documents found for {sector}")
            continue
            
        print(f"  Found {len(sector_df)} documents for {sector}")
        
        # Step 2: Sort by date (documents with dates first, then without dates)
        sector_df = sector_df.sort_values('Date_parsed', na_position='last')
        
        # Assign sequential IDs starting from 01 for documents with dates
        date_documents = sector_df[sector_df['Date_parsed'].notna()]
        no_date_documents = sector_df[sector_df['Date_parsed'].isna()]
        
        # Assign sequential IDs to documents with dates
        for i, (idx, row) in enumerate(date_documents.iterrows(), 1):
            # Use 3-digit formatting from the start to avoid float conversion issues
            doc_id = f"{sector_id}.{i:03d}"
            df_with_ids.loc[idx, 'Document_ID'] = doc_id
            print(f"    Assigned {doc_id} to document with date at index {idx}")
        
        # Assign random sequential IDs to documents without dates
        if len(no_date_documents) > 0:
            # Get the highest ID number used for this sector
            max_id = len(date_documents)
            
            # Create random order for no-date documents
            no_date_indices = no_date_documents.index.tolist()
            random.shuffle(no_date_indices)
            
            for i, idx in enumerate(no_date_indices):
                doc_num = max_id + i + 1
                # Use 3-digit formatting from the start
                doc_id = f"{sector_id}.{doc_num:03d}"
                df_with_ids.loc[idx, 'Document_ID'] = doc_id
                print(f"    Assigned {doc_id} to document without date at index {idx}")
    
    # Ensure Document_ID column is stored as string and force string type
    df_with_ids['Document_ID'] = df_with_ids['Document_ID'].astype(str)
    
    return df_with_ids.drop('Date_parsed', axis=1)

def main():
    # Load the data
    df = pd.read_csv('full_mfsr_data_complete.csv')
    
    print("="*60)
    print("CREATING UNIQUE DOCUMENT IDs")
    print("="*60)
    print(f"Total documents: {len(df)}")
    print(f"Sectors: {df['Sector'].value_counts().to_dict()}")
    print()
    
    # Create unique IDs
    df_with_ids = create_unique_ids(df)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    # Save the result
    df_with_ids.to_csv("full_mfsr_data_completewith_ids.csv", index=False, encoding="utf-8-sig")
    print("Saved results to: full_mfsr_data_completewith_ids.csv")
    
    # Show summary by sector
    print("\nID ranges by sector:")
    for sector in ['Doprava', 'Informatizacia', 'Budovy', 'Obrana', 'Ostatne']:
        sector_data = df_with_ids[df_with_ids['Sector'] == sector]['Document_ID']
        if not sector_data.empty:
            print(f"{sector}: {sector_data.min()} to {sector_data.max()} ({len(sector_data)} documents)")
    
    # Show sample results
    print("\nSample of results:")
    sample_cols = ['Document_ID', 'Sector', 'Project Name', 'Date']
    print(df_with_ids[sample_cols].head(10).to_string(index=False))
    
    # Verify all documents have IDs
    missing_ids = len(df_with_ids[df_with_ids['Document_ID'] == ''])
    print(f"\nDocuments without IDs: {missing_ids}")
    print(f"Total documents processed: {len(df_with_ids)}")
    
    # Show examples by sector
    print("\nFirst 3 IDs for each sector:")
    for sector in ['Doprava', 'Informatizacia', 'Budovy', 'Obrana', 'Ostatne']:
        sector_data = df_with_ids[df_with_ids['Sector'] == sector]['Document_ID'].head(3)
        if not sector_data.empty:
            print(f"{sector}: {sector_data.tolist()}")

if __name__ == "__main__":
    main()
