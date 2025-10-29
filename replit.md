# Rasch Model Telegram Bot

## Overview
This project is a Telegram bot designed for performing Rasch model analysis on dichotomous test data. It enables users to upload CSV/Excel files, which are then processed using Python's `girth` library for Rasch model analysis (MML estimation). The bot generates and returns professional PDF reports containing essential psychometric information, including item difficulties, person abilities, and reliability statistics. The vision is to provide an accessible, user-friendly tool for educators and researchers to conduct robust psychometric analysis directly through Telegram. The bot also supports test creation from PDF files, making it easier for teachers to digitalize and administer tests with integrated analysis capabilities.

## User Preferences
- Uzbek language interface for Uzbek-speaking users
- Analysis method: Rasch model (equivalent to R TAM's tam.cmle)
- Output format: PDF reports

## System Architecture
The bot operates using a Python backend with the `python-telegram-bot` framework.

### UI/UX Decisions
- The bot features an Uzbek language interface.
- Inline keyboards are extensively used for interactive test creation, offering dynamic answer options (A, B, C, D, plus additional options) and test configuration (e.g., time restrictions).
- Visual indicators like ✅ for answered questions, color-coded time warnings (🔴, 🟡, ⏰), and performance medals (🥇🥈🥉) enhance user experience.
- PDF reports are professionally formatted using ReportLab, presenting data clearly in tables.

### Technical Implementations
- **Rasch Analysis**: Utilizes the `girth` library for Marginal Maximum Likelihood (MML) estimation of the Rasch (1PL) model, providing item difficulties, person abilities, and reliability coefficients.
- **PDF Generation**: `reportlab` is used to create detailed PDF reports, including individual person statistics (Z-scores, T-scores, standard errors) and section-based T-score reporting.
- **Test Management**: Supports creation of tests from PDF files, text-based answer input format, and optional time restrictions. Questions can be extracted from PDFs using PyMuPDF. PDF files uploaded during test creation are automatically stored in `data/uploads/pdf_files/` and distributed to candidates when they begin the test.
- **PDF File Distribution**: When teachers upload a PDF file containing test questions during test creation, the file is permanently saved and automatically sent to students when they click the "Boshlash" (Begin) button to start the test. This ensures students have access to the complete test document while taking the test.
- **Answer Input System**: Teachers submit all answers in a compact text format (e.g., "1a2b3c32a+33b++43(ayb)44(alisher Navoiy)"), which is parsed by `bot/utils/answer_parser.py`. The parser supports standard 4-option questions, extended options (5-26 options using + notation), and text-based answers (using parentheses notation).
- **Text Answer Questions**: For text-based answer questions, students type their answers directly in the chat instead of selecting from inline keyboard options. The system compares student text input with the correct answer (case-insensitive) during grading.
- **Auto-Complete Suggestion**: When all questions are answered, the system automatically suggests test completion with a prominent button, while also providing navigation to unanswered questions if any remain.
- **Data Handling**: Employs `pandas` for data manipulation, including automatic numeric conversion and handling mixed data types with error coercion. A dedicated "File Analyzer" mode allows users to clean and standardize data (e.g., renaming columns to "Savol_1"). **Evalbee Format Support (2025-10-29):** The File Analyzer now automatically detects and processes Evalbee exported files, extracting only the "Q X Marks" columns (student scores 0/1) while removing "Q X Options", "Q X Key", and all metadata columns (Total Marks, Grade, Rank, Correct Answers, etc.). This enables seamless Rasch analysis of Evalbee test results.
- **Payment System**: Integrated with Telegram Stars for per-analysis payments, managed by a `PaymentManager` that handles invoice creation, pre-checkout, and successful payment callbacks. An admin panel allows toggling between free and paid modes and configuring pricing.
- **Error Handling**: Enhanced error handling provides clear messages, guiding users when data needs cleaning or is improperly formatted.
- **Multi-bot architecture**: Separate bots for teacher and student functionalities, ensuring distinct workflows.

### Feature Specifications
- **Core Analysis**: Performs Rasch analysis on dichotomous data (0/1 format).
- **Report Generation**: Produces PDF reports with item parameters, person abilities, reliability statistics, and normalized section T-scores.
- **Test Creation**: Teachers can upload PDFs and submit all answers in a compact text format (e.g., "1a2b3c32a+33b++43(ayb)"), supporting variable option counts (4-26 options A-Z) and text-based answers.
- **Answer Format**: Supports standard 4-option questions (A,B,C,D), extended options with "+" notation (5 options: "32a+", 6 options: "33b++"), and text answers using parentheses ("43(ayb)", "44(alisher Navoiy)").
- **Student Interface**: Provides test navigation (previous/next), real-time timer, progress bar, answer review, and detailed results.
- **Admin Features**: Includes a comprehensive admin panel for payment configuration, balance monitoring (`/balance` command), and user management.
- **Contact/Community**: Dedicated sections for contacting admin (Telegram, Email) and accessing community channels.

### System Design Choices
- **Modularity**: The codebase is structured into `handlers`, `utils`, `database`, and separate modules for `rasch_analysis`, `pdf_generator`, and `payment_manager`.
- **Data Persistence**: Now uses PostgreSQL database for all data storage (migrated from JSON files). Database includes tables for users, students, tests, test_results, payments, payment_config, and system_logs.
- **Workflow**: The bot follows a clear workflow for file upload → optional payment → analysis → PDF delivery.
- **Error Monitoring**: Implemented Telegram-based error alerting system that notifies admins immediately when errors occur.
- **Backup System**: Automated database backup to JSON files with Git integration for disaster recovery.

## External Dependencies
- `python-telegram-bot` (20.7): Telegram Bot API interaction.
- `pandas` (2.1.3): Data manipulation and analysis.
- `girth` (0.8.0): Rasch model MML estimation.
- `reportlab` (4.0.7): Professional PDF generation.
- `openpyxl` (3.1.2): Support for Excel file formats (.xlsx and .xls with fallback).
- `xlrd` (2.0.2): Legacy Excel file format support (.xls) with openpyxl fallback.
- `PyMuPDF`: PDF text extraction for test creation.
- `python-dotenv` (1.0.0): Environment variable management.
- `asyncpg`: Async PostgreSQL database driver.
- `sqlalchemy[asyncio]`: SQL toolkit and ORM with async support.
- `apscheduler`: Background job scheduler for automated tasks.

## Data Storage
**Current Status (2025-10-29):**
- System currently uses JSON file storage for user data, students, tests, and payments
- JSON files are stored in `data/` directory: `user_profiles.json`, `students.json`, `tests.json`, `payments.json`
- PostgreSQL database infrastructure exists but is currently disabled to simplify deployment
- Database can be re-enabled by uncommenting initialization code in `run_bots.py`

**Database Architecture (Available but Disabled):**
- Location: `bot/database/` directory
- Schema: `bot/database/schema.py`
- Managers: `bot/database/managers.py` (UserManager, StudentManager, TestManager, etc.)
- Migration: `bot/database/migrate_json_to_postgres.py` (one-time migration from JSON)
- Backup: `bot/database/backup_to_git.py` (automated backup to Git)

## Error Monitoring
**Telegram Alert System:**
- All errors are automatically logged to database
- Admin users receive immediate Telegram notifications when errors occur
- Notifications include: error type, timestamp, user info, traceback
- Configure admin IDs in `data/payment_config.json` under `admin_ids`
- See `ADMIN_SETUP.md` for configuration instructions