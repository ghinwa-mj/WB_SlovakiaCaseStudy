#!/bin/bash
# Script to activate the World Bank virtual environment

echo "🚀 Activating World Bank virtual environment..."
source wb_venv/bin/activate

echo "✅ Virtual environment activated!"
echo "📦 Installed packages:"
echo "   - pandas (data manipulation)"
echo "   - PyPDF2 (PDF reading)"
echo "   - openpyxl (Excel files)"
echo "   - python-docx (Word documents)"
echo "   - openai (GPT-4 API)"
echo "   - jupyter (notebook environment)"
echo ""
echo "💡 To start Jupyter notebook, run: jupyter notebook"
echo "💡 To run the document processing, execute the cells in create_metadata.ipynb"
echo ""
echo "🔧 To deactivate the environment later, run: deactivate"
