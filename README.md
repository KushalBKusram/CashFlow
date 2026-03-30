# CashFlow - Transaction Flow Visualizer

A Streamlit web application that visualizes your financial transactions as an interactive Sankey diagram and projects your year-end spending by category.

![Transaction Flow Visualization](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)

## Features

### Spending Tracker
- **Interactive Sankey Diagram**: Visualize income flow to savings and expense categories
- **Multiple Date Ranges**: View transactions for different time periods (Last Week, Month, 60/90 days, 6 months, Year, All Time)
- **Key Metrics Dashboard**: Track Income, Expenses, Savings, and Savings Rate
- **Category Drill-Down**: Select any category to see:
  - Top 10 merchants/payees in that category (pie chart)
  - Detailed transaction table
  - Category-specific metrics
- **Percentage-Based Labels**: Node labels show percentages of income for easy comparison
- **Tag Filtering**: Filter the diagram by tags from your CSV

### Year-end Projections
- **Per-Category Projections**: See where every expense category will land by year-end based on your average monthly rate
- **Income Detection**: Auto-detects monthly income from the CSV; override manually if needed
- **Session Targets**: Set a target per category as a % of annual income and instantly see whether you're on pace or over
- **Summary Dashboard**: See how many categories are on pace vs. over budget at a glance
- **Visual Gap Chart**: Horizontal bar chart comparing projected vs. target spend across all categories

### Data Correctness
- Excluded transactions (marked in Copilot Money) are filtered out of all calculations
- Credit card payment transfers are excluded from expense totals
- Negative amounts (refunds) reduce category totals automatically

## Requirements

**CSV Format:** Currently tested and working with CSV exports from [Copilot Money](https://copilot.money).

Your CSV file should include these columns:
- `date` - Transaction date
- `name` - Merchant/payee name
- `amount` - Transaction amount (negative for income, positive for expenses)
- `type` - Transaction type (e.g., `income`, `regular`, `transfer`)
- `category` - Expense category
- `account` - Account name
- `excluded` - Whether to exclude (true/false)
- `tags` - Optional tags for filtering

## Installation

1. Clone this repository:
```bash
git clone https://github.com/KushalBKusram/CashFlow.git
cd CashFlow
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser to `http://localhost:8501`

3. Export your transactions from **Copilot Money** and upload the CSV using the sidebar file uploader

That's it! The app processes your transactions and visualizes them across both tabs.

## Tech Stack

- **[Streamlit](https://streamlit.io/)**: Web application framework
- **[Pandas](https://pandas.pydata.org/)**: Data manipulation
- **[Plotly](https://plotly.com/python/)**: Interactive visualizations
- **Python**: 3.9+

## Project Structure

```
CashFlow/
├── app.py                       # Main Streamlit application
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## How It Works

### Income Calculation
- Only transactions with `type == 'income'` are counted as income
- Uses absolute value of amount (income is stored as negative in Copilot Money exports)

### Expense Calculation
- Non-income, non-transfer transactions with valid categories
- Excluded transactions are filtered out (income rows kept even if marked excluded)
- Refunds (negative amounts) reduce category totals

### Savings Calculation
```
Savings = Total Income - Total Expenses
Savings Rate = (Savings / Income) × 100%
```

### Year-end Projections
```
Monthly Rate = Category Spend in Window / Months Elapsed
Projected Annual = Monthly Rate × 12
Target $ = Target % × Annual Income
Gap = Projected Annual - Target $
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Support

If you find this useful, please star ⭐ the repository!

For issues or questions, please open an issue on GitHub.
