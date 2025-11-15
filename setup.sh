#!/bin/bash
# Setup script for Website Crawler

echo "🚀 Setting up Website Crawler Environment..."

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed. Please install Anaconda or Miniconda first."
    echo "   Visit: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "✅ Conda found"

# Create conda environment
echo "📦 Creating conda environment 'website-crawler'..."
conda env create -f environment.yml

if [ $? -eq 0 ]; then
    echo "✅ Environment created successfully"
else
    echo "❌ Failed to create environment"
    exit 1
fi

# Activate environment and install additional dependencies
echo "🔧 Installing additional dependencies..."
conda activate website-crawler && pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Download Chromium for pyppeteer
echo "🌐 Downloading Chromium for pyppeteer..."
conda activate website-crawler && python -c "import pyppeteer; pyppeteer.chromium_downloader.download_chromium()"

if [ $? -eq 0 ]; then
    echo "✅ Chromium downloaded successfully"
else
    echo "⚠️  Chromium download failed, but you can still try running the crawler"
fi

echo ""
echo "🎉 Setup completed!"
echo ""
echo "To use the crawler:"
echo "1. Activate the environment: conda activate website-crawler"
echo "2. Run the test script: python test_crawler.py"
echo "3. Or use the main crawler: python website_crawler.py"
echo ""
echo "📁 Files created:"
echo "  - environment.yml (conda environment definition)"
echo "  - requirements.txt (Python dependencies)"
echo "  - website_crawler.py (main crawler script)"
echo "  - test_crawler.py (test script)"
echo ""
echo "Happy crawling! 🕷️"
