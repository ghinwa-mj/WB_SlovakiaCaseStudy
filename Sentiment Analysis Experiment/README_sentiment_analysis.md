# Sentiment Analysis Comparison Script

## Overview
This script analyzes project recommendations from Slovak Cost Benefit Analysis documents using 4 different AI models (OpenAI, Mistral, Claude, Gemini) and compares their responses.

## Features
- Randomly selects 30 projects from `project_summary.csv`
- Extracts text from corresponding PDFs in `downloaded_first_links` folder
- Runs recommendation analysis using 4 AI models in parallel
- Outputs results in CSV format for easy comparison
- Includes error handling and logging

## Installation
```bash
pip install -r requirements_sentiment.txt
```

## Usage
```bash
python sentiment_analysis_comparison.py
```

## Output Format
The script generates two files:
1. `sentiment_analysis_results_YYYYMMDD_HHMMSS.csv` - Main results in CSV format
2. `sentiment_analysis_results_YYYYMMDD_HHMMSS.json` - Detailed JSON results

### CSV Columns:
- Project_Name: Name of the project
- Document_ID: Document identifier
- Error: Any errors encountered (if any)
- Model: AI model used (OpenAI, Mistral, Claude, Gemini)
- Recommendation: Positive/Negative/Neutral recommendation
- Recommendation_Reasoning: Detailed reasoning behind the recommendation

## Configuration
- API keys are loaded from `Sentiment Analysis Experiment/apikeys.py`
- PDF folder path: `downloaded_first_links/`
- Project data: `project_summary.csv`
- Random seed: 42 (for reproducible results)

## Notes
- Text is truncated to 8000 characters to avoid token limits
- 1-second delay between projects to avoid rate limiting
- All responses are in English as requested
- Focuses only on recommendation and reasoning (as specified)
