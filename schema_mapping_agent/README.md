# Schema Mapping Agent

LLM-powered schema mapping backend for TDS (Tax Deducted at Source) reconciliation pipeline. This agent intelligently maps columns from uploaded Excel files (Tally ledger exports, Form 26AS, etc.) to a standardized internal schema.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Raw XLSX      │────▶│  Schema Mapper   │────▶│ schema_map.json │
│   File          │     │  Agent (LLM)     │     │   (draft)       │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                              ┌───────────────────────────┼───────────┐
                              │                           │           │
                              ▼                           ▼           ▼
                    ┌─────────────────┐        ┌─────────────────┐   │
                    │  Auto-Approved  │        │  Human Review   │   │
                    │ (confidence>0.85│        │      UI         │   │
                    └────────┬────────┘        └────────┬────────┘   │
                             │                          │            │
                             └──────────────┬───────────┘            │
                                            ▼                        │
                                   ┌─────────────────┐               │
                                   │ Approved schema │◀──────────────┘
                                   │   _map.json     │
                                   └────────┬────────┘
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │  Parser Agent   │
                                   │ (uses mapping)  │
                                   └─────────────────┘
```

## Features

- **Intelligent Column Mapping**: Uses Claude API to map source columns to internal schema
- **Confidence Scoring**: Each mapping includes a confidence score (0.0-1.0)
- **Auto-Approval**: Mappings with confidence > 0.85 are auto-approved
- **Human Review**: Low-confidence mappings are flagged for manual review
- **Per-Client Storage**: Schema maps saved per client folder
- **Past Mapping Cache**: Leverages previous mappings for similar files
- **Multi-Sheet Support**: Handles Excel files with multiple sheets

## Tech Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI
- **LLM**: Claude API (Anthropic)
- **File Handling**: pandas, openpyxl

## Installation

```bash
# Clone/navigate to the project
cd schema_mapping_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your-claude-api-key"
export STORAGE_PATH="./storage"  # Optional, defaults to ./storage
```

## Running the Server

```bash
# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or run directly
python app/main.py
```

The API will be available at `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

## API Endpoints

### Health & Info

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/internal-schema/{file_type}` | GET | Get internal schema definition |

### File Upload & Detection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload Excel file, detect schema |

### Schema Mapping

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/map` | POST | Generate mapping via LLM |
| `/map-and-approve` | POST | Upload + map + auto-approve if high confidence |
| `/approve` | POST | Save approved mapping after human review |

### Schema Map Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/clients` | GET | List all clients |
| `/schema-maps/{client_id}` | GET | List client's schema maps |
| `/schema-maps/{client_id}/{file_type}` | GET | Get specific schema map |
| `/schema-maps/{client_id}/{file_type}` | DELETE | Delete schema map |

## Usage Examples

### 1. Upload and Detect Schema

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@Tally_extract.xlsx" \
  -F "client_id=HPC_LTD"
```

Response:
```json
{
  "success": true,
  "client_id": "HPC_LTD",
  "detected_type": "ledger",
  "columns": ["Date", "Particulars", "Voucher No.", "Value", ...],
  "sample_data": [...],
  "sheet_names": ["Purchase Register", "Journal Register"]
}
```

### 2. Generate Schema Mapping

```bash
curl -X POST "http://localhost:8000/map" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "HPC_LTD",
    "columns": ["Date", "Particulars", "Voucher No.", "Value", "Gross Total"],
    "sample_data": [
      {"Date": "2024-04-12", "Particulars": "A K Syntex", "Voucher No.": 1, "Value": 38986.4},
      ...
    ],
    "file_type": "ledger"
  }'
```

Response:
```json
{
  "success": true,
  "client_id": "HPC_LTD",
  "file_type": "ledger",
  "mappings": {
    "Date": {"source_column": "Date", "mapped_to": "date", "confidence": 0.98, "reasoning": "..."},
    "Particulars": {"source_column": "Particulars", "mapped_to": "party_name", "confidence": 0.95, "reasoning": "..."},
    ...
  },
  "overall_confidence": 0.92,
  "auto_approve": true,
  "unmapped_columns": [],
  "required_fields_covered": ["date", "party_name", "value"],
  "required_fields_missing": []
}
```

### 3. Approve Mapping (After Human Review)

```bash
curl -X POST "http://localhost:8000/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "HPC_LTD",
    "file_type": "ledger",
    "mappings": {
      "Date": "date",
      "Particulars": "party_name",
      "Voucher No.": "voucher_number",
      "Value": "value",
      "Gross Total": "gross_total"
    },
    "confidence_scores": {
      "Date": 0.98,
      "Particulars": 0.95,
      ...
    }
  }'
```

Response:
```json
{
  "success": true,
  "message": "Schema mapping approved and saved successfully",
  "saved_path": "./storage/hpcltd/ledger_schema_map.json",
  "version": 1
}
```

### 4. Convenience: Upload + Map + Auto-Approve

```bash
curl -X POST "http://localhost:8000/map-and-approve" \
  -F "file=@Form_26.xlsx" \
  -F "client_id=HPC_LTD" \
  -F "auto_approve_threshold=0.85"
```

### 5. Retrieve Saved Schema Map

```bash
curl "http://localhost:8000/schema-maps/HPC_LTD/ledger"
```

Response:
```json
{
  "success": true,
  "schema_map": {
    "client_id": "HPC_LTD",
    "file_type": "ledger",
    "mappings": {
      "Date": "date",
      "Particulars": "party_name",
      ...
    },
    "version": 1,
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

## Internal Schemas

### Tally Ledger Schema (`ledger`)

| Internal Field | Description | Required |
|----------------|-------------|----------|
| `date` | Transaction date | Yes |
| `party_name` | Vendor/Party name | Yes |
| `voucher_number` | Invoice/Voucher number | Yes |
| `value` | Net amount (excl. GST) | Yes |
| `gross_total` | Gross total amount | No |
| `cgst_amount` | Central GST | No |
| `sgst_amount` | State GST | No |
| `igst_amount` | Integrated GST | No |
| `tds_amount` | TDS deducted | No |
| `tds_section` | TDS section code | No |
| `pan` | PAN number | No |
| `gstin` | GSTIN | No |

### Form 26AS/TDS Schema (`tds`)

| Internal Field | Description | Required |
|----------------|-------------|----------|
| `party_name` | Deductee name | Yes |
| `pan` | PAN number | Yes |
| `tds_section` | TDS section (194C, 194J, etc.) | Yes |
| `amount_paid` | Amount paid/credited | Yes |
| `date_of_payment` | Payment date | Yes |
| `income_tax` | Income tax deducted | Yes |
| `surcharge` | Surcharge amount | No |
| `cess` | Health & Education Cess | No |
| `tax_rate` | TDS rate percentage | Yes |
| `tax_deducted` | Total tax deducted | Yes |
| `date_of_deduction` | TDS deduction date | Yes |
| `certificate_number` | TDS certificate ref | No |

## Storage Structure

```
storage/
├── client_a_pan/
│   ├── ledger_schema_map.json
│   └── tds_schema_map.json
├── client_b_pan/
│   ├── ledger_Purchase Register_schema_map.json
│   ├── ledger_Journal Register_schema_map.json
│   └── tds_schema_map.json
└── ...
```

## Client Identification

Clients are identified by a unique string. Recommended approaches:
- **Company PAN** (e.g., `AAJCR2207E`)
- **Database UUID** from your company table
- **Custom client code** (e.g., `HPC_LTD`)

The client ID is sanitized for filesystem safety (lowercase, special chars replaced with `_`).

## Confidence Scoring

| Confidence | Interpretation | Action |
|------------|----------------|--------|
| 0.95-1.00 | Exact match | Auto-approve |
| 0.85-0.94 | Strong match | Auto-approve |
| 0.70-0.84 | Likely match | Human review recommended |
| 0.50-0.69 | Uncertain | Human review required |
| < 0.50 | No match | Mark as unmapped |

Auto-approval requires:
- Overall confidence ≥ 0.85
- All critical fields mapped (date, party_name, value/amount_paid)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key |
| `STORAGE_PATH` | No | `./storage` | Base path for schema map storage |

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid file type, etc.)
- `404`: Schema map not found
- `500`: Server error
- `503`: LLM not configured

## Future Enhancements

- [ ] Vector similarity search for past mappings (pgvector)
- [ ] Support for CSV files
- [ ] Batch mapping for multiple files
- [ ] Mapping validation against actual data
- [ ] A/B testing different LLM models

## License

MIT
