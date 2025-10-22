# Rasch Model Telegram Bot

## Overview
Telegram bot for performing Rasch model analysis on dichotomous test data. The bot accepts CSV/Excel files, runs Rasch model analysis using Python's girth library (MML estimation), and returns professional PDF reports with item difficulties, person abilities, and reliability statistics.

## Project Status
- **Created:** October 22, 2025
- **Language:** Python 3.11
- **Framework:** python-telegram-bot
- **Analysis:** girth library (Rasch MML estimation)
- **Reports:** ReportLab PDF generation

## Recent Changes
- Initial project setup with complete Rasch analysis bot
- Implemented file upload handling (CSV/Excel)
- Created Rasch model analysis module with MML estimation
- Built PDF report generator with professional formatting
- Added Uzbek language interface for user interactions

## Architecture

### Directory Structure
```
├── bot/
│   ├── main.py                    # Bot entry point
│   ├── handlers/
│   │   └── message_handlers.py    # Commands & file handling
│   └── utils/
│       ├── rasch_analysis.py      # Rasch model implementation
│       └── pdf_generator.py       # PDF report generation
├── data/
│   ├── uploads/                   # Temporary file storage
│   └── results/                   # Generated PDFs
```

### Key Components

1. **Rasch Analysis Module** (`bot/utils/rasch_analysis.py`)
   - Uses girth library for MML estimation
   - Implements Rasch (1PL) model
   - Estimates item difficulties and person abilities
   - Calculates reliability coefficients

2. **PDF Generator** (`bot/utils/pdf_generator.py`)
   - Professional ReportLab-based reports
   - Formatted tables for item parameters
   - Statistical summaries
   - Person ability distributions

3. **Telegram Handlers** (`bot/handlers/message_handlers.py`)
   - File upload processing (CSV/Excel)
   - Data validation
   - Analysis orchestration
   - Report delivery

### Dependencies
- python-telegram-bot 20.7 - Telegram Bot API
- pandas 2.1.3 - Data manipulation
- girth 0.8.0 - Rasch model MML estimation
- reportlab 4.0.7 - PDF generation
- openpyxl 3.1.2 - Excel file support
- python-dotenv 1.0.0 - Environment management

## Configuration

### Required Secrets
- `BOT_TOKEN` - Telegram bot token from @BotFather

### Workflow
Bot runs via: `python bot/main.py`

## User Preferences
- Uzbek language interface for Uzbek-speaking users
- Analysis method: Rasch model (equivalent to R TAM's tam.cmle)
- Output format: PDF reports

## Technical Notes

### Rasch Model Implementation
- Method: Marginal Maximum Likelihood (MML) estimation
- Comparable to R's TAM package `tam.cmle()` function
- Python implementation chosen for reliability in cloud environment

### Data Requirements
- Format: CSV or Excel (.xlsx, .xls)
- Structure: Rows = persons, Columns = items
- Values: Dichotomous (0 = incorrect, 1 = correct)

### Analysis Output
- Item difficulty parameters
- Person ability estimates (MLE)
- Reliability (person separation)
- Descriptive statistics

## Future Enhancements (Possible)
- Support for polytomous models (PCM, RSM)
- Data visualization in PDF (Wright maps, ICC curves)
- Multiple model comparison
- Item fit statistics
- DIF detection
