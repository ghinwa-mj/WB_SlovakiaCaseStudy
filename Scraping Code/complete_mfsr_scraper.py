#!/usr/bin/env python3
"""
Complete MFSR scraper that captures ALL document types from all sectors.
Loops through all sector pages and extracts all documents (PDF, Word, Excel, PowerPoint, etc.).
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import re
import sys
import traceback
import time

BASE = "https://www.mfsr.sk"

# All sector URLs to scrape
SECTOR_URLS = {
    "Obrana": "https://www.mfsr.sk/sk/financie/hodnota-za-peniaze/hodnotenia/obrana.html",
    "Budovy": "https://www.mfsr.sk/sk/financie/hodnota-za-peniaze/hodnotenia/budovy.html", 
    "Doprava": "https://www.mfsr.sk/sk/financie/hodnota-za-peniaze/hodnotenia/doprava.html",
    "Informatizacia": "https://www.mfsr.sk/sk/financie/hodnota-za-peniaze/hodnotenia/informatizacia.html",
    "Ostatne": "https://www.mfsr.sk/sk/financie/hodnota-za-peniaze/hodnotenia/ostatne.html"
}

# Regexes
date_re = re.compile(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b')
size_re = re.compile(r'\b\d+(?:[.,]\d+)?\s*(?:kB|KB|MB|GB|B|kb|mb|gb)\b')

def extract_date_and_size(anchor):
    """Search for date and size strings around the anchor."""
    search_texts = []

    try:
        search_texts.append(anchor.get_text(" ", strip=True))
    except Exception:
        pass

    if anchor.parent:
        try:
            search_texts.append(anchor.parent.get_text(" ", strip=True))
        except Exception:
            pass

    for sib in list(anchor.previous_siblings)[:12]:
        if hasattr(sib, "get_text"):
            search_texts.append(sib.get_text(" ", strip=True))
        else:
            search_texts.append(str(sib).strip())

    for sib in list(anchor.next_siblings)[:6]:
        if hasattr(sib, "get_text"):
            search_texts.append(sib.get_text(" ", strip=True))
        else:
            search_texts.append(str(sib).strip())

    combined = " ".join([t for t in search_texts if t])
    date_match = date_re.search(combined)
    size_match = size_re.search(combined)

    return date_match.group(0) if date_match else None, size_match.group(0) if size_match else None

def is_document_link(href, link_text):
    """Check if link is a document (PDF, DOC, DOCX, XLS, XLSX, etc.)."""
    if not href:
        return False
    href_l = href.lower()
    link_text_l = link_text.lower()
    
    # Check for common document file extensions
    document_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.odt', '.ods', '.odp']
    
    # Check if href contains any document extension
    for ext in document_extensions:
        if ext in href_l:
            return True
    
    # Check if link text suggests it's a document
    document_keywords = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'súbor', 'dokument', 'file', 'hodnotenie', 'analýza', 'analyza', 'štúdia', 'aktualizácia', 'stanovisko', 'správa', 'metodika', 'zmluva', 'dohoda']
    for keyword in document_keywords:
        if keyword in link_text_l:
            return True
    
    # Check if it's a link to files/archiv (common pattern for MFSR documents)
    if '/files/archiv/' in href_l or '/files/' in href_l:
        return True
    
    # Check if it's an external document link (mosr.sk, etc.)
    if 'mosr.sk' in href_l and any(ext in href_l for ext in document_extensions):
        return True
    
    return False

def determine_document_type(link_text, parent_text="", href=""):
    """Determine document type from link text, parent context, and file extension."""
    text_to_search = f"{link_text} {parent_text}".lower()
    href_l = href.lower() if href else ""
    
    # First check file extension to determine format
    file_format = ""
    if '.pdf' in href_l:
        file_format = "PDF"
    elif '.doc' in href_l or '.docx' in href_l:
        file_format = "Word"
    elif '.xls' in href_l or '.xlsx' in href_l:
        file_format = "Excel"
    elif '.ppt' in href_l or '.pptx' in href_l:
        file_format = "PowerPoint"
    elif '.txt' in href_l:
        file_format = "Text"
    elif '.rtf' in href_l:
        file_format = "RTF"
    
    # Standard document types
    if 'hodnotenie' in text_to_search:
        doc_type = 'hodnotenie'
    elif 'analýza' in text_to_search or 'analyza' in text_to_search:
        doc_type = 'analýza'
    elif 'štúdia uskutočniteľnosti' in text_to_search:
        doc_type = 'štúdia uskutočniteľnosti'
    elif 'aktualizácia' in text_to_search:
        doc_type = 'aktualizácia'
    elif 'stanovisko' in text_to_search:
        doc_type = 'stanovisko'
    elif 'správa' in text_to_search:
        doc_type = 'správa'
    elif 'metodika' in text_to_search:
        doc_type = 'metodika'
    elif 'zmluva' in text_to_search:
        doc_type = 'zmluva'
    elif 'dohoda' in text_to_search:
        doc_type = 'dohoda'
    elif 'investičný zámer' in text_to_search:
        doc_type = 'investičný zámer'
    else:
        # If no specific type found, use the link text itself (truncated)
        doc_type = link_text[:50] + "..." if len(link_text) > 50 else link_text
    
    # Combine document type with file format if available
    if file_format:
        return f"{doc_type} ({file_format})"
    else:
        return doc_type

def scrape_sector_page(sector_name, page_url, session):
    """Scrape a single sector page and return list of documents."""
    print(f"\nScraping {sector_name} sector: {page_url}")
    
    try:
        resp = session.get(page_url, timeout=20)
        if resp.status_code != 200:
            print(f"Non-200 status code for {sector_name}: {resp.status_code}")
            return []

        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = []
        seen = set()
        last_project_name = "UNKNOWN_PROJECT"

        # Find all h5 elements (project headers) and process them with their associated links
        h5_elements = soup.find_all("h5")
        
        for h5 in h5_elements:
            project_name = h5.get_text(" ", strip=True)
            # Clean up project name - remove extra whitespace and formatting
            project_name = re.sub(r'\s+', ' ', project_name).strip()
            
            # Skip empty or very short project names
            if len(project_name) < 5:
                continue
                
            # Look for document links that follow this h5 element
            # Find the next sibling elements until we hit another h5 or end
            current_element = h5.next_sibling
            
            while current_element:
                if current_element.name == "h5":
                    # Hit another project, stop processing
                    break
                    
                # Look for links in this element and its children
                if current_element.name == "a" and is_document_link(current_element.get("href"), current_element.get_text(" ", strip=True)):
                    link_text = current_element.get_text(" ", strip=True)
                    parent_text = current_element.parent.get_text(" ", strip=True) if current_element.parent else ""
                    dtype = determine_document_type(link_text, parent_text, current_element.get("href"))
                    url = urljoin(BASE, current_element["href"])
                    date, size = extract_date_and_size(current_element)
                    
                    key = (sector_name, project_name, url)
                    if key not in seen:
                        rows.append((sector_name, project_name, dtype, url, date or "", size or ""))
                        seen.add(key)
                
                # Also check for links in child elements (like <ul><li><a>)
                elif hasattr(current_element, 'find_all'):
                    links = current_element.find_all("a")
                    for link in links:
                        if is_document_link(link.get("href"), link.get_text(" ", strip=True)):
                            link_text = link.get_text(" ", strip=True)
                            parent_text = link.parent.get_text(" ", strip=True) if link.parent else ""
                            dtype = determine_document_type(link_text, parent_text, link.get("href"))
                            url = urljoin(BASE, link["href"])
                            date, size = extract_date_and_size(link)
                            
                            key = (sector_name, project_name, url)
                            if key not in seen:
                                rows.append((sector_name, project_name, dtype, url, date or "", size or ""))
                                seen.add(key)
                
                current_element = current_element.next_sibling

        print(f"Found {len(rows)} documents in {sector_name}")
        return rows

    except Exception as e:
        print(f"Error scraping {sector_name}: {e}")
        return []

def main():
    """Main function to scrape all sectors."""
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/117.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,sk;q=0.8"
        }
        session.headers.update(headers)

        all_rows = []
        
        # Scrape each sector
        for sector_name, page_url in SECTOR_URLS.items():
            sector_rows = scrape_sector_page(sector_name, page_url, session)
            all_rows.extend(sector_rows)
            
            # Small delay between requests to be respectful
            time.sleep(1)

        # Create DataFrame
        df = pd.DataFrame(all_rows, columns=["Sector", "Project Name", "Type", "URL", "Date", "File Size"])
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total documents collected: {len(df)}")
        
        # Show summary by sector
        print(f"\nDocuments by sector:")
        sector_counts = df['Sector'].value_counts()
        for sector, count in sector_counts.items():
            print(f"  {sector}: {count}")
        
        # Show unique document types found
        print(f"\nUnique document types found:")
        unique_types = df['Type'].value_counts()
        for doc_type, count in unique_types.items():
            print(f"  {doc_type}: {count}")
        
        # Show sample of results
        print(f"\nSample of results:")
        print(df.head(10).to_string(index=False))
        
        # Save to CSV
        output_file = "full_mfsr_data_complete.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\nSaved complete data to: {output_file}")
        
        # Show some examples of different document types
        print(f"\nExamples of 'Aktualizácia' documents:")
        aktualizacia_docs = df[df['Type'].str.contains('aktualizácia', case=False, na=False)]
        if not aktualizacia_docs.empty:
            print(aktualizacia_docs[['Sector', 'Project Name', 'Type', 'Date']].head().to_string(index=False))
        
        print(f"\nExamples of 'Stanovisko' documents:")
        stanovisko_docs = df[df['Type'].str.contains('stanovisko', case=False, na=False)]
        if not stanovisko_docs.empty:
            print(stanovisko_docs[['Sector', 'Project Name', 'Type', 'Date']].head().to_string(index=False))
        
        # Show examples of different file formats found
        print(f"\nExamples of different file formats:")
        format_examples = df[df['Type'].str.contains(r'\(PDF\)|\(Word\)|\(Excel\)|\(PowerPoint\)', case=False, na=False)]
        if not format_examples.empty:
            print(format_examples[['Sector', 'Project Name', 'Type', 'Date']].head().to_string(index=False))

    except Exception as e:
        print("Exception occurred:", e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
