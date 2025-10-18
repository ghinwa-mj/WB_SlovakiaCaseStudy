#!/usr/bin/env python3
"""
GPT-5.1 Sentiment Analysis Script

This script reads the existing sentiment analysis results CSV file,
extracts unique projects, and runs the same prompt using GPT-5.1
to generate new recommendations for comparison.
"""

import pandas as pd
import os
import json
import asyncio
import aiohttp
import PyPDF2
from pathlib import Path
import sys
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import re

# Import API keys
sys.path.append('/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Sentiment Analysis Experiment')
from apikeys import open_ai_api_key

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFTextExtractor:
    """Extract text from PDF files"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Extract text from a PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""

class GPT51Analyzer:
    """Analyze project recommendations using GPT-5.1"""
    
    def __init__(self):
        self.api_key = open_ai_api_key
        
    def create_prompt(self, project_name: str, document_id: str, pdf_text: str) -> str:
        """Create the analysis prompt focusing on recommendation and reasoning"""
        return f"""This document is an assessment of a Cost Benefit Analysis project in Slovak language. 
        Read through the document and extract the following information - Extract only in JSON file. 
        Make sure that the responses come from the document and do not make anything up.

        Project Name: {project_name}
        Document ID: {document_id}

        Document Text:
        {pdf_text}

        Please extract:
        - Positive/Negative/Neutral Recommendation of the Project - Provide some additional information about the recommendation to support the answer

        All responses should be in English. Return the response in JSON format with these exact keys:
        {{
            "recommendation": "Positive/Negative/Neutral",
            "recommendation_description": "Additional information about the recommendation to support the answer"
        }}"""

    async def analyze_with_gpt51(self, prompt: str) -> Dict:
        """Analyze using OpenAI GPT-5.1"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-5-2025-08-07',
                'messages': [{'role': 'user', 'content': prompt}]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post('https://api.openai.com/v1/chat/completions', 
                                      headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        return self._parse_json_response(content, 'GPT-5.1')
                    else:
                        error_text = await response.text()
                        logger.error(f"GPT-5.1 API error: {response.status} - {error_text}")
                        return {'recommendation': 'Error', 'recommendation_description': f'API Error: {response.status}'}
        except Exception as e:
            logger.error(f"GPT-5.1 analysis error: {e}")
            return {'recommendation': 'Error', 'recommendation_description': str(e)}

    def _parse_json_response(self, content: str, model_name: str) -> Dict:
        """Parse JSON response from AI model"""
        try:
            # Clean the content to remove control characters and extra whitespace
            cleaned_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
            
            # Try to extract JSON from the response
            if '{' in cleaned_content and '}' in cleaned_content:
                start = cleaned_content.find('{')
                end = cleaned_content.rfind('}') + 1
                json_str = cleaned_content[start:end]
                
                # Try to parse the JSON with relaxed parsing for control characters
                result = json.loads(json_str, strict=False)
                
                # Ensure required keys exist
                if 'recommendation' not in result:
                    result['recommendation'] = 'Not specified'
                if 'recommendation_description' not in result:
                    result['recommendation_description'] = 'No description provided'
                    
                return result
            else:
                logger.warning(f"No JSON found in {model_name} response: {content[:200]}...")
                return {'recommendation': 'Parse Error', 'recommendation_description': f'Could not find JSON in {model_name} response'}
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {model_name}: {e}")
            logger.error(f"Content that failed to parse: {content[:500]}...")
            return {'recommendation': 'Parse Error', 'recommendation_description': f'JSON parsing failed: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected error parsing {model_name} response: {e}")
            return {'recommendation': 'Parse Error', 'recommendation_description': f'Unexpected parsing error: {str(e)}'}

class GPT51Processor:
    """Main processor for GPT-5.1 sentiment analysis"""
    
    def __init__(self, csv_path: str, pdf_folder_path: str):
        self.csv_path = csv_path
        self.pdf_folder_path = pdf_folder_path
        self.analyzer = GPT51Analyzer()
        self.pdf_extractor = PDFTextExtractor()
        
    def load_existing_results(self) -> pd.DataFrame:
        """Load existing sentiment analysis results"""
        try:
            df = pd.read_csv(self.csv_path)
            logger.info(f"Loaded {len(df)} records from {self.csv_path}")
            return df
        except Exception as e:
            logger.error(f"Error loading existing results: {e}")
            raise
    
    def get_unique_projects(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique projects from the existing results"""
        # Group by Document_ID and Project_Name to get unique projects
        unique_projects = df.groupby(['Document_ID', 'Project_Name']).first().reset_index()
        logger.info(f"Found {len(unique_projects)} unique projects")
        return unique_projects
    
    def get_pdf_path(self, document_id: str) -> str:
        """Get the path to the PDF file"""
        return os.path.join(self.pdf_folder_path, f"{document_id}.pdf")
    
    async def process_project(self, row: pd.Series) -> Dict:
        """Process a single project"""
        project_name = row['Project_Name']
        document_id = row['Document_ID']
        
        logger.info(f"Processing project: {project_name} (ID: {document_id})")
        
        # Get PDF path and extract text
        pdf_path = self.get_pdf_path(document_id)
        
        if not os.path.exists(pdf_path):
            logger.warning(f"PDF not found: {pdf_path}")
            return {
                'project_name': project_name,
                'document_id': document_id,
                'error': 'PDF not found',
                'analysis': {}
            }
        
        # Extract text from PDF
        pdf_text = self.pdf_extractor.extract_text_from_pdf(pdf_path)
        
        if not pdf_text.strip():
            logger.warning(f"No text extracted from {pdf_path}")
            return {
                'project_name': project_name,
                'document_id': document_id,
                'error': 'No text extracted',
                'analysis': {}
            }
        
        # Run GPT-5.1 analysis
        try:
            prompt = self.analyzer.create_prompt(project_name, document_id, pdf_text)
            analysis = await self.analyzer.analyze_with_gpt51(prompt)
            return {
                'project_name': project_name,
                'document_id': document_id,
                'error': None,
                'analysis': analysis
            }
        except Exception as e:
            logger.error(f"Error analyzing {document_id}: {e}")
            return {
                'project_name': project_name,
                'document_id': document_id,
                'error': str(e),
                'analysis': {}
            }
    
    async def process_all_projects(self, unique_projects: pd.DataFrame) -> List[Dict]:
        """Process all unique projects"""
        results = []
        
        for idx, row in unique_projects.iterrows():
            try:
                result = await self.process_project(row)
                results.append(result)
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing project {idx}: {e}")
                results.append({
                    'project_name': row['Project_Name'],
                    'document_id': row['Document_ID'],
                    'error': str(e),
                    'analysis': {}
                })
        
        return results
    
    def save_results(self, results: List[Dict], output_path: str):
        """Save results to CSV file in the same format as the original"""
        # Flatten results for CSV output
        flattened_results = []
        
        for result in results:
            base_data = {
                'Project_Name': result['project_name'],
                'Document_ID': result['document_id'],
                'Error': result['error'] if result['error'] else '',
                'Model': 'GPT-5.1',
                'Recommendation': result['analysis'].get('recommendation', 'Not specified') if result['analysis'] else 'N/A',
                'Recommendation_Reasoning': result['analysis'].get('recommendation_description', 'No description') if result['analysis'] else 'N/A'
            }
            
            flattened_results.append(base_data)
        
        # Create DataFrame and save
        df_results = pd.DataFrame(flattened_results)
        df_results.to_csv(output_path, index=False)
        logger.info(f"Results saved to {output_path}")
        
        # Also save detailed JSON results
        json_path = output_path.replace('.csv', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Detailed results saved to {json_path}")

async def main():
    """Main execution function"""
    # Configuration
    csv_path = "/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Sentiment Analysis Experiment/sentiment_analysis_results_20250929_103309.csv"
    pdf_folder_path = "/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/downloaded_first_links"
    output_path = f"/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Sentiment Analysis Experiment/gpt51_sentiment_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Initialize processor
    processor = GPT51Processor(csv_path, pdf_folder_path)
    
    try:
        # Load existing results
        logger.info("Loading existing sentiment analysis results...")
        df = processor.load_existing_results()
        
        # Extract unique projects
        logger.info("Extracting unique projects...")
        unique_projects = processor.get_unique_projects(df)
        
        # Log unique projects
        logger.info("Unique projects to analyze:")
        for idx, row in unique_projects.iterrows():
            logger.info(f"  {row['Project_Name']} (ID: {row['Document_ID']})")
        
        # Process all projects
        logger.info("Starting GPT-5.1 analysis...")
        results = await processor.process_all_projects(unique_projects)
        
        # Save results
        logger.info("Saving results...")
        processor.save_results(results, output_path)
        
        # Print summary
        successful = sum(1 for r in results if r['error'] is None)
        logger.info(f"Analysis complete! {successful}/{len(results)} projects processed successfully")
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
