#!/usr/bin/env python3
"""Check for duplicate IDs in courses_chunks.jsonl"""
import json
from collections import Counter

jsonl_path = "data/processed/courses/courses_chunks.jsonl"

ids = []
with open(jsonl_path, 'r') as f:
    for line_num, line in enumerate(f, 1):
        if line.strip():
            try:
                chunk = json.loads(line)
                chunk_id = chunk.get('id')
                ids.append((chunk_id, line_num, chunk.get('meta', {}).get('course_code', 'UNKNOWN')))
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")

print(f"\nTotal chunks: {len(ids)}")
print(f"Unique IDs: {len(set(id[0] for id in ids))}")
print(f"Duplicates: {len(ids) - len(set(id[0] for id in ids))}")

# Find duplicates
id_counts = Counter(id[0] for id in ids)
duplicates = {id_val: count for id_val, count in id_counts.items() if count > 1}

if duplicates:
    print(f"\n⚠️  Found {len(duplicates)} duplicate IDs:")
    for dup_id, count in list(duplicates.items())[:10]:  # Show first 10
        matching_chunks = [chunk for chunk in ids if chunk[0] == dup_id]
        print(f"\n  ID: {dup_id} (appears {count} times)")
        for chunk_id, line_num, course_code in matching_chunks[:3]:
            print(f"    - Line {line_num}, Course: {course_code}")
    if len(duplicates) > 10:
        print(f"\n  ... and {len(duplicates) - 10} more duplicates")
else:
    print("\n✅ No duplicates found!")


