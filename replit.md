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
- **October 23, 2025 (Latest)**: Fixed critical bugs in PDF generation and `/namuna` command
  - Fixed undefined variable error: `pending_general_pdf` → `general_pdf_path`
  - Added proper null safety checks for Optional type parameters
  - Fixed section results generation in `/namuna` command
  - Added section-based PDF generation to sample data analysis
  - Fixed indentation error in section results loop
  - All type annotations now properly use Optional for nullable parameters
- **October 23, 2025**: Implemented section-based T-score reporting in PDF
  - Added normalized section T-score calculation: Section T-scores sum to overall T-score
  - Formula: section_t = overall_t × (section_raw / sum_section_raw) when raw > 0
  - Equal distribution when all section raw scores are 0
  - Handles edge cases: empty sections, zero scores, invalid question indices
  - Modified PDF person results table to dynamically include section T-score columns
  - Added response_matrix to Rasch analysis results for section-based calculations
  - Integrated section_questions from user_data into PDF generation pipeline
  - Dynamic column layout adjusts to variable number of sections
  - Backward compatible: legacy format preserved when no sections configured
- **October 23, 2025**: Added subject sections configuration feature
  - Created subject_sections.py with all 9 subjects and their sections
  - Added section question number collection when section_results is enabled
  - Implemented question number parsing with validation (supports ranges, comma-separated, mixed)
  - Added "Bo'limlarni sozlash" menu option to reconfigure sections
  - Section configuration data saved to user_data for future use
  - Enhanced error messages for better user experience
- **October 22, 2025 (Latest)**: Fixed critical indexing bug in Rasch analysis
  - Removed unnecessary `.astype(bool)` conversion causing NumPy indexing errors
  - Fixed unbound variable issue in person statistics calculation
  - Added null safety checks for difficulty array indexing
  - Bot now runs without errors
- **October 22, 2025**: Added individual person statistics to PDF reports
  - Z-scores (standardized scores)
  - T-scores (mean=50, SD=10)
  - Standard errors for ability estimates
  - Detailed person-by-person table
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
