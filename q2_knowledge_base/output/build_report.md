# KB Build Report

- KB version: `2026.10.01-89661c9`  
- Built: 2026-10-01T13:54:56+00:00  
- Embeddings: 101 vectors (3072-d, gemini), 101 newly embedded

## Counts

| Metric | Value |
|---|---|
| source_files | 20 |
| sections_extracted | 101 |
| records | 101 |
| active | 97 |
| superseded | 4 |
| by_market | {'id_multifinance': 15, 'in_lender': 71, 'ph_life': 15} |
| by_category | {'faq': 25, 'compliance': 11, 'objection': 15, 'form': 2, 'insight': 6, 'policy': 6, 'charges': 9, 'qualification': 4, 'contact': 3, 'product': 4, 'marketing': 2, 'partnership': 3, 'process': 7} |

## Extraction failures and dropped content

| Source | Issue | Action |
|---|---|---|
| `in_lender/pdf/scanned_kyc_update_form.pdf` | PDF has no text layer (scanned image) | Skipped and queued for OCR (e.g. Tesseract / Document AI) + human check. |
| `in_lender/tables/charges_matrix.csv#row11` | Exact duplicate table row | Dropped duplicate row. |
| `in_lender/web/broken_offers_page.html` | No readable text after boilerplate removal (JS-rendered single-page app) | Skipped. Re-fetch with headless browser (Playwright) rendering before ingest. |

Cross-document boilerplate sentences removed: **0** (plus nav/header/footer/cookie banners/breadcrumbs/chat widgets removed structurally, and PDF running headers/footers/page numbers).

## Duplicates / superseded versions

| Kept | Source | Dropped | Source | Sim | Reason |
|---|---|---|---|---|---|
| kb_in_faq_c00b42 | `in_lender/web/faq.html` | kb_in_faq_4d9737 | `in_lender/web/faq_archive_2024.html` | 0.85 | same question, older/lower-authority version |
| kb_in_faq_3f3266 | `in_lender/web/faq.html` | kb_in_faq_0c088f | `in_lender/web/faq_archive_2024.html` | 1.0 | same question, older/lower-authority version |
| kb_in_faq_279e0d | `in_lender/web/faq.html` | kb_in_faq_23be83 | `in_lender/web/faq_archive_2024.html` | 0.27 | same question, older/lower-authority version |
| kb_in_faq_1848f4 | `in_lender/web/faq.html` | kb_in_faq_de9c88 | `in_lender/web/faq_archive_2024.html` | 1.0 | same question, older/lower-authority version |

## Source errors and conflicts (auto-reconciled to authoritative source, flagged for owner review)

| Record | Source | Fact | Original | Corrected | Authority |
|---|---|---|---|---|---|
| kb_in_objection_02a0c6 | `in_lender/docs/objection_playbook.md` | grace_period_days | “grace period of 5” | “grace period of 3” | `in_lender/pdf/Schedule_of_Charges_and_Policies_2026.pdf` |
| kb_in_charges_29d85f | `in_lender/tables/charges_matrix.csv` | bounce_charge_inr | “Bounce charge: ₹5900” | “Bounce charge: ₹590” | `in_lender/pdf/Schedule_of_Charges_and_Policies_2026.pdf` |

## PII protection

Detected and replaced with typed placeholders before indexing (raw values are never written to the KB):

| Type | Count |
|---|---|
| AADHAAR | 1 |
| ACCOUNT_NO | 1 |
| CARD | 1 |
| EMAIL | 1 |
| PAN | 1 |
| PERSON | 12 |
| PHONE | 6 |
| UTR | 1 |

Records that contained PII: 6 (all `audience=internal` call notes; excluded from customer-facing retrieval).

## Changelog vs previous build

```json
{
 "added": [],
 "removed": [],
 "modified": []
}
```