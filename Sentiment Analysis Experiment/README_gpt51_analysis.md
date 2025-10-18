# GPT-5.1 Sentiment Analysis Script

This script reads the existing sentiment analysis results from `sentiment_analysis_results_20250929_103309.csv` and runs the same prompt using GPT-5.1 to generate new recommendations for comparison.

## Features

- **Reads existing results**: Loads the CSV file with 200 records (50 unique projects × 4 models)
- **Extracts unique projects**: Identifies 50 unique projects from the existing data
- **PDF text extraction**: Reads corresponding PDF files from `downloaded_first_links` folder
- **GPT-5.1 analysis**: Uses the same prompt as the original analysis
- **Same output format**: Saves results in the same CSV format as the original file

## Files

- `gpt51_sentiment_analysis.py` - Main script
- `test_gpt51_setup.py` - Test script to verify setup
- `apikeys.py` - Contains OpenAI API key

## Usage

### 1. Test Setup
```bash
cd "/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Sentiment Analysis Experiment"
source ../wb_venv/bin/activate
python3 test_gpt51_setup.py
```

### 2. Run GPT-5.1 Analysis
```bash
cd "/Users/ghinwamoujaes/Desktop/World Bank/Code/slovakia_CaseStudy/Sentiment Analysis Experiment"
source ../wb_venv/bin/activate
python3 gpt51_sentiment_analysis.py
```

## Output

The script will create:
- `gpt51_sentiment_analysis_results_YYYYMMDD_HHMMSS.csv` - Results in same format as original
- `gpt51_sentiment_analysis_results_YYYYMMDD_HHMMSS.json` - Detailed JSON results

## CSV Format

The output CSV will have the same columns as the original:
- `Project_Name` - Name of the project
- `Document_ID` - Document identifier
- `Error` - Any errors encountered (empty if successful)
- `Model` - Always "GPT-5.1"
- `Recommendation` - Positive/Negative/Neutral
- `Recommendation_Reasoning` - Detailed reasoning

## Data Summary

- **Total records in original**: 200 (50 projects × 4 models)
- **Unique projects**: 50
- **PDF files available**: 267
- **Models in original**: OpenAI, Mistral, Claude, Gemini
- **New model**: GPT-5.1

## Requirements

- Python 3.9+
- pandas
- PyPDF2
- aiohttp
- OpenAI API key

## Notes

- The script processes all 50 unique projects
- Each project takes ~1 second to process (with rate limiting)
- Total runtime: ~1 minute
- Uses the same prompt as the original analysis
- Handles errors gracefully (missing PDFs, API errors, etc.)
