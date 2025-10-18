# Slovakia Case Study - Sentiment Analysis

This repository contains sentiment analysis tools for analyzing Cost Benefit Analysis projects from Slovakia using multiple AI models.

## 🚀 Features

- **Multi-Model Analysis**: Compare results across different AI models
- **PDF Processing**: Extract text from Slovak CBA documents
- **Cost Tracking**: Monitor API usage and costs for each model
- **Flexible Analysis**: Run analysis on subsets or full datasets

## 📋 Available Scripts

### 1. Full Model Comparison (`sentiment_analysis_comparison.py`)
Runs analysis on 50 random projects using 8 different AI models:
- GPT-5 (2025-08-07)
- GPT-5 Mini (2025-08-07) 
- GPT-4.1
- Mistral Large Latest
- Claude Opus 4.1
- Claude Sonnet 4.5
- Gemini 2.5 Flash Lite
- Gemini 2.5 Pro

### 2. Claude-Only Analysis (`claude_only_analysis.py`)
Runs analysis on 50 random projects using only Claude Sonnet 4.5.

### 3. Gemini + GPT Full Analysis (`gemini_gpt_full_analysis.py`)
Runs analysis on the **ENTIRE dataset** using:
- Gemini 2.5 Pro
- GPT-4.1
- GPT-5.1

### 4. GPT-5.1 Analysis (`gpt51_sentiment_analysis.py`)
Runs analysis using only GPT-5.1 model.

## 🛠️ Setup

### Prerequisites
- Python 3.9+
- Required packages (see `requirements_sentiment.txt`)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd slovakia_CaseStudy/Sentiment\ Analysis\ Experiment/

# Install dependencies
pip install -r requirements_sentiment.txt

# Set up API keys
cp apikeys_template.py apikeys.py
# Edit apikeys.py with your actual API keys
```

### API Keys Required
You'll need API keys for:
- OpenAI (for GPT models)
- Mistral AI
- Anthropic (for Claude)
- Google AI (for Gemini)

## 📊 Usage

### Test Run (Recommended First)
```bash
# Test with minimal data to verify setup
python sentiment_analysis_comparison.py test
python claude_only_analysis.py test
python gemini_gpt_full_analysis.py test
```

### Full Analysis
```bash
# Run 50-project comparison across all models
python sentiment_analysis_comparison.py

# Run Claude-only analysis on 50 projects
python claude_only_analysis.py

# Run Gemini + GPT analysis on FULL dataset
python gemini_gpt_full_analysis.py
```

## 📁 Data Requirements

The scripts expect:
- `project_summary.csv` in the `../Outputs/` directory
- PDF files in the `../downloaded_first_links/` directory
- Each PDF should be named `{document_id}.pdf`

## 📈 Output Files

Each script generates:
- `*_results_YYYYMMDD_HHMMSS.csv` - Main results in CSV format
- `*_results_YYYYMMDD_HHMMSS.json` - Detailed JSON results
- `*_unparseable_responses.json` - Any parsing errors (if applicable)

## 💰 Cost Tracking

All scripts include detailed cost tracking:
- Input/output token counts
- Cost per model
- Total project costs
- Grand total costs

## 🔒 Security

- **API keys are excluded** from version control via `.gitignore`
- Use `apikeys_template.py` as a template for your API keys
- Never commit actual API keys to the repository

## 📝 Analysis Prompt

All scripts use the same standardized prompt to extract:
- Positive/Negative/Neutral recommendations
- Supporting reasoning for recommendations
- Structured JSON output format

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure API keys are not committed
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Troubleshooting

### Common Issues
- **API Key Errors**: Ensure `apikeys.py` exists and contains valid keys
- **PDF Not Found**: Check that PDF files are in the correct directory
- **Rate Limiting**: Scripts include delays, but you may need to increase them for large datasets

### Support
For issues or questions, please create an issue in the repository.
