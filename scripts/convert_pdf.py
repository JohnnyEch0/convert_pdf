#!/usr/bin/env python
# Find instructions how to install dependencies and how to run this script in README.md
import argparse
import os
import sys
import time
from pathlib import Path

import requests

my_api_key = ""
path_to_key = os.path.join(os.path.expanduser("~"), ".tudai-api-key")
if os.path.exists(path_to_key):
    with open(path_to_key) as keyfile:
        my_api_key = keyfile.readline().strip()
if len(my_api_key) < 1:
    print("Error: The key file '.tudai-api-key' did not contain any key. Please make sure the file exists and contains only your API key.")
    exit(1)

DOCLING_URL = "https://llm.scads.ai/docling"
TEXT = {
    "do_ocr": "true",
    "force_ocr": "false",
    "ocr_preset": "easyocr",
    "ocr_lang": ["en", "de", "fr", "es", "it", "nl", "pl", "cs", "pt"],
    "do_table_structure": "true",
    "table_mode": "accurate",
    "document_timeout": "840",
}

# These only change what is returned, not how the document is converted.
OUTPUT = {"to_formats": "md", "image_export_mode": "placeholder"}

MAX_FILE_SIZE = 50 * 1024 * 1024
REQUEST_TIMEOUT = 900


def convert(path, pages):
    data = {**TEXT, **OUTPUT}
    if pages:
        data["page_range"] = [str(pages[0]), str(pages[1])]

    with path.open("rb") as document:
        response = requests.post(
            f"{DOCLING_URL}/v1/convert/file",
            headers={"Authorization": f"Bearer {my_api_key}"},
            files={"files": (path.name, document)},
            data=data,
            timeout=REQUEST_TIMEOUT,
        )
    if not response.ok:
        print(f"  Failed with HTTP {response.status_code}")
        return None
    return response.json()


def parse_pages(value):
    first, _, last = value.partition("-")
    return int(first), int(last or first)


def main():
    parser = argparse.ArgumentParser(description="Convert documents to Markdown with Docling on llm.scads.ai.")
    parser.add_argument("files", nargs="+", type=Path, help="documents to convert, one after another")
    parser.add_argument("--pages", type=parse_pages, help="convert only these pages, e.g. 1-20")
    parser.add_argument("--output-dir", type=Path, default=Path("converted"), help="where to write the Markdown files")
    args = parser.parse_args()

    # Check sizes before doing any work: a file that is too large aborts the run.
    for path in args.files:
        if path.is_file() and path.stat().st_size >= MAX_FILE_SIZE:
            print(f"{path}: 50 MB or larger, split it first.")
            return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    # One file at a time: the service converts only a few documents at once for all
    # users together, so parallel requests just wait in its queue.
    for path in args.files:
        pages = f".p{args.pages[0]}-{args.pages[1]}" if args.pages else ""
        target = args.output_dir / f"{path.name}{pages}.md"
        if target.exists():
            print(f"Skipping {path}: {target} exists already (delete it to convert again).")
            continue
        if not path.is_file():
            print(f"Skipping {path}: file not found.")
            failed += 1
            continue

        print(f"Converting {path} ...")
        started = time.monotonic()
        try:
            result = convert(path, args.pages)
        except requests.Timeout:
            print("  No answer within 15 minutes. Convert fewer pages at once (--pages).")
            result = None
        except requests.RequestException as error:
            print(f"  Request failed: {error}")
            result = None
        if result is None:
            failed += 1
            continue

        markdown = (result.get("document") or {}).get("md_content")
        if not markdown:
            print(f"  No text returned (status: {result.get('status')}).")
            failed += 1
            continue
        target.write_text(markdown, encoding="utf-8")
        print(f"  {result.get('status')}: converted in {result.get('processing_time', 0):.1f} s, "
              f"{time.monotonic() - started:.0f} s including the queue -> {target}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
