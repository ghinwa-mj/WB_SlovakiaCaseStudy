#!/usr/bin/env python3
"""
Sentiment Analysis Comparison Script

This script extracts a random subset of 50 files from project_summary.csv,
reads their corresponding PDFs, and runs recommendation analysis using
8 different AI models to compare responses and calculate costs.
"""

import pandas as pd
import random
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

class AIRecommendationAnalyzer:
    """Analyze project recommendations using different AI models"""
    
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
                return {'recommendation': 'Parse Error', 'recommendation_description': f'Could not find JSON in {model_name} response'}
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {model_name}: {e}")
            logger.error(f"Content that failed to parse: {content[:500]}...")
            # Save unparseable response
            self.unparseable_responses.append({
                'model': model_name,
                'content': content,
                'error': f'JSON parsing failed: {str(e)}'
            })
            return {'recommendation': 'Parse Error', 'recommendation_description': f'JSON parsing failed: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected error parsing {model_name} response: {e}")
            # Save unparseable response
            self.unparseable_responses.append({
                'model': model_name,
                'content': content,
                'error': f'Unexpected parsing error: {str(e)}'
            })
            return {'recommendation': 'Parse Error', 'recommendation_description': f'Unexpected parsing error: {str(e)}'}

    async def analyze_all_models(self, project_name: str, document_id: str, pdf_text: str) -> Dict:
        """Run analysis on all AI models in parallel"""
        prompt = self.create_prompt(project_name, document_id, pdf_text)
        
        # Create tasks for all models
        tasks = []
        model_names = []
        
        for model_name, config in self.model_configs.items():
            provider = config['provider']
            
            if provider == 'openai':
                tasks.append(self.analyze_with_openai(prompt, model_name))
            elif provider == 'mistral':
                tasks.append(self.analyze_with_mistral(prompt, model_name))
            elif provider == 'claude':
                tasks.append(self.analyze_with_claude(prompt, model_name))
            elif provider == 'gemini':
                tasks.append(self.analyze_with_gemini(prompt, model_name))
            
            model_names.append(model_name)
        
        # Run all analyses in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results with model names
        combined_results = {}
        for i, result in enumerate(results):
            model_name = model_names[i]
            if isinstance(result, Exception):
                combined_results[model_name] = {
                    'recommendation': 'Error', 
                    'recommendation_description': str(result),
                    'input_cost': 0,
                    'output_cost': 0,
                    'total_cost': 0,
                    'input_tokens': 0,
                    'output_tokens': 0
                }
            else:
                combined_results[model_name] = result
        
        return combined_results

class SentimentAnalysisProcessor:
    """Main processor for sentiment analysis comparison"""
    
    def __init__(self, project_summary_path: str, pdf_folder_path: str):
        self.project_summary_path = project_summary_path
        self.pdf_folder_path = pdf_folder_path
        self.analyzer = AIRecommendationAnalyzer()
        self.pdf_extractor = PDFTextExtractor()
        
    def load_project_data(self) -> pd.DataFrame:
        """Load project summary data"""
        try:
            df = pd.read_csv(self.project_summary_path)
            logger.info(f"Loaded {len(df)} projects from {self.project_summary_path}")
            return df
        except Exception as e:
            logger.error(f"Error loading project data: {e}")
            raise
    
    def select_random_projects(self, df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
        """Select random subset of projects"""
        if len(df) < n:
            logger.warning(f"Only {len(df)} projects available, selecting all")
            return df
        
        selected = df.sample(n=n, random_state=42)  # Fixed seed for reproducibility
        logger.info(f"Selected {len(selected)} random projects")
        return selected
    
    def get_pdf_path(self, document_id: str) -> str:
        """Get the path to the PDF file"""
        return os.path.join(self.pdf_folder_path, f"{document_id}.pdf")
    
    async def process_project(self, row: pd.Series) -> Dict:
        """Process a single project"""
        project_name = row['Project_Name']
        document_id = row['First_File_Document_ID']
        
        logger.info(f"Processing project: {project_name} (ID: {document_id})")
        
        # Get PDF path and extract text
        pdf_path = self.get_pdf_path(document_id)
        
        if not os.path.exists(pdf_path):
            logger.warning(f"PDF not found: {pdf_path}")
            return {
                'project_name': project_name,
                'document_id': document_id,
                'error': 'PDF not found',
                'analyses': {}
            }
        
        # Extract text from PDF
        pdf_text = self.pdf_extractor.extract_text_from_pdf(pdf_path)
        
        if not pdf_text.strip():
            logger.warning(f"No text extracted from {pdf_path}")
            return {
                'project_name': project_name,
                'document_id': document_id,
                'error': 'No text extracted',
                'analyses': {}
            }
        
        # Run AI analysis
        try:
            analyses = await self.analyzer.analyze_all_models(project_name, document_id, pdf_text)
            return {
                'project_name': project_name,
                'document_id': document_id,
                'error': None,
                'analyses': analyses
            }
        except Exception as e:
            logger.error(f"Error analyzing {document_id}: {e}")
            return {
                'project_name': project_name,
                'document_id': document_id,
                'error': str(e),
                'analyses': {}
            }
    
    async def process_all_projects(self, selected_projects: pd.DataFrame) -> List[Dict]:
        """Process all selected projects"""
        results = []
        
        for idx, row in selected_projects.iterrows():
            try:
                result = await self.process_project(row)
                results.append(result)
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing project {idx}: {e}")
                results.append({
                    'project_name': row['Project_Name'],
                    'document_id': row['First_File_Document_ID'],
                    'error': str(e),
                    'analyses': {}
                })
        
        return results
    
    def save_results(self, results: List[Dict], output_path: str):
        """Save results to CSV file"""
        # Flatten results for CSV output
        flattened_results = []
        
        for result in results:
            base_data = {
                'Project_Name': result['project_name'],
                'Document_ID': result['document_id'],
                'Error': result['error']
            }
            
            if result['analyses']:
                for model_name, analysis in result['analyses'].items():
                    flattened_results.append({
                        **base_data,
                        'Model': model_name,
                        'Recommendation': analysis.get('recommendation', 'Not specified'),
                        'Recommendation_Reasoning': analysis.get('recommendation_description', 'No description'),
                        'Input_Tokens': analysis.get('input_tokens', 0),
                        'Output_Tokens': analysis.get('output_tokens', 0),
                        'Input_Cost': analysis.get('input_cost', 0),
                        'Output_Cost': analysis.get('output_cost', 0),
                        'Total_Cost': analysis.get('total_cost', 0)
                    })
            else:
                # Add row even if no analyses
                flattened_results.append({
                    **base_data,
                    'Model': 'N/A',
                    'Recommendation': 'N/A',
                    'Recommendation_Reasoning': 'N/A',
                    'Input_Tokens': 0,
                    'Output_Tokens': 0,
                    'Input_Cost': 0,
                    'Output_Cost': 0,
                    'Total_Cost': 0
                })
        
        # Create DataFrame and save
        df_results = pd.DataFrame(flattened_results)
        df_results.to_csv(output_path, index=False)
        logger.info(f"Results saved to {output_path}")
        
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

async def test_trial():
    """Test trial to verify all models work with minimal prompt"""
    logger.info("Starting test trial with minimal prompt...")
    
    # Create analyzer
    analyzer = AIRecommendationAnalyzer()
    
    # Simple test prompt
    test_prompt = """Analyze this project assessment text and extract the recommendation information.

Project Text: "This project shows positive results and should be approved. The cost-benefit analysis demonstrates clear economic benefits."

Please extract the recommendation and provide reasoning. Return ONLY a JSON response in this exact format:
{
    "recommendation": "Positive",
    "recommendation_description": "The project shows positive results and should be approved based on clear economic benefits"
}"""
    
    logger.info("Testing all models...")
    results = await analyzer.analyze_all_models("Test Project", "test_doc", test_prompt)
    
    # Print results
    logger.info("Test trial results:")
    total_cost = 0
    for model_name, result in results.items():
        logger.info(f"\n{model_name}:")
        logger.info(f"  Recommendation: {result.get('recommendation', 'N/A')}")
        logger.info(f"  Input Tokens: {result.get('input_tokens', 0)}")
        logger.info(f"  Output Tokens: {result.get('output_tokens', 0)}")
        logger.info(f"  Total Cost: ${result.get('total_cost', 0):.6f}")
        total_cost += result.get('total_cost', 0)
    
    logger.info(f"\nTotal test cost: ${total_cost:.6f}")
    logger.info("Test trial completed!")
    
    return results

async def main():
    """Main execution function"""
    # Configuration
    project_summary_path = "/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Outputs/project_summary.csv"
    pdf_folder_path = "/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/downloaded_first_links"
    output_path = f"/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/sentiment_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Initialize processor
    processor = SentimentAnalysisProcessor(project_summary_path, pdf_folder_path)
    
    try:
        # Load and select projects
        logger.info("Loading project data...")
        df = processor.load_project_data()
        
        logger.info("Selecting random projects...")
        selected_projects = processor.select_random_projects(df, n=50)
        
        # Log selected projects
        logger.info("Selected projects:")
        for idx, row in selected_projects.iterrows():
            logger.info(f"  {row['Project_Name']} (ID: {row['First_File_Document_ID']})")
        
        # Process all projects
        logger.info("Starting analysis...")
        results = await processor.process_all_projects(selected_projects)
        
        # Save results
        logger.info("Saving results...")
        processor.save_results(results, output_path)
        
        # Print summary
        successful = sum(1 for r in results if r['error'] is None)
        logger.info(f"Analysis complete! {successful}/{len(results)} projects processed successfully")
        
        # Calculate total costs
        total_cost_by_model = {}
        for result in results:
            if result['analyses']:
                for model_name, analysis in result['analyses'].items():
                    if model_name not in total_cost_by_model:
                        total_cost_by_model[model_name] = 0
                    total_cost_by_model[model_name] += analysis.get('total_cost', 0)
        
        logger.info("\nTotal costs by model:")
        grand_total = 0
        for model_name, cost in total_cost_by_model.items():
            logger.info(f"  {model_name}: ${cost:.6f}")
            grand_total += cost
        
        logger.info(f"\nGrand total cost: ${grand_total:.6f}")
        
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run test trial
        asyncio.run(test_trial())
    else:
        # Run full analysis
        asyncio.run(main())
