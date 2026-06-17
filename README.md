# CRM Data Extract Agent

> Multi-agent pipeline that extracts insurance policy data from client documents into a unified CRM table.

> ⚠️ Real client data is excluded for privacy (PIPEDA) reasons — all sample data is fictional.

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
2. **Miner** reads every file in the folder recursively (see [OCR and File Processing](#-ocr-and-file-processing)), reasons over the extracted text, and returns structured JSON or `NO_ROW`.
3. **Forge** aggregates all miner results, deduplicates, normalizes, and writes a CSV to `tmp/batch_{N}_table.csv`.
4. A git commit tracks progress so the pipeline can resume.

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

| Document Type        | Tool Chain                                                                      |
| -------------------- | ------------------------------------------------------------------------------- |
| Text-layer PDFs      | `PyMuPDF` extracts embedded text directly                                       |
| Scanned/image PDFs   | `PyMuPDF` → `Pillow` (deskew / binarize / upscale) → `pytesseract` OCR          |
| Low-confidence pages | `PyMuPDF` renders the page to an image, Qwen3-VL-32B reads it via native vision |
| `.docx` files        | `python-docx` text extraction                                                   |
| `.xls` files         | `xlrd` data extraction                                                          |

## 📊 Output

> **Note:** Real client data is excluded for privacy (PIPEDA) reasons. The sample data in this repo (`client_info/`, `batch/`, `tmp/`, `full_crm_example.csv`) uses entirely fictional characters 🦸 for demonstration.

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

Each batch takes approximately **150 minutes** to process (25 folders × ~18 min per folder, 3 concurrent miners). The full 68-batch pipeline (68 × 150 min = 10,200 min ≈ 170 hours) completes in roughly **7 days** of continuous runtime.

## 🖥️ Hardware & Model

Runs entirely on a **Mac Mini M4 Pro** (48GB unified memory) with **Qwen3-VL-32B** (dense, Q4_K_M 4-bit quantization) served via Ollama 🦙 (~20GB VRAM). A single model instance serves both agents with up to 3 concurrent inference requests (`OLLAMA_NUM_PARALLEL=3`), zero model swaps, fully offline, and PIPEDA-compliant. No client data leaves the machine.

Both agents use the deterministic `crm-vl` model (`temperature 0`, fixed seed) defined in `Modelfile`. Build it once before running the pipeline:

```
ollama create crm-vl -f Modelfile
```

## 🗂️ Project Structure

```
crm-data-extract-agent/
├── client_info/            # 1,696 client folders with insurance documents
├── batch/                  # 68 batch files, each listing ~25 folder names
├── tmp/                    # 68 per-batch CSV outputs from Forge
├── docs/
│   ├── pipeline.drawio         # Data pipeline diagram (source)
│   ├── pipeline.svg            # Data pipeline diagram
│   ├── agent_arch.drawio       # Agent architecture diagram (source)
│   └── agent_arch.svg          # Agent architecture diagram
├── .codex/
│   ├── agents/
│   │   ├── forge_local.toml    # Batch orchestrator agent
│   │   └── miner_local.toml    # Per-folder extractor agent
│   └── config.toml             # Codex CLI configuration
├── Main_Prompt.md              # Pipeline entry point (read by Codex CLI)
├── Modelfile                   # Ollama model definition (crm-vl)
├── split_batches.py        # Stage 1: split folders into batches
├── join_batches.py         # Stage 3: merge batch CSVs into final CRM
├── full_crm_example.csv            # Final output
└── full_crm_example.xlsx           # Final output (Excel)
```

## 🚀 Proposed Architecture

![Revised Agent Architecture](docs/improved_architecture.svg)

> The current Miner architecture was chosen to ship a reliable pipeline within a tight timeline — it works correctly and processes all 1,696 folders end to end. The architecture below is the next iteration: same outputs, substantially faster and more accurate.

Today every Miner is a single Qwen3-VL **vision** agent that reads files, OCRs, reasons, and returns rows in one pass.

The proposed architecture splits that one heavy step into three cheaper ones:

1. **Deterministic extraction** — a plain Python script routes each file by extension (`PyMuPDF`, Tesseract, `python-docx`, `xlrd`), writes a clean `.md`, and attaches an extraction confidence score. No model involved.
2. **Text-only Reader model** — reasons over the compact `.md` instead of doing vision over every rendered page.
3. **Vision fallback** — native vision runs **only** on pages whose extraction confidence is low, gated by a threshold.

**Why it's faster and more accurate:**

- **Speed** — deterministic extraction is near-instant, and reasoning over short `.md` text is far cheaper than per-page vision. Expensive vision is reserved for the small fraction of low-confidence pages instead of every file.
- **Accuracy** — clean normalized `.md` gives the model a sharper input, the confidence score makes weak extractions explicit, and threshold-gated vision recovers exactly the pages where OCR fails.
