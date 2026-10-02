# Tarasca

Personal financial tracker/planning app that ingests bank/credit card extracts, automatically parses and categorizes transactions, and provides spending dashboards.

## Features

- **Multi-bank import**: Upload extracts from Fiwind (Excel) and Galicia Mastercard (PDF)
- **Phone uploads**: Share extracts from Android's share sheet via the Tarasca uploader app
- **Real-time card expenses**: Card-use notification emails are polled every ~5 min and imported automatically (no duplicates when the monthly statement arrives)
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
│   │   ├── upload.py       # File upload & import (browser + phone)
│   │   ├── transactions.py # Transaction management
│   │   └── budgets.py      # Budget tracking
│   ├── core/               # Business logic
│   │   ├── ingestion.py    # File parsing (Excel/CSV/PDF)
│   │   ├── movements.py    # Movement type classification
│   │   ├── categorization.py # Rule-based categorization
│   │   ├── database.py     # Supabase CRUD operations
│   │   ├── email_templates.py # Email notification templates
│   │   ├── email_ingest.py  # IMAP email fetching + normalization
│   │   ├── merging.py      # Cross-source dedupe (email ↔ statement)
│   │   ├── models.py       # Data models
│   │   └── templates.py    # Bank template definitions
│   └── components/         # Reusable UI components
├── scripts/                # CLI entrypoints (diagnose, poll_email, ...)
├── mobile/                 # Android uploader app (Kotlin)
├── tests/                  # Unit tests
├── samples/                # Sample bank extracts (gitignored)
├── .github/workflows/      # Email ingest cron
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
   If you created the tables with an older schema, run the migrations in order
   to upgrade in place:
   - `supabase_migration_002_movement_types.sql` (movement types + free-form currencies)
   - `supabase_migration_003_phone_uploads.sql` (Storage bucket for phone uploads)
   - `supabase_migration_004_email_ingest.sql` (source column + ingest_state table)
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

1. **Import**: Go to "Importar" page, select your bank template, upload your extract (from your browser or phone)
2. **Review**: Preview transactions before importing
3. **Categorize**: Transactions are auto-categorized; manually adjust as needed
4. **Analyze**: View spending patterns on the Dashboard
5. **Budget**: Set monthly budgets and track progress

### Phone uploads

1. Open `mobile/` in Android Studio (or build with `./gradlew assembleDebug`)
2. Copy `mobile/local.properties.example` to `mobile/local.properties` and fill in
   your Supabase project URL and publishable key (Dashboard → Project Settings → API)
3. Install the APK on your phone (sideloading)
4. Share a bank extract from any app → select "Tarasca" → tap "Subir a Tarasca"
5. The file appears in the Importar page under "Desde el teléfono"

### Real-time card expenses (email ingest)

The GitHub Actions workflow (`.github/workflows/email-ingest.yml`) polls your Gmail
for card-use notifications every 5 minutes and imports them as transactions.
When the monthly statement is later imported, email-tracked purchases are
automatically skipped (no duplicates).

**Setup:**

1. Enable 2-Step Verification on your Google account and create an
   [App Password](https://myaccount.google.com/apppasswords) for "Mail"
2. Add these secrets to your GitHub repo (Settings → Secrets → Actions):
   - `IMAP_HOST` = `imap.gmail.com`
   - `IMAP_USER` = your Gmail address
   - `IMAP_APP_PASSWORD` = the app password from step 1
   - `SUPABASE_URL` / `SUPABASE_SECRET_KEY` = same as in `.streamlit/secrets.toml`
3. The workflow runs automatically every 5 minutes; you can also trigger it
   manually from the Actions tab

**Note:** Scheduled workflows are automatically disabled after 60 days of
repository inactivity.

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
