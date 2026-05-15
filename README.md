# CRM Data Extract Agent

> Multi-agent pipeline that extracts insurance policy data from client documents into a unified CRM table.

## 📋 The Problem

An insurance brokerage with years of messy, unstructured client data spread across 1,696 folders. Folders are named after families or referrals, one folder can contain multiple clients. Inside: nested subfolders, mixed file formats (PDFs, scanned images, Word docs, spreadsheets), quotes mixed in with actual policy confirmations, and no consistent naming or structure.

Traditional parsing is impossible. Every folder is different. An LLM-based approach handles the variability by reading and reasoning over documents the way a human would, but at scale.

## ⚙️ How It Works

![Pipeline](docs/pipeline.svg)

### Stage 1 — Split

`split_batches.py` splits the 1,696 client folder names into 68 batch files of ~25 folders each, written to `batch/`.

![Agent Architecture](docs/agent_arch.svg)

### Stage 2 — Extract

Codex CLI reads `Main_Prompt.md`, checks the last git commit for progress (`Batch X,Y,Z,W Done`), and picks the next 4 batches to process. For each batch:

1. **Forge** agent reads the batch file, spawns **Miner** agents per folder (up to 3 concurrently).
2. **Miner** reads every file in the folder recursively, extracts text from PDFs, OCRs scanned documents using the model's native vision, reads Word/Excel files, and returns structured JSON or `NO_ROW`. Up to 3 miners run concurrently per batch.
3. **Forge** aggregates all miner results, deduplicates, normalizes, and writes a CSV to `tmp/batch_{N}_table.csv`.
4. A git commit (`Batch X,Y,Z,W Done`) tracks progress so the pipeline can resume.

### Stage 3 — Join

`join_batches.py` merges all 68 batch CSVs from `tmp/` into `full_crm.csv` and `full_crm.xlsx`.

## 🧹 Data Normalization

Miner agents follow strict normalization rules before returning data:

- **Money fields** (`Premium`, `Deductible`, `Coverage`): no `$` or commas, exactly 2 decimal places, currency code appended when known (e.g., `453.00 CAD`)
- **String fields**: no embedded newlines/tabs, collapsed whitespace, trimmed
- **Expansion**: one row per insured person per confirmed policy (family policies produce multiple rows)
- **Inclusion**: all confirmed policies extracted, including expired, cancelled, and renewed ones
- **Deduplication**: by `Folder name` + `First name` + `Last name` + `Policy #` + `Effective`

## 📂 OCR and File Processing

| Document Type           | Tool Chain                                                                |
| ----------------------- | ------------------------------------------------------------------------- |
| Text-layer PDFs         | `PyMuPDF` extracts embedded text directly                                 |
| Scanned/image PDFs      | `PyMuPDF` renders pages to images, Qwen2.5-VL-32B reads via native vision |
| Scanned PDFs (fallback) | `PyMuPDF` → `Pillow` → `pytesseract` OCR                                  |
| `.docx` files           | `python-docx` text extraction                                             |
| `.xls` files            | `xlrd` data extraction                                                    |

The primary OCR method is **Qwen2.5-VL-32B's native vision** — the model processes page images directly without needing traditional OCR. `pytesseract` serves as a fallback for edge cases.

## 📊 Output

> **Note:** The sample data included in this repository (`client_info/`, `batch/`, `tmp/`, and `full_crm_example.csv`) uses entirely fictional characters 🦸 for demonstration purposes. No real client data is included.

A 16-column CRM table with one row per (insured person, policy) combination.

| Column       | Example                            |
| ------------ | ---------------------------------- |
| Folder name  | `SMITH, JOHN`                      |
| First name   | `JOHN`                             |
| Last name    | `SMITH`                            |
| DOB          | `1985-03-14`                       |
| Email        | `JOHN@EXAMPLE.COM`                 |
| Phone number | `+1 (416) 555-0123`                |
| Address      | `123 MAIN ST, TORONTO, ON M5V 2T6` |
| Product      | `Travel`                           |
| Policy #     | `TRV-2024-00123`                   |
| Effective    | `2024-01-15`                       |
| Expiry       | `2025-01-15`                       |
| Carrier      | `Manulife`                         |
| Premium      | `453.00 CAD`                       |
| Deductible   | `0.00 CAD`                         |
| Coverage     | `50000.00 CAD`                     |
| Notes        | `Source: confirmation.pdf`         |

## ⏱️ Performance

Each batch takes approximately **100 minutes** to process (25 folders × ~8 min per folder, 3 concurrent miners). The full 68-batch pipeline completes in roughly **5 days** of continuous runtime.

## 🖥️ Hardware & Model

Runs entirely on a **Mac Mini M4 Pro** (24GB unified memory) with **Qwen2.5-VL-32B-Instruct** served via Ollama 🦙 (~20GB VRAM). A single model instance serves both agents with up to 3 concurrent inference requests (`OLLAMA_NUM_PARALLEL=3`), zero model swaps, fully offline, and PIPEDA-compliant. No client data leaves the machine.

## 🗂️ Project Structure

```
crm-data-extract-agent/
├── client_info/            # 1,696 client folders with insurance documents
├── batch/                  # 68 batch files, each listing ~25 folder names
├── tmp/                    # 68 per-batch CSV outputs from Forge
├── docs/
│   ├── pipeline.svg            # Data pipeline diagram
│   └── agent_arch.svg          # Agent architecture diagram
├── .codex/
│   └── agents/
│       ├── forge_local.toml    # Batch orchestrator agent
│       └── miner_local.toml    # Per-folder extractor agent
├── Main_Prompt.md              # Pipeline entry point (read by Codex CLI)
├── split_batches.py        # Stage 1: split folders into batches
├── join_batches.py         # Stage 3: merge batch CSVs into final CRM
├── full_crm.csv            # Final output
└── full_crm.xlsx           # Final output (Excel)
```
