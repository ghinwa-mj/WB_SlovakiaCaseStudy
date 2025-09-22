import os
import pandas as pd
import PyPDF2
import openpyxl
from docx import Document
import csv
import json
from typing import Union, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_pdf(file_path: str) -> str:
    """
    Read text content from a PDF file.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text content
    """
    try:
        text_content = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content.append(page.extract_text())
        
        return '\n'.join(text_content)
    except Exception as e:
        logger.error(f"Error reading PDF {file_path}: {str(e)}")
        return ""

def read_excel(file_path: str) -> str:
    """
    Read content from an Excel file (.xlsx).
    
    Args:
        file_path (str): Path to the Excel file
        
    Returns:
        str: Extracted content as formatted text
    """
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        content_parts = []
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            content_parts.append(f"Sheet: {sheet_name}")
            content_parts.append(df.to_string())
            content_parts.append("\n" + "="*50 + "\n")
        
        return '\n'.join(content_parts)
    except Exception as e:
        logger.error(f"Error reading Excel {file_path}: {str(e)}")
        return ""

def read_csv(file_path: str) -> str:
    """
    Read content from a CSV file.
    
    Args:
        file_path (str): Path to the CSV file
        
    Returns:
        str: Extracted content as formatted text
    """
    try:
        df = pd.read_csv(file_path)
        return df.to_string()
    except Exception as e:
        logger.error(f"Error reading CSV {file_path}: {str(e)}")
        return ""

def read_docx(file_path: str) -> str:
    """
    Read text content from a Word document (.docx).
    
    Args:
        file_path (str): Path to the Word document
        
    Returns:
        str: Extracted text content
    """
    try:
        doc = Document(file_path)
        text_content = []
        
        for paragraph in doc.paragraphs:
            text_content.append(paragraph.text)
        
        return '\n'.join(text_content)
    except Exception as e:
        logger.error(f"Error reading DOCX {file_path}: {str(e)}")
        return ""

def read_document(file_path: str) -> str:
    """
    Read document content based on file extension.
    
    Args:
        file_path (str): Path to the document file
        
    Returns:
        str: Extracted text content
    """
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return ""
    
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        return read_pdf(file_path)
    elif file_extension in ['.xlsx', '.xls']:
        return read_excel(file_path)
    elif file_extension == '.csv':
        return read_csv(file_path)
    elif file_extension == '.docx':
        return read_docx(file_path)
    else:
        logger.warning(f"Unsupported file type: {file_extension}")
        return ""

def read_all_documents(data_folder: str) -> Dict[str, str]:
    """
    Read all documents in the specified folder.
    
    Args:
        data_folder (str): Path to the folder containing documents
        
    Returns:
        Dict[str, str]: Dictionary mapping filename to content
    """
    documents = {}
    
    if not os.path.exists(data_folder):
        logger.error(f"Data folder does not exist: {data_folder}")
        return documents
    
    for filename in os.listdir(data_folder):
        file_path = os.path.join(data_folder, filename)
        
        if os.path.isfile(file_path):
            logger.info(f"Reading document: {filename}")
            content = read_document(file_path)
            documents[filename] = content
    
    return documents

def save_documents_to_json(documents: Dict[str, str], output_file: str):
    """
    Save document contents to a JSON file.
    
    Args:
        documents (Dict[str, str]): Dictionary mapping filename to content
        output_file (str): Path to output JSON file
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        logger.info(f"Documents saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving to JSON: {str(e)}")

if __name__ == "__main__":
    # Example usage
    data_folder = "Data"
    documents = read_all_documents(data_folder)
    
    # Print summary
    print(f"Successfully read {len(documents)} documents:")
    for filename, content in documents.items():
        print(f"- {filename}: {len(content)} characters")
    
    # Save to JSON file
    save_documents_to_json(documents, "documents_content.json")
