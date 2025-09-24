#!/usr/bin/env python3
"""
Document Downloader for MFSR Documents
Downloads all documents (PDFs, Word, Excel, etc.) from the MFSR data and saves them with Document_ID as filename.
Creates a tracking CSV to monitor download success/failure.
"""

import pandas as pd
import requests
import os
import time
from urllib.parse import urlparse
import traceback
from pathlib import Path

def setup_download_directory():
    """Create downloads directory if it doesn't exist."""
    download_dir = Path("downloaded_documents")
    download_dir.mkdir(exist_ok=True)
    return download_dir

def get_file_extension(url):
    """Extract file extension from URL."""
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    # Common document extensions
    extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                 '.txt', '.rtf', '.odt', '.ods', '.odp', '.csv', '.xml',
                 '.zip', '.rar', '.7z', '.tar', '.gz']
    
    for ext in extensions:
        if path.endswith(ext):
            return ext
    
    # Default to .pdf if no extension found (for backward compatibility)
    return '.pdf'

def is_archive_file(url):
    """Check if the URL points to an archive file that should be skipped."""
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    # Archive extensions to skip
    archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz']
    
    for ext in archive_extensions:
        if path.endswith(ext):
            return True
    
    return False

def clean_filename(filename):
    """Clean filename to be filesystem-safe."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove extra spaces and dots
    filename = filename.strip('. ')
    
    # Ensure it's not too long
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def download_document(url, filepath, session, timeout=30):
    """Download a document from URL and save to filepath."""
    try:
        print(f"Downloading: {url}")
        
        response = session.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Check content type for validation
        content_type = response.headers.get('content-type', '').lower()
        print(f"  Content-Type: {content_type}")
        
        # Save the file
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Verify file was created and has content
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            file_size = os.path.getsize(filepath)
            print(f"  ✓ Success: {file_size:,} bytes")
            return True, f"Success: {file_size:,} bytes"
        else:
            print(f"  ✗ Failed: File is empty or doesn't exist")
            return False, "Failed: File is empty"
            
    except requests.exceptions.Timeout:
        error_msg = "Timeout"
        print(f"  ✗ Failed: {error_msg}")
        return False, error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Connection error"
        print(f"  ✗ Failed: {error_msg}")
        return False, error_msg
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error: {e.response.status_code}"
        print(f"  ✗ Failed: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"  ✗ Failed: {error_msg}")
        return False, error_msg

def main():
    """Main function to download all documents."""
    
    # Setup
    print("="*60)
    print("MFSR DOCUMENT DOWNLOADER")
    print("="*60)
    
    # Load the data
    csv_file = "full_mfsr_data_completewith_ids.csv"
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found!")
        print("Please make sure the CSV file exists in the current directory.")
        return
    
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} documents from {csv_file}")
    
    # Filter out documents without URLs
    df_with_urls = df[df['URL'].notna() & (df['URL'] != '')]
    print(f"Documents with URLs: {len(df_with_urls)}")
    
    # Filter to only specific document types
    allowed_types = ['analýza', 'hodnotenie', 'stanovisko']
    df_filtered = df_with_urls[df_with_urls['Type'].isin(allowed_types)]
    print(f"Documents filtered to types {allowed_types}: {len(df_filtered)}")
    
    # Show breakdown by type
    print(f"\nDocument type breakdown:")
    type_counts = df_filtered['Type'].value_counts()
    for doc_type, count in type_counts.items():
        print(f"  {doc_type}: {count}")
    
    if len(df_filtered) == 0:
        print("No documents found with the specified types!")
        return
    
    # Setup download directory
    download_dir = setup_download_directory()
    print(f"Download directory: {download_dir.absolute()}")
    
    # Setup session
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,sk;q=0.8"
    })
    
    # Track download results
    download_results = []
    
    print(f"\nStarting downloads...")
    print("-" * 60)
    
    # Download each document
    for idx, row in df_filtered.iterrows():
        doc_id = row['Document_ID']
        url = row['URL']
        sector = row['Sector']
        project_name = row['Project Name']
        doc_type = row['Type']
        
        # Check if this is an archive file that should be skipped
        if is_archive_file(url):
            print(f"Skipping {doc_id} - archive file (.zip, .rar, etc.)")
            download_results.append({
                'Document_ID': doc_id,
                'Sector': sector,
                'Project_Name': project_name,
                'Type': doc_type,
                'URL': url,
                'Filename': f"{doc_id}{get_file_extension(url)}",
                'Status': 'Failed',
                'Message': 'Skipped: Archive file (.zip, .rar, etc.)',
                'File_Size': 0
            })
            continue
        
        # Create filename from Document_ID with proper extension
        file_extension = get_file_extension(url)
        filename = f"{doc_id}{file_extension}"
        filename = clean_filename(filename)
        filepath = download_dir / filename
        
        # Skip if file already exists
        if filepath.exists():
            print(f"Skipping {doc_id} - file already exists")
            download_results.append({
                'Document_ID': doc_id,
                'Sector': sector,
                'Project_Name': project_name,
                'Type': doc_type,
                'URL': url,
                'Filename': filename,
                'Status': 'Skipped',
                'Message': 'File already exists',
                'File_Size': os.path.getsize(filepath)
            })
            continue
        
        # Download the document
        success, message = download_document(url, filepath, session)
        
        # Record result
        file_size = os.path.getsize(filepath) if success and filepath.exists() else 0
        download_results.append({
            'Document_ID': doc_id,
            'Sector': sector,
            'Project_Name': project_name,
            'Type': doc_type,
            'URL': url,
            'Filename': filename,
            'Status': 'Success' if success else 'Failed',
            'Message': message,
            'File_Size': file_size
        })
        
        # Small delay to be respectful to the server
        time.sleep(0.5)
    
    # Create results DataFrame
    results_df = pd.DataFrame(download_results)
    
    # Save results CSV (includes ALL downloads - successful and failed)
    results_file = "download_results.csv"
    results_df.to_csv(results_file, index=False, encoding="utf-8-sig")
    print(f"\nDownload results saved to: {results_file}")
    print("Note: This CSV includes ALL downloads (successful, failed, and skipped)")
    
    # Save separate CSV for failed downloads only
    failed_df = results_df[results_df['Status'] == 'Failed']
    if len(failed_df) > 0:
        failed_file = "failed_downloads.csv"
        failed_df.to_csv(failed_file, index=False, encoding="utf-8-sig")
        print(f"Failed downloads saved to: {failed_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    
    total_docs = len(results_df)
    successful = len(results_df[results_df['Status'] == 'Success'])
    failed = len(results_df[results_df['Status'] == 'Failed'])
    skipped = len(results_df[results_df['Status'] == 'Skipped'])
    
    print(f"Total documents: {total_docs}")
    print(f"Successfully downloaded: {successful}")
    print(f"Failed downloads: {failed}")
    print(f"Skipped (already exists): {skipped}")
    print(f"Success rate: {(successful/total_docs)*100:.1f}%")
    
    # Show failed downloads with more detail
    if failed > 0:
        print(f"\nFailed downloads details:")
        failed_docs = results_df[results_df['Status'] == 'Failed']
        for _, row in failed_docs.iterrows():
            print(f"  {row['Document_ID']} ({row['Sector']}): {row['Message']}")
            print(f"    URL: {row['URL']}")
    
    # Show status breakdown by sector
    print(f"\nStatus breakdown by sector:")
    sector_status = results_df.groupby(['Sector', 'Status']).size().unstack(fill_value=0)
    print(sector_status)
    
    # Show file size statistics
    successful_docs = results_df[results_df['Status'].isin(['Success', 'Skipped'])]
    if len(successful_docs) > 0:
        total_size = successful_docs['File_Size'].sum()
        avg_size = successful_docs['File_Size'].mean()
        print(f"\nFile size statistics:")
        print(f"Total downloaded size: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
        print(f"Average file size: {avg_size:,.0f} bytes ({avg_size/1024:.1f} KB)")
    
    print(f"\nDownloaded files are in: {download_dir.absolute()}")

if __name__ == "__main__":
    main()
