---
name: docling-pdf-to-markdown
description: Convert PDFs and other documents to Markdown via Docling service. Use when the user wants text, tables, or OCR extracted from PDF/DOCX/PPTX/image-based documents into Markdown files. Handles page ranges and batch conversion.
---

# Docling document → Markdown

Wraps `scripts/docling_convert.py`, a thin CLI over the ScaDS.AI Docling HTTP API.

## Prerequisites

- API key in `~/.tudai-api-key` (first line, key only). Script exits 1 if missing/empty.
- `requests` installed.
- Network access to `https://llm.scads.ai/docling`.

## Usage

```bash
python scripts/docling_convert.py FILE [FILE ...] [--pages 1-20] [--output-dir DIR]
```

- `FILE`: one or more documents. At least one required.
- `--pages N-M` or `--pages N`: convert only that page range. Default: whole document.
- `--output-dir`: default `converted/`. Created if absent.

Output path: `<output-dir>/<filename><.pN-M>.md`, e.g. `converted/report.pdf.p1-20.md`.

## Behavior to expect

| Condition | Result |
|---|---|
| Any input file ≥ 50 MB | Prints the path, exits **1 immediately**, converts nothing |
| Target `.md` already exists | Skips that file, **not** counted as failure |
| File not found | Skips, counted as failure |
| HTTP error / timeout / empty result | Prints message, counted as failure |
| Any failure | Exit code 1 |
| All succeeded or skipped | Exit code 0 |

No retries. No rate-limit handling — a 429 is reported as a plain HTTP failure.
Request timeout: 900 s. Server-side document timeout: 840 s.

Fixed pipeline settings (OCR on, `easyocr`, 9 languages, accurate table mode, images exported as placeholders). Do **not** edit them: the service keeps a warm GPU pipeline for exactly these values; other values force a model reload or get rejected.

## Agent workflow

1. Check size before invoking: `ls -l FILE`. If ≥ 50 MB, split first (e.g. `qpdf --split-pages`, `pdftk burst`) — do not call the script expecting partial work.
2. Run the script, one invocation for the whole batch.
3. On "No answer within 15 minutes": re-run with a narrower `--pages` range rather than retrying unchanged.
4. On "already exists": delete the target only if the user wants a fresh conversion.
5. Read the resulting `.md` files for downstream tasks.

## Limitations

- No image/picture description (vision pipeline removed).
- No server-capability/limits query.
- Serial processing by design; do not parallelize — the service queues all users together.
- Error output is minimal (status code only); inspect the service directly if diagnosis is needed.
```
