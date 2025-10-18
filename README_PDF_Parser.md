# PDF Structured Parser

This tool can parse PDF documents that are organized with:
- **Headers** (Sector names)
- **Project Names** 
- **Document Types** with associated URLs

## Files Created

1. **`pdf_structured_parser.py`** - Basic PDF parser using PyPDF2 and pdfplumber
2. **`pdf_advanced_parser.py`** - Advanced parser using PyMuPDF for better link extraction
3. **`test_pdf_parser.py`** - Test script to verify functionality

## Usage

### Basic Parser
```bash
python3 pdf_structured_parser.py your_document.pdf
```

### Advanced Parser (Recommended)
```bash
python3 pdf_advanced_parser.py your_document.pdf
```

### Test the Parsers
```bash
python3 test_pdf_parser.py
```

## Expected PDF Structure

The parser expects PDFs organized like this:

```
Obrana
  Project Name 1
    hodnotenie (PDF) https://example.com/doc1.pdf
    analýza (PDF) https://example.com/doc2.pdf
  
  Project Name 2
    štúdia uskutočniteľnosti (PDF) https://example.com/doc3.pdf

Budovy
  Project Name 3
    aktualizácia (PDF) https://example.com/doc4.pdf
```

## Output

The parser will create:
- **CSV file** with structured data (Sector, Project Name, Document Type, URL, etc.)
- **Text file** with all URLs found
- **Console output** showing summary statistics

## Features

- **Multiple PDF libraries**: Uses PyPDF2, pdfplumber, and PyMuPDF for robust extraction
- **URL extraction**: Finds URLs both in text and as clickable links
- **Document type detection**: Recognizes Slovak document types (hodnotenie, analýza, etc.)
- **File format detection**: Identifies PDF, Word, Excel, PowerPoint formats
- **Page tracking**: Records which page each document was found on
- **Error handling**: Graceful fallbacks if one method fails

## Dependencies

Required packages (already installed):
- PyPDF2
- pdfplumber  
- PyMuPDF (fitz)
- pandas

## Example Output

```
=== ADVANCED PARSING RESULTS ===
Total structured entries found: 25
Total URLs found in text: 30
Total links found via PyMuPDF: 25

Entries by sector:
  Obrana: 8
  Budovy: 7
  Doprava: 10

Document types found:
  hodnotenie (PDF): 12
  analýza (PDF): 8
  štúdia uskutočniteľnosti (PDF): 5
```

## Troubleshooting

If parsing fails:
1. Check that the PDF contains text (not just images)
2. Verify the PDF structure matches the expected format
3. Try both basic and advanced parsers
4. Check console output for specific error messages

