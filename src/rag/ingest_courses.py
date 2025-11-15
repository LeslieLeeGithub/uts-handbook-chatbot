#!/usr/bin/env python3
"""
Course JSON ingestion script for UTS Handbook chatbot
Processes course JSON files from data/courses/ into chunks for RAG

Outputs JSON Lines with:
{
  "id": "<uuidv5>",
  "text": "<chunk text>",
  "meta": {
    "course_code": "C10302",
    "course_name": "Bachelor of Sport and Exercise Science...",
    "chunk_type": "overview|admission|career|structure|learning_outcomes|...",
    "source_url": "https://handbook.uts.edu.au/courses/c10302.html",
    "ingested_at": "2025-11-10T00:00:00Z"
  }
}
"""
import argparse
import json
import re
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse


def extract_course_code_from_filename(filename: str) -> Optional[str]:
    """Extract course code from filename (e.g., C10302 from ..._C10302.json)"""
    # Look for pattern like C10302, C20060, etc. (C followed by 5 digits)
    match = re.search(r'([C]\d{5})', filename)
    if match:
        return match.group(1)
    return None


def extract_course_code_from_url(url: str) -> Optional[str]:
    """Extract course code from URL (e.g., c10302.html -> C10302)"""
    if not url:
        return None
    # Extract from URL like https://handbook.uts.edu.au/courses/c10302.html
    match = re.search(r'/courses/([cC]\d{5})', url)
    if match:
        return match.group(1).upper()
    return None


def get_course_code(course_data: Dict, filename: str) -> str:
    """Get correct course code from JSON, URL, or filename"""
    # Try JSON first
    code = course_data.get('course_code', '').strip()
    if code and re.match(r'^[C]\d{5}$', code, re.IGNORECASE):
        return code.upper()
    
    # Try source URL
    metadata = course_data.get('metadata', {})
    source_url = metadata.get('source_url', '')
    code = extract_course_code_from_url(source_url)
    if code:
        return code
    
    # Try filename
    code = extract_course_code_from_url(filename)
    if code:
        return code
    
    # Fallback: use what's in JSON (even if wrong format)
    return course_data.get('course_code', 'UNKNOWN').strip().upper()


def make_chunk_uuid(course_code: str, chunk_type: str, chunk_index: int, unique_id: str = "") -> str:
    """Generate deterministic UUIDv5 for chunk
    
    Args:
        course_code: Course code (may not be unique)
        chunk_type: Type of chunk (overview, admission, etc.)
        chunk_index: Index of chunk within course
        unique_id: Unique identifier (filename or source_url) to ensure uniqueness
    """
    # Include unique_id to ensure uniqueness even if course codes are duplicated
    key = f"course|{course_code}|type:{chunk_type}|chunk:{chunk_index}|unique:{unique_id}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def format_field_value(value: Any) -> str:
    """Format a field value for display"""
    if value is None:
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        if isinstance(value[0], dict):
            # Handle learning outcomes
            return "\n".join([f"{item.get('number', '')}. {item.get('text', '')}" 
                            for item in value if item.get('text')])
        return ", ".join(str(v) for v in value if v)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def create_chunks_from_course(course_data: Dict, filename: str) -> List[Dict]:
    """Create chunks from a course JSON file"""
    chunks = []
    
    # Get course code (with fallback logic)
    course_code = get_course_code(course_data, filename)
    course_name = course_data.get('course_name', '').strip()
    
    # Fix course name if it's wrong (some have "TEQSA Category: Australian University")
    if not course_name or course_name == "TEQSA Category: Australian University":
        # Try to extract from filename
        filename_parts = Path(filename).stem.split('_')
        # Remove course code and None parts
        name_parts = [p for p in filename_parts 
                     if p not in ['None', ''] and not re.match(r'^[C]\d{5}$', p, re.IGNORECASE)]
        if name_parts:
            course_name = ' '.join(name_parts).replace('_', ' ')
    
    metadata = course_data.get('metadata', {})
    source_url = metadata.get('source_url', '')
    ingested_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    
    # Use filename as unique identifier for UUID generation
    # This ensures uniqueness even if multiple JSON files have the same course_code or source_url
    # (Some courses may have multiple JSON files with the same source_url)
    unique_id = str(Path(filename).stem)  # Use filename without extension
    
    # Define chunkable fields with their labels
    chunkable_fields = {
        'overview': 'Overview',
        'admission_requirements': 'Admission Requirements',
        'career_options': 'Career Options',
        'course_structure': 'Course Structure',
        'professional_recognition': 'Professional Recognition',
        'inherent_requirements': 'Inherent Requirements',
        'structure_notes': 'Structure Notes',
        'notes': 'Notes',
    }
    
    chunk_index = 0
    
    # Create chunks for each field
    for field, label in chunkable_fields.items():
        value = course_data.get(field)
        if not value or value == "None" or (isinstance(value, str) and value.strip() == ""):
            continue
        
        text = format_field_value(value)
        if not text or len(text.strip()) < 50:
            continue
        
        # Create chunk
        chunk_id = make_chunk_uuid(course_code, field, chunk_index, unique_id)
        chunk_index += 1
        
        # Format text with label
        chunk_text = f"{label}:\n{text}"
        
        chunks.append({
            "id": chunk_id,
            "text": chunk_text,
            "meta": {
                "course_code": course_code,
                "course_name": course_name,
                "chunk_type": field,
                "chunk_label": label,
                "source_url": source_url,
                "ingested_at": ingested_at,
            }
        })
    
    # Handle learning outcomes separately (they're a list of dicts)
    learning_outcomes = course_data.get('learning_outcomes', [])
    if learning_outcomes and isinstance(learning_outcomes, list):
        outcomes_text = "\n".join([
            f"{item.get('number', '')}. {item.get('text', '')}"
            for item in learning_outcomes
            if item.get('text')
        ])
        if outcomes_text:
            chunk_id = make_chunk_uuid(course_code, 'learning_outcomes', chunk_index, unique_id)
            chunk_index += 1
            chunks.append({
                "id": chunk_id,
                "text": f"Learning Outcomes:\n{outcomes_text}",
                "meta": {
                    "course_code": course_code,
                    "course_name": course_name,
                    "chunk_type": "learning_outcomes",
                    "chunk_label": "Learning Outcomes",
                    "source_url": source_url,
                    "ingested_at": ingested_at,
                }
            })
    
    # Create a comprehensive course info chunk (for better retrieval by course name/code)
    course_info_parts = []
    if course_name:
        course_info_parts.append(f"Course Name: {course_name}")
    if course_code:
        course_info_parts.append(f"Course Code: {course_code}")
    if course_data.get('credit_points'):
        course_info_parts.append(f"Credit Points: {course_data.get('credit_points')}")
    if course_data.get('cricos_code') and course_data.get('cricos_code') != "None":
        course_info_parts.append(f"CRICOS Code: {course_data.get('cricos_code')}")
    if course_data.get('faculty'):
        faculty_str = ", ".join(course_data.get('faculty', []))
        if faculty_str:
            course_info_parts.append(f"Faculty: {faculty_str}")
    if course_data.get('study_level'):
        course_info_parts.append(f"Study Level: {course_data.get('study_level')}")
    if course_data.get('duration_fulltime'):
        course_info_parts.append(f"Duration (Full-time): {course_data.get('duration_fulltime')}")
    if course_data.get('duration_parttime'):
        course_info_parts.append(f"Duration (Part-time): {course_data.get('duration_parttime')}")
    if course_data.get('location'):
        location_str = ", ".join(course_data.get('location', []))
        if location_str:
            course_info_parts.append(f"Location: {location_str}")
    if course_data.get('awards'):
        awards_str = ", ".join(course_data.get('awards', []))
        if awards_str:
            course_info_parts.append(f"Awards: {awards_str}")
    
    # Add overview to course info if it exists
    if course_data.get('overview'):
        course_info_parts.append(f"\nOverview:\n{course_data.get('overview')}")
    
    if course_info_parts:
        chunk_id = make_chunk_uuid(course_code, 'course_info', chunk_index, unique_id)
        chunk_index += 1
        chunks.append({
            "id": chunk_id,
            "text": "\n".join(course_info_parts),
            "meta": {
                "course_code": course_code,
                "course_name": course_name,
                "chunk_type": "course_info",
                "chunk_label": "Course Information",
                "source_url": source_url,
                "ingested_at": ingested_at,
            }
        })
    
    return chunks


def main():
    parser = argparse.ArgumentParser(
        description="Ingest UTS course JSON files into chunks for RAG"
    )
    parser.add_argument(
        "--courses_dir",
        required=True,
        help="Directory containing course JSON files (e.g., data/courses/)"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSONL file path (e.g., data/processed/courses_chunks.jsonl)"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Don't write file; just print stats"
    )
    args = parser.parse_args()
    
    courses_dir = Path(args.courses_dir)
    if not courses_dir.is_dir():
        raise SystemExit(f"Not a directory: {courses_dir}")
    
    # Find all JSON files
    json_files = sorted(courses_dir.glob("*.json"))
    if not json_files:
        raise SystemExit(f"No JSON files found in {courses_dir}")
    
    print(f"Found {len(json_files)} course JSON files")
    
    all_chunks = []
    courses_processed = 0
    courses_skipped = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                course_data = json.load(f)
            
            chunks = create_chunks_from_course(course_data, json_file.name)
            if chunks:
                all_chunks.extend(chunks)
                courses_processed += 1
                print(f"✅ {json_file.name}: {len(chunks)} chunks")
            else:
                courses_skipped += 1
                print(f"⚠️  {json_file.name}: No chunks created (empty/invalid data)")
        
        except Exception as e:
            courses_skipped += 1
            print(f"❌ Error processing {json_file.name}: {e}")
    
    print(f"\n{'='*70}")
    print(f"Total courses processed: {courses_processed}")
    print(f"Total courses skipped: {courses_skipped}")
    print(f"Total chunks created: {len(all_chunks)}")
    print(f"{'='*70}")
    
    if args.dry_run:
        print("\n[DRY RUN] Not writing file")
        return
    
    # Write output
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Wrote {len(all_chunks)} chunks → {out_path}")


if __name__ == "__main__":
    main()

