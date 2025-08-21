# Document Translation Service

A comprehensive document translation service with custom glossary support. This service allows you to translate Word documents while preserving formatting and using custom terminology glossaries.

## Features

- **Document Translation**: Translate .doc and .docx files while preserving formatting
- **Custom Glossary Generation**: Extract terms from documents and generate Excel glossaries
- **Glossary-Based Translation**: Use custom Excel glossaries to ensure consistent terminology
- **Two Output Modes**: 
  - Translation only
  - Side-by-side comparison with terminology highlighting
- **Multiple Language Support**: English, Chinese, Thai

## Quick Start

### Option 1: Direct Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the service:
```bash
python start.py
```

3. Open your browser to `http://localhost:7888`

### Option 2: Docker

1. Build and start with Docker Compose:
```bash
docker-compose up --build
```

2. Open your browser to `http://localhost:7888`

## Usage

### Generate Custom Glossary

1. Go to the "Generate Glossary" tab
2. Upload your document (.doc or .docx)
3. Select source and target languages
4. Click "Generate Glossary"
5. Download the Excel file
6. Edit the glossary as needed (two columns: "Source Content", "Target Content")

### Translate Documents

1. Go to the "Translate Document" tab
2. Upload your document to translate
3. (Optional) Upload your edited glossary Excel file and click "Load Glossary"
4. Select languages and output type
5. Click "Translate Document"
6. Download the result

## New Features in This Version

- **No Database Dependency**: Removed PostgreSQL dependency for easier deployment
- **Excel-Based Glossaries**: All terminology is managed through Excel files
- **Improved UI**: Tab-based interface for better workflow
- **Local Processing**: All glossary management is done locally
- **Docker Support**: Easy deployment with Docker Compose

## API Configuration

Update the API settings in `prompt.py`:
- `api_key`: Your OpenAI/OpenRouter API key
- `base_url`: API endpoint URL
- `model`: AI model to use (default: google/gemini-2.0-flash-001)

## File Structure

- `gradio_ui.py`: Main web interface
- `glossary_manager.py`: Glossary management without database
- `translation.py`: Translation service
- `word_translation_service.py`: Word document processing
- `prompt.py`: API configuration and prompts
- `start.py`: Application launcher

## Requirements

### For Direct Installation
- Python 3.8+
- OpenAI/OpenRouter API access
- Required packages listed in `requirements.txt`

### For Docker
- Docker and Docker Compose
- OpenAI/OpenRouter API access

## Glossary Excel Format

The glossary Excel file must have exactly two columns:
- **Source Content**: Original terms in source language
- **Target Content**: Translated terms in target language

Example:
| Source Content | Target Content |
|----------------|----------------|
| API            | 应用程序接口      |
| database       | 数据库          |
| authentication | 身份验证        |

## Notes

- Processing time depends on document length
- Large documents may take several minutes to process
- The service preserves formatting, images, and tables
- Custom glossary terms are highlighted in contrast mode
- All terminology is case-insensitive when matching
