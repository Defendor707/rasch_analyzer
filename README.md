# Rasch Model Telegram Bot

Telegram bot that performs Rasch model analysis using marginal maximum likelihood (MML) estimation and returns results as a PDF report.

## Features

- 📊 Rasch model analysis for dichotomous data (0/1)
- 📄 Professional PDF reports with detailed statistics
- 🔄 Support for CSV and Excel file formats
- 📱 Easy-to-use Telegram interface
- 🌐 Uzbek language support

## Project Structure

```
project/
├── bot/
│   ├── main.py                    # Main bot application
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── message_handlers.py    # Command and message handlers
│   └── utils/
│       ├── __init__.py
│       ├── rasch_analysis.py      # Rasch model analysis module
│       └── pdf_generator.py       # PDF report generation
├── data/
│   ├── uploads/                   # Temporary file uploads
│   └── results/                   # Generated PDF reports
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

## Installation & Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Save the bot token you receive

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your bot token:

```
BOT_TOKEN=your_telegram_bot_token_here
```

### 3. Install Dependencies

Dependencies are automatically installed. The bot uses:
- `python-telegram-bot` - Telegram Bot API
- `pandas` - Data processing
- `girth` - Rasch model analysis (MML estimation)
- `reportlab` - PDF generation
- `openpyxl` - Excel file support

## Usage

### Starting the Bot

The bot runs automatically when you start the project. Users interact with it through Telegram.

### Bot Commands

- `/start` - Start the bot and see welcome message
- `/help` - Get help on how to use the bot

### Data Format Requirements

Your data file should:
- Be in CSV (.csv) or Excel (.xlsx, .xls) format
- Have **rows** representing persons/respondents
- Have **columns** representing items/questions
- Contain only **0** (incorrect) and **1** (correct) values

**Example data structure:**

| Item1 | Item2 | Item3 | Item4 |
|-------|-------|-------|-------|
| 1     | 0     | 1     | 1     |
| 0     | 0     | 0     | 1     |
| 1     | 1     | 1     | 1     |
| 0     | 1     | 0     | 1     |

### Workflow

1. Start a conversation with your bot on Telegram
2. Send `/start` to begin
3. Upload your data file (CSV or Excel)
4. Wait for the analysis to complete
5. Receive a PDF report with:
   - Item difficulty parameters
   - Person ability estimates
   - Reliability coefficient
   - Descriptive statistics

## Analysis Details

### Rasch Model

The bot uses a **1-parameter logistic (1PL) Rasch model** with MML estimation, similar to TAM's `tam.cmle` function in R.

The model estimates:
- **Item difficulties**: How hard each item is
- **Person abilities**: Each person's skill level
- **Reliability**: Test reliability (person separation)

### PDF Report Contents

Generated reports include:

1. **Sample Information**
   - Number of persons
   - Number of items
   - Reliability coefficient

2. **Item Difficulty Parameters**
   - Difficulty estimate for each item
   - Mean score for each item

3. **Person Ability Distribution**
   - Mean, SD, Min, Max of person abilities

## Technical Notes

### Python Implementation vs R TAM

This bot uses the `girth` Python library instead of R's TAM package because:
- More reliable in cloud environments
- Faster installation and dependency management
- Provides equivalent MML estimation
- Compatible API and results

The results are comparable to R's `tam.cmle()` function.

### Limitations

- Currently supports only dichotomous (0/1) data
- Designed for Rasch (1PL) model only
- Not suitable for polytomous items (rating scales)

## Troubleshooting

### Common Issues

**"BOT_TOKEN not found"**
- Make sure you created a `.env` file
- Check that BOT_TOKEN is set correctly in `.env`

**"Invalid file format"**
- Only CSV and Excel (.xlsx, .xls) files are supported
- Check that your file is not corrupted

**"Data contains non-binary values"**
- Rasch model requires dichotomous data (0 and 1 only)
- Check your data for invalid values

### Contact

For issues or questions, check the `/help` command in the bot.

## License

This project is provided as-is for educational and research purposes.
