#!/usr/bin/env python3
"""
Error Re-run Script

This script processes the error_reRun.csv file and re-runs specific model-document combinations
that failed in the original analysis. For parse errors, it saves the unparseable response
in the Recommendation field for manual parsing.
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
import anthropic
import google.generativeai as genai
import tiktoken

# Import API keys
sys.path.append('/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Sentiment Analysis Experiment')
from apikeys import open_ai_api_key, mistal_api_key, claude_api_key, gemini_api_key

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

class ErrorRerunAnalyzer:
    """Re-run analysis for specific model-document combinations"""
    
    def __init__(self):
        self.api_keys = {
            'openai': open_ai_api_key,
            'mistral': mistal_api_key,
            'claude': claude_api_key,
            'gemini': gemini_api_key
        }
        
        # Model configurations with pricing (per 1M tokens)
        self.model_configs = {
            'gpt-5-2025-08-07': {
                'provider': 'openai',
                'input_price': 1.25,
                'output_price': 10.0,
                'model_name': 'gpt-5-2025-08-07'
            },
            'gpt-5-mini-2025-08-07': {
                'provider': 'openai',
                'input_price': 0.25,
                'output_price': 2.0,
                'model_name': 'gpt-5-mini-2025-08-07'
            },
            'gpt-4.1': {
                'provider': 'openai',
                'input_price': 3.0,
                'output_price': 12.0,
                'model_name': 'gpt-4.1'
            },
            'mistral-large-latest': {
                'provider': 'mistral',
                'input_price': 2.0,
                'output_price': 6.0,
                'model_name': 'mistral-large-latest'
            },
            'claude-opus-4-1-20250805': {
                'provider': 'claude',
                'input_price': 15.0,
                'output_price': 75.0,
                'model_name': 'claude-opus-4-1-20250805'
            },
            'claude-sonnet-4-5': {
                'provider': 'claude',
                'input_price': 3.0,
                'output_price': 15.0,
                'model_name': 'claude-sonnet-4-5'
            },
            'gemini-2.5-flash-lite': {
                'provider': 'gemini',
                'input_price': 0.1,
                'output_price': 0.4,
                'model_name': 'gemini-2.5-flash-lite'
            },
            'gemini-2.5-pro': {
                'provider': 'gemini',
                'input_price': 1.25,  # For prompts <= 200k tokens
                'output_price': 10.0,  # For prompts <= 200k tokens
                'model_name': 'gemini-2.5-pro'
            }
        }
        
        # Initialize SDK clients
        self.claude_client = anthropic.Anthropic(api_key=claude_api_key)
        genai.configure(api_key=gemini_api_key)
        self.gemini_flash_model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.gemini_pro_model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Initialize tiktoken for token counting
        try:
            self.tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
        except:
            self.tiktoken_encoder = None
        
        # Store unparseable responses for debugging
        self.unparseable_responses = []
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        if self.tiktoken_encoder:
            return len(self.tiktoken_encoder.encode(text))
        else:
            # Fallback: rough estimation (4 characters per token)
            return len(text) // 4
    
    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> Dict:
        """Calculate cost based on token usage"""
        config = self.model_configs.get(model_name, {})
        if not config:
            return {'input_cost': 0, 'output_cost': 0, 'total_cost': 0}
        
        input_cost = (input_tokens / 1_000_000) * config['input_price']
        output_cost = (output_tokens / 1_000_000) * config['output_price']
        total_cost = input_cost + output_cost
        
        return {
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        }
    
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

    async def analyze_with_openai(self, prompt: str, model_name: str) -> Dict:
        """Analyze using OpenAI models"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_keys["openai"]}',
                'Content-Type': 'application/json'
            }
            
            # GPT-5 models only support temperature=1 (default)
            temperature = 1.0 if 'gpt-5' in model_name else 0.1
            
            data = {
                'model': model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': temperature
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post('https://api.openai.com/v1/chat/completions', 
                                      headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Extract token usage
                        usage = result.get('usage', {})
                        input_tokens = usage.get('prompt_tokens', self.count_tokens(prompt))
                        output_tokens = usage.get('completion_tokens', self.count_tokens(content))
                        
                        # Calculate cost
                        cost_info = self.calculate_cost(model_name, input_tokens, output_tokens)
                        
                        parsed_response = self._parse_json_response(content, model_name)
                        parsed_response.update(cost_info)
                        
                        return parsed_response
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenAI API error for {model_name}: {response.status} - {error_text}")
                        return {'recommendation': 'Error', 'recommendation_description': f'API Error: {response.status}'}
        except Exception as e:
            logger.error(f"OpenAI analysis error for {model_name}: {e}")
            return {'recommendation': 'Error', 'recommendation_description': str(e)}

    async def analyze_with_mistral(self, prompt: str, model_name: str) -> Dict:
        """Analyze using Mistral AI"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_keys["mistral"]}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens': 1000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post('https://api.mistral.ai/v1/chat/completions', 
                                      headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Extract token usage
                        usage = result.get('usage', {})
                        input_tokens = usage.get('prompt_tokens', self.count_tokens(prompt))
                        output_tokens = usage.get('completion_tokens', self.count_tokens(content))
                        
                        # Calculate cost
                        cost_info = self.calculate_cost(model_name, input_tokens, output_tokens)
                        
                        parsed_response = self._parse_json_response(content, model_name)
                        parsed_response.update(cost_info)
                        
                        return parsed_response
                    else:
                        error_text = await response.text()
                        logger.error(f"Mistral API error for {model_name}: {response.status} - {error_text}")
                        return {'recommendation': 'Error', 'recommendation_description': f'API Error: {response.status}'}
        except Exception as e:
            logger.error(f"Mistral analysis error for {model_name}: {e}")
            return {'recommendation': 'Error', 'recommendation_description': str(e)}

    async def analyze_with_claude(self, prompt: str, model_name: str) -> Dict:
        """Analyze using Claude AI with official SDK"""
        try:
            response = self.claude_client.messages.create(
                model=model_name,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8000
            )
            
            content = response.content[0].text
            
            # Extract token usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            # Calculate cost
            cost_info = self.calculate_cost(model_name, input_tokens, output_tokens)
            
            parsed_response = self._parse_json_response(content, model_name)
            parsed_response.update(cost_info)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Claude analysis error for {model_name}: {e}")
            return {'recommendation': 'Error', 'recommendation_description': str(e)}

    async def analyze_with_gemini(self, prompt: str, model_name: str) -> Dict:
        """Analyze using Google Gemini with official SDK"""
        try:
            # Select the appropriate Gemini model
            if model_name == 'gemini-2.5-flash-lite':
                model = self.gemini_flash_model
            elif model_name == 'gemini-2.5-pro':
                model = self.gemini_pro_model
            else:
                raise ValueError(f"Unknown Gemini model: {model_name}")
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1
                )
            )
            
            content = response.text
            
            # Gemini doesn't provide token usage in response, so estimate
            input_tokens = self.count_tokens(prompt)
            output_tokens = self.count_tokens(content)
            
            # Calculate cost
            cost_info = self.calculate_cost(model_name, input_tokens, output_tokens)
            
            parsed_response = self._parse_json_response(content, model_name)
            parsed_response.update(cost_info)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Gemini analysis error for {model_name}: {e}")
            return {'recommendation': 'Error', 'recommendation_description': str(e)}

    def _parse_json_response(self, content: str, model_name: str) -> Dict:
        """Parse JSON response from AI model"""
        try:
            # Clean the content to remove control characters and extra whitespace
            import re
            # Remove control characters except newlines and tabs
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
                # Save unparseable response
                self.unparseable_responses.append({
                    'model': model_name,
                    'content': content,
                    'error': 'No JSON found'
                })
                return {'recommendation': content, 'recommendation_description': 'Raw response (no JSON found)'}
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {model_name}: {e}")
            logger.error(f"Content that failed to parse: {content[:500]}...")
            # Save unparseable response
            self.unparseable_responses.append({
                'model': model_name,
                'content': content,
                'error': f'JSON parsing failed: {str(e)}'
            })
            return {'recommendation': content, 'recommendation_description': f'Raw response (JSON parsing failed: {str(e)})'}
        except Exception as e:
            logger.error(f"Unexpected error parsing {model_name} response: {e}")
            # Save unparseable response
            self.unparseable_responses.append({
                'model': model_name,
                'content': content,
                'error': f'Unexpected parsing error: {str(e)}'
            })
            return {'recommendation': content, 'recommendation_description': f'Raw response (Unexpected parsing error: {str(e)})'}

    async def analyze_single_model(self, project_name: str, document_id: str, pdf_text: str, model_name: str) -> Dict:
        """Run analysis on a single model for a specific document"""
        prompt = self.create_prompt(project_name, document_id, pdf_text)
        
        config = self.model_configs.get(model_name, {})
        if not config:
            return {'recommendation': 'Error', 'recommendation_description': f'Unknown model: {model_name}'}
        
        provider = config['provider']
        
        if provider == 'openai':
            return await self.analyze_with_openai(prompt, model_name)
        elif provider == 'mistral':
            return await self.analyze_with_mistral(prompt, model_name)
        elif provider == 'claude':
            return await self.analyze_with_claude(prompt, model_name)
        elif provider == 'gemini':
            return await self.analyze_with_gemini(prompt, model_name)
        else:
            return {'recommendation': 'Error', 'recommendation_description': f'Unknown provider: {provider}'}

class ErrorRerunProcessor:
    """Main processor for error re-run analysis"""
    
    def __init__(self, error_csv_path: str, pdf_folder_path: str):
        self.error_csv_path = error_csv_path
        self.pdf_folder_path = pdf_folder_path
        self.analyzer = ErrorRerunAnalyzer()
        self.pdf_extractor = PDFTextExtractor()
        
    def load_error_data(self) -> pd.DataFrame:
        """Load error re-run data"""
        try:
            df = pd.read_csv(self.error_csv_path)
            logger.info(f"Loaded {len(df)} error cases from {self.error_csv_path}")
            return df
        except Exception as e:
            logger.error(f"Error loading error data: {e}")
            raise
    
    def get_pdf_path(self, document_id: str) -> str:
        """Get the path to the PDF file"""
        return os.path.join(self.pdf_folder_path, f"{document_id}.pdf")
    
    async def process_error_case(self, row: pd.Series) -> Dict:
        """Process a single error case"""
        project_name = row['Project_Name']
        document_id = row['Document_ID']
        model_name = row['Model']
        
        logger.info(f"Re-running: {project_name} (ID: {document_id}) with {model_name}")
        
        # Get PDF path and extract text
        pdf_path = self.get_pdf_path(document_id)
        
        if not os.path.exists(pdf_path):
            logger.warning(f"PDF not found: {pdf_path}")
            return {
                'Project_Name': project_name,
                'Document_ID': document_id,
                'Model': model_name,
                'Error': 'PDF not found',
                'Recommendation': 'N/A',
                'Recommendation_Reasoning': 'N/A',
                'Input_Tokens': 0,
                'Output_Tokens': 0,
                'Input_Cost': 0,
                'Output_Cost': 0,
                'Total_Cost': 0
            }
        
        # Extract text from PDF
        pdf_text = self.pdf_extractor.extract_text_from_pdf(pdf_path)
        
        if not pdf_text.strip():
            logger.warning(f"No text extracted from {pdf_path}")
            return {
                'Project_Name': project_name,
                'Document_ID': document_id,
                'Model': model_name,
                'Error': 'No text extracted',
                'Recommendation': 'N/A',
                'Recommendation_Reasoning': 'N/A',
                'Input_Tokens': 0,
                'Output_Tokens': 0,
                'Input_Cost': 0,
                'Output_Cost': 0,
                'Total_Cost': 0
            }
        
        # Run AI analysis
        try:
            analysis = await self.analyzer.analyze_single_model(project_name, document_id, pdf_text, model_name)
            
            return {
                'Project_Name': project_name,
                'Document_ID': document_id,
                'Model': model_name,
                'Error': None,
                'Recommendation': analysis.get('recommendation', 'Not specified'),
                'Recommendation_Reasoning': analysis.get('recommendation_description', 'No description'),
                'Input_Tokens': analysis.get('input_tokens', 0),
                'Output_Tokens': analysis.get('output_tokens', 0),
                'Input_Cost': analysis.get('input_cost', 0),
                'Output_Cost': analysis.get('output_cost', 0),
                'Total_Cost': analysis.get('total_cost', 0)
            }
        except Exception as e:
            logger.error(f"Error analyzing {document_id} with {model_name}: {e}")
            return {
                'Project_Name': project_name,
                'Document_ID': document_id,
                'Model': model_name,
                'Error': str(e),
                'Recommendation': 'N/A',
                'Recommendation_Reasoning': 'N/A',
                'Input_Tokens': 0,
                'Output_Tokens': 0,
                'Input_Cost': 0,
                'Output_Cost': 0,
                'Total_Cost': 0
            }
    
    async def process_all_errors(self, error_df: pd.DataFrame) -> List[Dict]:
        """Process all error cases"""
        results = []
        
        for idx, row in error_df.iterrows():
            try:
                result = await self.process_error_case(row)
                results.append(result)
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing case {idx}: {e}")
                results.append({
                    'Project_Name': row['Project_Name'],
                    'Document_ID': row['Document_ID'],
                    'Model': row['Model'],
                    'Error': str(e),
                    'Recommendation': 'N/A',
                    'Recommendation_Reasoning': 'N/A',
                    'Input_Tokens': 0,
                    'Output_Tokens': 0,
                    'Input_Cost': 0,
                    'Output_Cost': 0,
                    'Total_Cost': 0
                })
        
        return results
    
    def save_results(self, results: List[Dict], output_path: str):
        """Save results to CSV file"""
        # Create DataFrame and save
        df_results = pd.DataFrame(results)
        df_results.to_csv(output_path, index=False)
        logger.info(f"Re-run results saved to {output_path}")
        
        # Also save detailed JSON results
        json_path = output_path.replace('.csv', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Detailed results saved to {json_path}")
        
        # Save unparseable responses if any
        if self.analyzer.unparseable_responses:
            unparseable_path = output_path.replace('.csv', '_unparseable_responses.json')
            with open(unparseable_path, 'w', encoding='utf-8') as f:
                json.dump(self.analyzer.unparseable_responses, f, ensure_ascii=False, indent=2)
            logger.info(f"Unparseable responses saved to {unparseable_path}")

async def main():
    """Main execution function"""
    # Configuration
    error_csv_path = "/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Sentiment Analysis Experiment/error_reRun.csv"
    pdf_folder_path = "/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/downloaded_first_links"
    output_path = f"/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Sentiment Analysis Experiment/error_rerun_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Initialize processor
    processor = ErrorRerunProcessor(error_csv_path, pdf_folder_path)
    
    try:
        # Load error data
        logger.info("Loading error data...")
        error_df = processor.load_error_data()
        
        # Log error cases
        logger.info("Error cases to re-run:")
        for idx, row in error_df.iterrows():
            logger.info(f"  {row['Project_Name']} (ID: {row['Document_ID']}) - {row['Model']}")
        
        # Process all error cases
        logger.info("Starting re-run analysis...")
        results = await processor.process_all_errors(error_df)
        
        # Save results
        logger.info("Saving results...")
        processor.save_results(results, output_path)
        
        # Print summary
        successful = sum(1 for r in results if r['Error'] is None)
        logger.info(f"Re-run complete! {successful}/{len(results)} cases processed successfully")
        
        # Calculate total costs
        total_cost_by_model = {}
        for result in results:
            model_name = result['Model']
            if model_name not in total_cost_by_model:
                total_cost_by_model[model_name] = 0
            total_cost_by_model[model_name] += result.get('Total_Cost', 0)
        
        logger.info("\nTotal costs by model:")
        grand_total = 0
        for model_name, cost in total_cost_by_model.items():
            logger.info(f"  {model_name}: ${cost:.6f}")
            grand_total += cost
        
        logger.info(f"\nGrand total re-run cost: ${grand_total:.6f}")
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
