#!/usr/bin/env python3
"""
Ingest CSV and JSON files from data/raw into a single normalized JSONL for indexing.
"""

import csv
import json
from pathlib import Path
from typing import Dict, Iterable


RAW_CSV_DIR = Path(__file__).resolve().parents[2] / 'data' / 'raw' / 'csv'
RAW_JSON_DIR = Path(__file__).resolve().parents[2] / 'data' / 'raw' / 'json'
PROCESSED_DIR = Path(__file__).resolve().parents[2] / 'data' / 'processed'
OUTPUT_JSONL = PROCESSED_DIR / 'documents.jsonl'


def iter_csv_documents() -> Iterable[Dict]:
    if not RAW_CSV_DIR.exists():
        return
    for csv_path in RAW_CSV_DIR.glob('*.csv'):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield {
                    'source': str(csv_path.name),
                    'text': '\n'.join([f"{k}: {v}" for k, v in row.items() if v]),
                    'meta': {'type': 'csv'}
                }


def iter_json_documents() -> Iterable[Dict]:
    if not RAW_JSON_DIR.exists():
        return
    for json_path in RAW_JSON_DIR.glob('*.json'):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Accept either dict or list; flatten to simple text
            text = json.dumps(data, ensure_ascii=False)
            yield {
                'source': str(json_path.name),
                'text': text,
                'meta': {'type': 'json'}
            }


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, 'w', encoding='utf-8') as out:
        for doc in iter_csv_documents() or []:
            out.write(json.dumps(doc, ensure_ascii=False) + '\n')
        for doc in iter_json_documents() or []:
            out.write(json.dumps(doc, ensure_ascii=False) + '\n')
    print(f"Wrote {OUTPUT_JSONL}")


if __name__ == '__main__':
    main()


