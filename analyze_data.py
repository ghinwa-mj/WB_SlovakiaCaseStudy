#!/usr/bin/env python3
"""
Diagnostic script to analyze the MFSR data and understand filtering issues.
"""

import pandas as pd
import numpy as np

def analyze_data():
    """Analyze the MFSR data to understand filtering issues."""
    
    csv_file = "full_mfsr_data_completewith_ids.csv"
    
    print("="*60)
    print("MFSR DATA ANALYSIS")
    print("="*60)
    
    # Load the data
    df = pd.read_csv(csv_file)
    print(f"Total rows in CSV: {len(df)}")
    
    # Check for empty rows
    print(f"\nChecking for empty rows...")
    empty_sector = df['Sector'].isna().sum()
    empty_project = df['Project Name'].isna().sum()
    empty_type = df['Type'].isna().sum()
    empty_url = df['URL'].isna().sum()
    empty_doc_id = df['Document_ID'].isna().sum()
    
    print(f"Empty Sector: {empty_sector}")
    print(f"Empty Project Name: {empty_project}")
    print(f"Empty Type: {empty_type}")
    print(f"Empty URL: {empty_url}")
    print(f"Empty Document_ID: {empty_doc_id}")
    
    # Remove empty rows (same as Word generator)
    df_clean = df.dropna(subset=['Sector', 'Project Name'])
    print(f"\nAfter removing empty Sector/Project Name: {len(df_clean)}")
    
    # Check document types
    print(f"\nDocument types in data:")
    type_counts = df_clean['Type'].value_counts()
    for doc_type, count in type_counts.items():
        print(f"  {doc_type}: {count}")
    
    # Check for 'štúdia uskutočniteľnosti' documents
    studia_docs = df_clean[df_clean['Type'] == 'štúdia uskutočniteľnosti']
    print(f"\n'Štúdia uskutočniteľnosti' documents: {len(studia_docs)}")
    
    # Show some examples of missing data
    print(f"\nRows with missing data:")
    missing_data = df_clean[
        df_clean['Sector'].isna() | 
        df_clean['Project Name'].isna() | 
        df_clean['Type'].isna() | 
        df_clean['URL'].isna() | 
        df_clean['Document_ID'].isna()
    ]
    print(f"Rows with any missing data: {len(missing_data)}")
    
    if len(missing_data) > 0:
        print("Sample of rows with missing data:")
        print(missing_data[['Sector', 'Project Name', 'Type', 'URL', 'Document_ID']].head())
    
    # Check for duplicate Document_IDs
    print(f"\nChecking for duplicate Document_IDs:")
    duplicate_ids = df_clean[df_clean['Document_ID'].duplicated(keep=False)]
    print(f"Duplicate Document_IDs: {len(duplicate_ids)}")
    
    if len(duplicate_ids) > 0:
        print("Sample duplicate IDs:")
        print(duplicate_ids[['Document_ID', 'Sector', 'Project Name', 'Type']].head(10))
    
    # Final count that should be processed
    print(f"\n" + "="*60)
    print("FINAL ANALYSIS")
    print("="*60)
    
    # This is what the Word generator should process
    final_df = df_clean  # No filtering of 'štúdia uskutočniteľnosti' since it was removed
    
    print(f"Total documents that should be processed: {len(final_df)}")
    print(f"Documents by sector:")
    sector_counts = final_df['Sector'].value_counts()
    for sector, count in sector_counts.items():
        print(f"  {sector}: {count}")
    
    # Check if there are any other filtering issues
    print(f"\nChecking for other potential issues:")
    
    # Check for very long project names that might cause issues
    long_names = final_df[final_df['Project Name'].str.len() > 200]
    print(f"Very long project names (>200 chars): {len(long_names)}")
    
    # Check for special characters in Document_IDs
    special_chars = final_df[final_df['Document_ID'].str.contains(r'[^0-9.]', na=False)]
    print(f"Document_IDs with special characters: {len(special_chars)}")
    
    if len(special_chars) > 0:
        print("Sample Document_IDs with special characters:")
        print(special_chars[['Document_ID', 'Sector', 'Project Name']].head())

if __name__ == "__main__":
    analyze_data()
