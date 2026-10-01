# Implementation Plan: Personal Financial Tracker

## Goal

Build a personal financial tracker/planning web app that ingests bank/credit card extracts (CSV, PDF, Excel), automatically parses and categorizes transactions, and provides spending dashboards. Must be accessible from any device via a free cloud platform. UI language: Spanish.

## Scope

### In Scope

- Excel (.xlsx), CSV, and PDF file upload and parsing
- Bank-specific template system for mapping columns/fields
- Pre-configured templates for **Fiwind** (Excel) and **Galicia Mastercard** (PDF)
- Multi-currency support (ARS and USD) with currency switcher in UI
- Rule-based transaction categorization (keyword matching, Spanish categories)
- PostgreSQL database persistence (Supabase)
- Streamlit web UI with multi-page navigation (all in Spanish)
- Dashboard with spending visualizations (charts, trends)
- Transaction list with manual category editing and metadata display
- Budget tracking (basic)
- Cloud deployment to Streamlit Community Cloud

### Out of Scope (Future Phases)

- Machine learning-based categorization
- Automatic bank API integrations (Plaid, etc.)
- Email-based extract parsing
- Multi-user support / authentication
- Mobile-native apps (PWA is acceptable via Streamlit responsiveness)
- Investment/portfolio tracking
- Recurring transaction detection
- Data export

## Constraints

- Python 3.13 only
- Free-tier cloud hosting (Streamlit Community Cloud)
- Free-tier database (Supabase PostgreSQL)
- Must use `uv` for dependency management
- No secrets committed to repository
- Responsive web UI (works on mobile, tablet, desktop)
- Use established libraries; do not reinvent the wheel
- UI language: Spanish
- Currency: ARS and USD (multi-currency with switcher)

## Relevant Architecture & Files

| File/Directory | Purpose |
|---|---|
| `pyproject.toml` | Project metadata, dependencies (streamlit, pandas, supabase, plotly, pdfplumber, openpyxl, sqlmodel, pydantic) |
| `src/app.py` | Streamlit entry point, navigation, page routing |
| `src/pages/dashboard.py` | Spending overview, charts, trends (Spanish) |
| `src/pages/upload.py` | File upload interface, template selection, preview (Spanish) |
| `src/pages/transactions.py` | Transaction list, filtering, manual category editing, metadata display (Spanish) |
| `src/pages/budgets.py` | Budget creation and tracking (Spanish) |
| `src/core/ingestion.py` | File parsing logic (Excel/CSV via pandas, PDF via pdfplumber) |
| `src/core/categorization.py` | Rule-based categorization engine (Spanish keywords) |
| `src/core/database.py` | Supabase client, CRUD operations, connection management |
| `src/core/models.py` | Pydantic/SQLModel data models (Transaction, Category, Account, Budget) |
| `src/core/templates.py` | Bank template definitions and column mapping (Fiwind, Galicia Mastercard) |
| `src/components/charts.py` | Reusable Plotly chart components |
| `src/components/forms.py` | Reusable Streamlit form components |
| `.streamlit/config.toml` | Streamlit theme and server configuration |
| `.streamlit/secrets.toml` | Local secrets (gitignored); production uses Streamlit secrets |
| `tests/test_ingestion.py` | Parsing logic tests |
| `tests/test_categorization.py` | Categorization engine tests |
| `tests/test_database.py` | Database operation tests (mocked) |

## Bank Templates

### Fiwind (Excel)

- **File**: `.xlsx` with sheets "Actividad" and "Balance"
- **Sheet**: "Actividad"
- **Columns**:
  - `Fecha` → `date` (format: `DD/MM/YYYY HH:MM:SS`)
  - `Tipo` → `metadata.tipo` (e.g., "Rendimiento bonificado", "Ganancia diaria", "Retiro", "Conversión")
  - `Monto` → `amount`
  - `Moneda` → `currency` (ARS, USDT, etc.)
  - `Monto Origen` → `metadata.monto_origen`
  - `Moneda Origen` → `metadata.moneda_origen`
  - `Precio` → `metadata.precio`
- **Sheet "Balance"**: Shows balances by currency (ARS, BUSD, USDC, USDT) — can be used for account balance tracking

### Galicia Mastercard (PDF)

- **File**: `.pdf` with 8 pages
- **Section**: "DETALLE DEL CONSUMO"
- **Columns**:
  - `FECHA` → `date` (format: `DD-Mon-YY`, e.g., `05-Sep-26`)
  - `REFERENCIA` → `description` (merchant name)
  - `COMPROBANTE` → `metadata.comprobante`
  - `PESOS` → `amount` (ARS)
  - `DÓLARES` → `amount` (USD)
- **Number format**: Argentine (dots for thousands, comma for decimals: `30.797,00`)
- **Special sections**:
  - "COMPRAS DEL MES" → `metadata.seccion` = "compras"
  - "CUOTA DEL MES" → `metadata.seccion` = "cuota" (installment payments)
- **Multi-currency**: ARS and USD columns — create separate transactions for each currency

## Data Models

### Transaction

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `date` | datetime | Transaction date |
| `description` | str | Merchant/description |
| `amount` | float | Transaction amount |
| `currency` | str | Currency code (ARS, USD) |
| `account` | str | Source account (Fiwind, Galicia Mastercard, etc.) |
| `category_id` | FK | Category reference |
| `metadata` | JSONB | Bank-specific fields (tipo, comprobante, moneda_origen, precio, seccion, etc.) |
| `created_at` | datetime | Record creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### Category

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | str | Category name (Spanish) |
| `color` | str | Hex color for charts |
| `icon` | str | Emoji or icon identifier |

### Default Categories (Spanish)

- `Vivienda` (Housing)
- `Alimentación` (Food & Dining)
- `Transporte` (Transportation)
- `Servicios` (Utilities)
- `Entretenimiento` (Entertainment)
- `Salud` (Healthcare)
- `Compras` (Shopping)
- `Ingresos` (Income)
- `Transferencias` (Transfers)
- `Otros` (Other)

### Budget

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `category_id` | FK | Category reference |
| `amount` | float | Budget amount |
| `currency` | str | Budget currency (ARS or USD) |
| `month` | int | Budget month (1-12) |
| `year` | int | Budget year |

## Ordered Implementation Steps

### Phase 1: Project Scaffolding

- [ ] 1.1 Create `pyproject.toml` with all dependencies (streamlit, pandas, supabase, plotly, pdfplumber, openpyxl, sqlmodel, pydantic, python-dotenv, pytest, ruff, mypy)
- [ ] 1.2 Create directory structure (`src/`, `src/pages/`, `src/core/`, `src/components/`, `tests/`, `.streamlit/`)
- [ ] 1.3 Create `.streamlit/config.toml` with basic theme settings
- [ ] 1.4 Create `.gitignore` (include `.streamlit/secrets.toml`, `__pycache__`, `.venv`, `.env`)
- [ ] 1.5 Create `src/app.py` with basic Streamlit page setup and navigation (Spanish)

### Phase 2: Data Layer

- [ ] 2.1 Define Pydantic models in `src/core/models.py` (Transaction, Category, Account, Budget)
- [ ] 2.2 Implement `src/core/database.py` with Supabase client initialization
- [ ] 2.3 Implement CRUD operations for transactions (create, read, update, delete)
- [ ] 2.4 Implement CRUD operations for categories and budgets
- [ ] 2.5 Add database connection health check and error handling

### Phase 3: Ingestion Engine

- [ ] 3.1 Implement Excel/CSV parsing in `src/core/ingestion.py` using pandas
- [ ] 3.2 Implement PDF parsing in `src/core/ingestion.py` using pdfplumber
- [ ] 3.3 Create bank template system in `src/core/templates.py` (column mappings, date formats, amount columns)
- [ ] 3.4 Implement Fiwind template (Excel parser with metadata extraction)
- [ ] 3.5 Implement Galicia Mastercard template (PDF parser with Argentine number format, multi-currency, section detection)
- [ ] 3.6 Add data validation and cleaning (date parsing, amount normalization, deduplication)

### Phase 4: Categorization Engine

- [ ] 4.1 Implement rule-based categorization in `src/core/categorization.py`
- [ ] 4.2 Create default category set in Spanish (Vivienda, Alimentación, Transporte, Servicios, Entretenimiento, Salud, Compras, Ingresos, Transferencias, Otros)
- [ ] 4.3 Implement keyword-to-category mapping with priority ordering (Spanish keywords)
- [ ] 4.4 Add "Otros" fallback for unmatched transactions
- [ ] 4.5 Allow manual category override (stored in database)

### Phase 5: UI - Upload & Transactions

- [ ] 5.1 Build upload page (`src/pages/upload.py`) with file uploader (Spanish)
- [ ] 5.2 Add bank template selector dropdown (Fiwind, Galicia Mastercard)
- [ ] 5.3 Implement parse preview (show first 10 rows before committing)
- [ ] 5.4 Add "Importar" button that saves to database
- [ ] 5.5 Build transactions page (`src/pages/transactions.py`) with data table (Spanish)
- [ ] 5.6 Add filtering by date range, category, account, currency
- [ ] 5.7 Add inline category editing with dropdown
- [ ] 5.8 Add metadata display (expandable row or tooltip showing bank-specific fields)

### Phase 6: UI - Dashboard & Budgets

- [ ] 6.1 Build dashboard page (`src/pages/dashboard.py`) (Spanish)
- [ ] 6.2 Add currency switcher (ARS/USD) in header or sidebar
- [ ] 6.3 Implement spending-by-category pie chart (Plotly)
- [ ] 6.4 Implement monthly spending trend line chart
- [ ] 6.5 Implement account balance summary cards
- [ ] 6.6 Build budgets page (`src/pages/budgets.py`) (Spanish)
- [ ] 6.7 Implement budget creation form
- [ ] 6.8 Implement budget vs. actual progress bars

### Phase 7: Integration & Polish

- [ ] 7.1 Add error handling and user-friendly error messages throughout (Spanish)
- [ ] 7.2 Add loading states and progress indicators
- [ ] 7.3 Ensure responsive layout for mobile/tablet
- [ ] 7.4 Add empty states (no data, no transactions)
- [ ] 7.5 Write unit tests for ingestion, categorization, and database modules

### Phase 8: Deployment

- [ ] 8.1 Create Streamlit Community Cloud account and connect GitHub repo
- [ ] 8.2 Configure Supabase project and set secrets in Streamlit
- [ ] 8.3 Deploy and verify end-to-end functionality
- [ ] 8.4 Test on mobile device

## Verification & Testing Strategy

- [ ] Unit tests for Excel/CSV parsing with sample Fiwind file
- [ ] Unit tests for PDF parsing with sample Galicia Mastercard file
- [ ] Unit tests for categorization rules (Spanish keyword matching, edge cases)
- [ ] Unit tests for database CRUD operations (mocked Supabase)
- [ ] Integration test: upload Excel -> parse -> categorize -> save to DB -> display
- [ ] Integration test: upload PDF -> parse -> categorize -> save to DB -> display
- [ ] Manual testing: verify UI on desktop browser
- [ ] Manual testing: verify UI on mobile browser (responsive)
- [ ] Lint: `uv run ruff check src/`
- [ ] Typecheck: `uv run mypy src/`
- [ ] Full test suite: `uv run pytest`

## Risks, Assumptions & Unresolved Unknowns

### Assumptions

- User can manually download Excel/CSV/PDF extracts from their bank/card apps (no direct API integration for now)
- Bank extract formats are relatively stable (templates may need occasional updates)
- Single-user app is sufficient for now (no auth needed beyond Streamlit's basic protection)
- Supabase free tier (500MB) is sufficient for personal transaction history
- User is based in Argentina (ARS currency, Argentine number formats)

### Risks

- **Bank format changes**: Bank extracts may change format without notice, breaking parsers. Mitigation: template system makes updates easy.
- **PDF parsing variability**: PDF extracts can be inconsistent. Mitigation: pdfplumber with fallback regex extraction.
- **Streamlit Cold Start**: Free tier apps sleep after inactivity, causing slow initial load. Mitigation: acceptable for personal use.
- **Supabase free tier limits**: 500MB storage, 2 project limit. Mitigation: sufficient for years of personal data.
- **Multi-currency complexity**: Exchange rates needed for currency conversion. Mitigation: use a free exchange rate API or allow manual rate input.

### Unresolved Unknowns

- Exchange rate source for currency conversion (API vs manual input)
- Whether to support additional banks beyond Fiwind and Galicia Mastercard in the initial version

## Observable Acceptance Criteria

- [ ] User can upload a Fiwind Excel file and see transactions parsed and displayed
- [ ] User can upload a Galicia Mastercard PDF and see transactions parsed and displayed
- [ ] Uploaded transactions are automatically categorized based on description keywords (Spanish)
- [ ] User can manually change a transaction's category via dropdown in the transactions list
- [ ] Dashboard shows a pie chart of spending by category for the selected month
- [ ] Dashboard shows a line chart of monthly spending trends
- [ ] User can switch between ARS and USD currency views
- [ ] User can view bank-specific metadata (Fiwind Tipo, Galicia Comprobante, etc.) in the transactions list
- [ ] User can create a monthly budget for a category and see progress (spent vs. budget)
- [ ] App is accessible via URL on phone, laptop, and tablet browsers
- [ ] All UI text is in Spanish
- [ ] No secrets or credentials are stored in the repository
- [ ] All tests pass and lint/typecheck are clean
