# Training / intake corpora

Local mirrors used by SwarmCFO document intake (`agents/erp/intake/`).

## daitavan/financial-documents

Source: https://huggingface.co/datasets/daitavan/financial-documents

Path: `accounting_samples/financial-documents/financial-documents/ocr/{class}/*.json`

Classes → ERP mapping:

| OCR class | ERP kind |
| --- | --- |
| `balance_sheets` | chart_of_accounts |
| `income_statement` | revenue |
| `cash_flow` | bank |
| `notes` / `others` | scanned_financial |

Each JSON is a list of `{ "word", "bounding_box": [x0,y0,x1,y1] }` tokens.

## TheFinAI/FinCriticalED

Source: https://huggingface.co/datasets/TheFinAI/FinCriticalED

Path: `scans/raw_input.csv` (`id`, `image`, `matched_html`)

HTML is stripped to text, SEC form type detected (Form 4 / 10-K / …), stored in the vault as critical filings.

## API

```bash
POST /v1/erp/intake/train-batch?per_class=3&fincritical_limit=3
POST /v1/erp/intake/ocr          # upload one OCR JSON
POST /v1/erp/intake/fincritical?limit=5
POST /v1/erp/intake/classify
```

Or in the UI: **Suite → Upload → Index train_data**.
