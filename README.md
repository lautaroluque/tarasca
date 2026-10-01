# Tarasca

Personal financial tracker/planning app that ingests bank/credit card extracts, automatically parses and categorizes transactions, and provides spending dashboards.

## Features

- **Multi-bank import**: Upload extracts from Fiwind (Excel) and Galicia Mastercard (PDF)
- **Automatic categorization**: Rule-based engine with Spanish keywords (10 categories)
- **Movement types**: Every transaction is typed as ingreso, gasto, or transferencia (card payments, conversions between balances, refunds)
- **Multi-currency**: ARS, USD and crypto balances (USDT, USDC...) with currency switcher
- **Flexible metadata**: Stores bank-specific fields (Tipo, Comprobante, etc.)
- **Dashboard**: Spending trends, category breakdowns, account balances
- **Budget tracking**: Create monthly budgets and track progress
- **Responsive UI**: Works on mobile, tablet, and desktop
- **Cloud-hosted**: Free deployment on Streamlit Community Cloud

## Tech Stack

- **Language**: Python 3.13
- **Framework**: Streamlit
- **Database**: Supabase (PostgreSQL)
- **Package manager**: uv
- **Key libraries**: pandas, pdfplumber, plotly, sqlmodel, pydantic

## Project Structure

```
tarasca/
├── src/
│   ├── app.py              # Main Streamlit entry point
│   ├── pages/              # UI pages
│   │   ├── dashboard.py    # Spending overview
│   │   ├── upload.py       # File upload & import
│   │   ├── transactions.py # Transaction management
│   │   └── budgets.py      # Budget tracking
│   ├── core/               # Business logic
│   │   ├── ingestion.py    # File parsing (Excel/CSV/PDF)
│   │   ├── movements.py    # Movement type classification
│   │   ├── categorization.py # Rule-based categorization
│   │   ├── database.py     # Supabase CRUD operations
│   │   ├── models.py       # Data models
│   │   └── templates.py    # Bank template definitions
│   └── components/         # Reusable UI components
├── tests/                  # Unit tests
├── samples/                # Sample bank extracts
├── .streamlit/             # Streamlit configuration
└── pyproject.toml          # Project metadata & dependencies
```

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd tarasca

# Install dependencies
uv sync
```

### Configuration

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Run the SQL schema to create tables (`supabase_schema.sql` in the SQL Editor).
   If you created the tables with an older schema, run
   `supabase_migration_002_movement_types.sql` instead to upgrade in place.
3. Create `.streamlit/secrets.toml`:

```toml
[supabase]
url = "your-supabase-url"
key = "your-supabase-anon-key"
```

### Run Locally

```bash
uv run streamlit run src/app.py
```

## Usage

1. **Import**: Go to "Importar" page, select your bank template, upload your extract
2. **Review**: Preview transactions before importing
3. **Categorize**: Transactions are auto-categorized; manually adjust as needed
4. **Analyze**: View spending patterns on the Dashboard
5. **Budget**: Set monthly budgets and track progress

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check src/

# Type check
uv run mypy src/
```

## License

Personal project.
