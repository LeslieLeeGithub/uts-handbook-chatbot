#!/usr/bin/env python3
"""
Check which courses from CSV are missing from the courses/ directory.
"""

import csv
import json
from pathlib import Path
from typing import Set, List, Dict


def sanitize_filename(name: str) -> str:
    """Sanitize filename by removing invalid characters."""
    import re
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    name = name.replace(' ', '_')
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return name


def get_existing_course_codes(courses_dir: Path) -> Set[str]:
    """Get set of course codes from existing JSON files."""
    existing_codes = set()
    if not courses_dir.exists():
        return existing_codes
    
    for json_file in courses_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                course_code = data.get('course_code', '').strip()
                if course_code:
                    existing_codes.add(course_code)
        except Exception as e:
            print(f"⚠️  Error reading {json_file.name}: {e}")
    
    return existing_codes


def get_missing_courses(csv_path: Path, courses_dir: Path) -> List[Dict]:
    """Get list of courses from CSV that don't have JSON files yet."""
    existing_codes = get_existing_course_codes(courses_dir)
    
    missing_courses = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            course_code = row.get('Course Code', '').strip()
            url = row.get('Link', '').strip()
            
            if course_code and url:
                if course_code not in existing_codes:
                    missing_courses.append(row)
    
    return missing_courses


def main():
    """Main function to check missing courses."""
    csv_path = Path(__file__).parent / "data" / "original_course_list_excel" / "merged_Admission_Courses.csv"
    courses_dir = Path(__file__).parent / "data" / "courses"
    
    print("🔍 Checking for missing courses...")
    print("=" * 70)
    
    # Get existing course codes
    print("📂 Scanning existing JSON files...")
    existing_codes = get_existing_course_codes(courses_dir)
    print(f"✅ Found {len(existing_codes)} existing course JSON files")
    
    # Get all courses from CSV
    print("\n📖 Reading CSV file...")
    all_courses = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            course_code = row.get('Course Code', '').strip()
            url = row.get('Link', '').strip()
            if course_code and url:
                all_courses.append(row)
    
    print(f"📊 Found {len(all_courses)} courses in CSV")
    
    # Find missing courses
    missing_courses = get_missing_courses(csv_path, courses_dir)
    
    print("\n" + "=" * 70)
    print(f"📈 Summary:")
    print(f"   Total courses in CSV: {len(all_courses)}")
    print(f"   Already crawled: {len(existing_codes)}")
    print(f"   Missing: {len(missing_courses)}")
    print("=" * 70)
    
    if missing_courses:
        print(f"\n❌ Missing courses ({len(missing_courses)}):")
        print("-" * 70)
        for i, course in enumerate(missing_courses[:20], 1):  # Show first 20
            course_code = course.get('Course Code', 'N/A')
            course_name = course.get('Course Name_y', course.get('Course Name_x', 'N/A'))
            url = course.get('Link', 'N/A')
            print(f"   {i}. {course_code} - {course_name[:60]}")
            print(f"      URL: {url}")
        
        if len(missing_courses) > 20:
            print(f"\n   ... and {len(missing_courses) - 20} more courses")
        
        # Save missing courses to a file for reference
        missing_file = courses_dir.parent / "missing_courses.txt"
        with open(missing_file, 'w', encoding='utf-8') as f:
            f.write(f"Missing Courses ({len(missing_courses)} total)\n")
            f.write("=" * 70 + "\n\n")
            for course in missing_courses:
                course_code = course.get('Course Code', 'N/A')
                course_name = course.get('Course Name_y', course.get('Course Name_x', 'N/A'))
                url = course.get('Link', 'N/A')
                f.write(f"Course Code: {course_code}\n")
                f.write(f"Course Name: {course_name}\n")
                f.write(f"URL: {url}\n")
                f.write("-" * 70 + "\n")
        
        print(f"\n💾 Missing courses list saved to: {missing_file}")
        print(f"\n💡 To continue crawling, run:")
        print(f"   python3 create_structured_course_json.py --resume")
    else:
        print("\n✅ All courses have been crawled!")


if __name__ == "__main__":
    main()

