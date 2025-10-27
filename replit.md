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
- **Test Management**: Supports creation of tests from PDF files, dynamic answer option configuration, and optional time restrictions. Questions can be extracted from PDFs using PyMuPDF.
- **Data Handling**: Employs `pandas` for data manipulation, including automatic numeric conversion and handling mixed data types with error coercion. A dedicated "File Analyzer" mode allows users to clean and standardize data (e.g., renaming columns to "Savol_1").
- **Payment System**: Integrated with Telegram Stars for per-analysis payments, managed by a `PaymentManager` that handles invoice creation, pre-checkout, and successful payment callbacks. An admin panel allows toggling between free and paid modes and configuring pricing.
- **Error Handling**: Enhanced error handling provides clear messages, guiding users when data needs cleaning or is improperly formatted.
- **Multi-bot architecture**: Separate bots for teacher and student functionalities, ensuring distinct workflows.

### Feature Specifications
- **Core Analysis**: Performs Rasch analysis on dichotomous data (0/1 format).
- **Report Generation**: Produces PDF reports with item parameters, person abilities, reliability statistics, and normalized section T-scores.
- **Test Creation**: Teachers can upload PDFs, define questions, set answers, and configure time restrictions.
- **Student Interface**: Provides test navigation (previous/next), real-time timer, progress bar, answer review, and detailed results.
- **Admin Features**: Includes a comprehensive admin panel for payment configuration, balance monitoring (`/balance` command), and user management.
- **Contact/Community**: Dedicated sections for contacting admin (Telegram, Email) and accessing community channels.

### System Design Choices
- **Modularity**: The codebase is structured into `handlers`, `utils`, and separate modules for `rasch_analysis`, `pdf_generator`, and `payment_manager`.
- **Data Persistence**: Payment data and test configurations are persisted using JSON-based databases.
- **Workflow**: The bot follows a clear workflow for file upload → optional payment → analysis → PDF delivery.

## External Dependencies
- `python-telegram-bot` (20.7): Telegram Bot API interaction.
- `pandas` (2.1.3): Data manipulation and analysis.
- `girth` (0.8.0): Rasch model MML estimation.
- `reportlab` (4.0.7): Professional PDF generation.
- `openpyxl` (3.1.2): Support for Excel file formats.
- `PyMuPDF`: PDF text extraction for test creation.
- `python-dotenv` (1.0.0): Environment variable management.