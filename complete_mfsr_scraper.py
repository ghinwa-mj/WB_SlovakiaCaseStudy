#!/usr/bin/env python3
"""
Complete MFSR scraper that captures ALL PDF documents from all sectors.
Loops through all sector pages and extracts all documents regardless of type.
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

def is_pdf_link(href, link_text):
    """Check if link is a PDF document."""
    if not href:
        return False
    href_l = href.lower()
    if '.pdf' in href_l or 'pdf' in link_text.lower():
        return True
    return False

def determine_document_type(link_text, parent_text=""):
    """Determine document type from link text and parent context."""
    text_to_search = f"{link_text} {parent_text}".lower()
    
    # Standard types
    if 'hodnotenie' in text_to_search:
        return 'hodnotenie'
    elif 'analýza' in text_to_search or 'analyza' in text_to_search:
        return 'analýza'
    elif 'štúdia uskutočniteľnosti' in text_to_search:
        return 'štúdia uskutočniteľnosti'
    elif 'aktualizácia' in text_to_search:
        return 'aktualizácia'
    elif 'stanovisko' in text_to_search:
        return 'stanovisko'
    elif 'správa' in text_to_search:
        return 'správa'
    elif 'metodika' in text_to_search:
        return 'metodika'
    elif 'zmluva' in text_to_search:
        return 'zmluva'
    elif 'dohoda' in text_to_search:
        return 'dohoda'
    elif 'investičný zámer' in text_to_search:
        return 'investičný zámer'
    else:
        # If no specific type found, use the link text itself (truncated)
        return link_text[:50] + "..." if len(link_text) > 50 else link_text

def scrape_sector_page(sector_name, page_url, session):
    """Scrape a single sector page and return list of documents."""
    print(f"\nScraping {sector_name} sector: {page_url}")
    
    try:
        resp = session.get(page_url, timeout=20)
        if resp.status_code != 200:
            print(f"Non-200 status code for {sector_name}: {resp.status_code}")
            return []

        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, "lxml")

        rows = []
        seen = set()
        last_project_name = "UNKNOWN_PROJECT"

        # Loop through all headers and links in order
        for elem in soup.find_all(["h4", "h5", "a"]):
            if elem.name == "h4":
                # Skip h4 headers as we're using sector_name from the URL
                continue
            elif elem.name == "h5":
                last_project_name = elem.get_text(" ", strip=True)
            elif elem.name == "a" and is_pdf_link(elem.get("href"), elem.get_text(" ", strip=True)):
                link_text = elem.get_text(" ", strip=True)

                # Determine type - captures ALL document types
                parent_text = elem.parent.get_text(" ", strip=True) if elem.parent else ""
                dtype = determine_document_type(link_text, parent_text)

                url = urljoin(BASE, elem["href"])
                date, size = extract_date_and_size(elem)

                # Use URL as unique key to avoid duplicates
                key = (sector_name, last_project_name, url)
                if key not in seen:
                    rows.append((sector_name, last_project_name, dtype, url, date or "", size or ""))
                    seen.add(key)

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
        
        # Show some examples of the previously missed document types
        print(f"\nExamples of 'Aktualizácia' documents:")
        aktualizacia_docs = df[df['Type'] == 'aktualizácia']
        if not aktualizacia_docs.empty:
            print(aktualizacia_docs[['Sector', 'Project Name', 'Type', 'Date']].head().to_string(index=False))
        
        print(f"\nExamples of 'Stanovisko' documents:")
        stanovisko_docs = df[df['Type'] == 'stanovisko']
        if not stanovisko_docs.empty:
            print(stanovisko_docs[['Sector', 'Project Name', 'Type', 'Date']].head().to_string(index=False))

    except Exception as e:
        print("Exception occurred:", e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
