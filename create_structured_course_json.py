#!/usr/bin/env python3
"""
Create Structured Course JSON
Processes crawled course data and CSV data into standardized format.
"""

import asyncio
import json
import csv
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "crawl"))
from uts_crawler import crawl_uts_course_with_expand


def extract_links_in_text(text: str, links: List[Dict]) -> str:
    """Replace link text with markdown-style links [text](url)."""
    if not text or not links:
        return text
    
    result = text
    # Sort by length (longest first) to avoid partial matches
    sorted_links = sorted(links, key=lambda x: len(x.get('text', '')), reverse=True)
    
    for link in sorted_links:
        link_text = link.get('text', '').strip()
        link_url = link.get('href', '')
        if link_text and link_url and len(link_text) > 3:
            # Only replace if it's a meaningful link (not just "C10026" but "Bachelor of Business (C10026)")
            if link_text in result and link_url.startswith('http'):
                # Use markdown link format
                result = result.replace(link_text, f"[{link_text}]({link_url})", 1)
    
    return result


def parse_course_info(crawled_data: Dict) -> Dict[str, Any]:
    """Parse crawled course data into structured format."""
    course_info = crawled_data.get('course_info', {})
    all_text = course_info.get('all_text_content', '')
    sections = course_info.get('sections', {})
    links = course_info.get('links', [])
    
    parsed = {
        'course_code': '',
        'course_name': '',
        'credit_points': '',
        'overview': '',
        'awards': [],
        'faculty': [],
        'study_level': '',
        'location': [],
        'duration_fulltime': '',
        'duration_parttime': '',
        'uac_codes': [],
        'cricos_code': '',
        'language': '',
        'availabilities': [],
        'professional_recognition': None,
        'learning_outcomes': [],
        'structure_notes': '',
        'structure': {},
        'inherent_requirements': None,
        'study_plans': [],
        'notes': None
    }
    
    # Extract course code and name
    title_match = re.search(r'([A-Z]\d{5})\s*-\s*(.+?)(?:\n|192|Credit|page)', all_text)
    if title_match:
        parsed['course_code'] = title_match.group(1)
        course_name = title_match.group(2).strip()
        # Remove "page" suffix if present
        course_name = re.sub(r'\s+page\s*$', '', course_name, flags=re.IGNORECASE)
        parsed['course_name'] = course_name
    
    # Extract credit points
    cp_match = re.search(r'(\d+)\s*Credit\s*points?', all_text, re.IGNORECASE)
    if cp_match:
        parsed['credit_points'] = f"{cp_match.group(1)} Credit points"
    
    # Extract Overview
    overview_section = sections.get('Overview', '')
    if overview_section:
        # Clean up overview text
        overview_text = overview_section.replace('Overview', '').strip()
        # Remove "Read More" prompts
        overview_text = re.sub(r'For more content click the Read More button below', '', overview_text)
        overview_text = re.sub(r'Read (More|Less).*?about Overview', '', overview_text, flags=re.IGNORECASE)
        parsed['overview'] = overview_text.strip()
    
    # Extract Awards
    award_text = sections.get('Award(s)', '')
    if award_text:
        # Remove "Award(s)" prefix
        award_text = re.sub(r'Award\(s\)', '', award_text, flags=re.IGNORECASE)
        # Split by common patterns
        awards = [a.strip() for a in re.split(r'\s{2,}|\n', award_text) if a.strip() and len(a.strip()) > 5]
        parsed['awards'] = awards
    
    # Extract Faculty
    faculty_text = sections.get('Faculty', '')
    if faculty_text:
        faculty_text = re.sub(r'Faculty', '', faculty_text, flags=re.IGNORECASE).strip()
        # Split by capital letters (e.g., "ScienceBusiness" -> ["Science", "Business"])
        # Or split by newlines/whitespace if already separated
        if '\n' in faculty_text or ' ' in faculty_text:
            parsed['faculty'] = [f.strip() for f in re.split(r'\s+|\n+', faculty_text) if f.strip()]
        else:
            # Split camelCase or concatenated words (e.g., "ScienceBusiness")
            # Look for capital letters followed by lowercase letters
            faculty_list = re.findall(r'[A-Z][a-z]+', faculty_text)
            if faculty_list:
                parsed['faculty'] = faculty_list
            else:
                parsed['faculty'] = [faculty_text] if faculty_text else []
    
    # Extract Study level
    study_level_text = sections.get('Study level', '')
    if study_level_text:
        study_level_text = re.sub(r'Study level', '', study_level_text, flags=re.IGNORECASE)
        parsed['study_level'] = study_level_text.strip()
    
    # Extract Location
    location_text = sections.get('Location', '')
    if location_text:
        location_text = re.sub(r'Location', '', location_text, flags=re.IGNORECASE).strip()
        # Location might be "City campus" as one string, or multiple locations
        if '\n' in location_text or ',' in location_text:
            parsed['location'] = [l.strip() for l in re.split(r'[\n,]+', location_text) if l.strip()]
        else:
            parsed['location'] = [location_text] if location_text else []
    
    # Extract Duration
    duration_text = sections.get('Duration', '')
    if duration_text:
        duration_match = re.search(r'(\d+)\s*Year\(s\)', duration_text)
        if duration_match:
            parsed['duration_fulltime'] = f"{duration_match.group(1)} Year(s)"
    
    duration_pt_text = sections.get('Duration - Part time', '')
    if duration_pt_text:
        duration_pt_match = re.search(r'(\d+)\s*Year\(s\)', duration_pt_text)
        if duration_pt_match:
            parsed['duration_parttime'] = f"{duration_pt_match.group(1)} Year(s)"
    
    # Extract UAC codes
    uac_text = sections.get('UAC code(s)', '')
    if uac_text:
        uac_text = re.sub(r'UAC code\(s\)', '', uac_text, flags=re.IGNORECASE)
        parsed['uac_codes'] = [u.strip() for u in uac_text.split('|') if u.strip()]
    
    # Extract CRICOS code
    cricos_text = sections.get('CRICOS code', '')
    if cricos_text:
        # Extract the actual code (e.g., "032310K" from "CRICOS code 032310K")
        cricos_match = re.search(r'CRICOS code\s+([A-Z0-9]{6,10})', cricos_text, re.IGNORECASE)
        if cricos_match:
            parsed['cricos_code'] = cricos_match.group(1)
        else:
            # Fallback: find any alphanumeric code
            cricos_match = re.search(r'([A-Z0-9]{6,10})', cricos_text)
            if cricos_match and cricos_match.group(1) != 'CRICOS':
                parsed['cricos_code'] = cricos_match.group(1)
    
    # Extract Language
    lang_text = sections.get('Language of instruction', '')
    if lang_text:
        lang_text = re.sub(r'Language of instruction', '', lang_text, flags=re.IGNORECASE)
        parsed['language'] = lang_text.strip()
    
    # Extract Availabilities
    avail_text = all_text
    # Find availability sections
    avail_pattern = r'City campus-([A-Z][a-z]+ Session)[\s\S]{0,500}?Attendance mode([^\n]+)[\s\S]{0,500}?Attendance type([^\n]+)[\s\S]{0,500}?Location([^\n]+)[\s\S]{0,500}?Session([^\n]+)[\s\S]{0,500}?Student type([^\n]+)'
    avail_matches = re.finditer(avail_pattern, avail_text)
    for match in avail_matches:
        availability = {
            'session': f"City campus-{match.group(1)}",
            'attendance_mode': match.group(2).strip(),
            'attendance_type': match.group(3).strip(),
            'location': match.group(4).strip(),
            'student_type': match.group(6).strip()
        }
        parsed['availabilities'].append(availability)
    
    # Extract Professional Recognition
    prof_rec_text = sections.get('Professional recognition', '')
    if prof_rec_text:
        prof_rec_text = re.sub(r'Professional recognition', '', prof_rec_text, flags=re.IGNORECASE)
        prof_rec_text = re.sub(r'Read (More|Less).*?', '', prof_rec_text, flags=re.IGNORECASE)
        if prof_rec_text.strip() and len(prof_rec_text.strip()) > 20:
            parsed['professional_recognition'] = prof_rec_text.strip()
    
    # Extract Learning Outcomes
    outcomes_text = all_text
    # Find numbered learning outcomes
    outcomes_pattern = r'(\d+)\.\s*([^\d]{20,500}?)(?=\d+\.|$)'
    outcomes_matches = re.finditer(outcomes_pattern, outcomes_text)
    for match in outcomes_matches:
        outcome_text = match.group(2).strip()
        # Clean up
        outcome_text = re.sub(r'keyboard_arrow_down', '', outcome_text)
        outcome_text = re.sub(r'\s+', ' ', outcome_text)
        if len(outcome_text) > 10:
            parsed['learning_outcomes'].append({
                'number': int(match.group(1)),
                'text': outcome_text
            })
    
    # Extract Structure Notes
    structure_notes_text = sections.get('Structure Notes', '')
    if structure_notes_text:
        structure_notes_text = re.sub(r'Structure Notes', '', structure_notes_text, flags=re.IGNORECASE)
        structure_notes_text = re.sub(r'Read (More|Less).*?about Structure Notes', '', structure_notes_text, flags=re.IGNORECASE)
        structure_notes_text = re.sub(r'For more content click the Read More button below', '', structure_notes_text)
        if structure_notes_text.strip() and len(structure_notes_text.strip()) > 20:
            parsed['structure_notes'] = structure_notes_text.strip()
    
    # Extract Structure - this is complex, will need to parse from all_text
    # For now, we'll extract basic structure info
    
    # Extract Inherent Requirements
    inherent_text = sections.get('Inherent requirements', '')
    if inherent_text:
        inherent_text = re.sub(r'Inherent requirements', '', inherent_text, flags=re.IGNORECASE)
        inherent_text = re.sub(r'inherent requirements directory', '', inherent_text, flags=re.IGNORECASE)
        inherent_text = inherent_text.strip()
        if inherent_text and len(inherent_text) > 20 and inherent_text.lower() != 'none':
            parsed['inherent_requirements'] = inherent_text
    
    # Extract Study Plans
    study_plans_text = all_text
    # Find study plan links
    for link in links:
        link_text = link.get('text', '')
        link_href = link.get('href', '')
        # Check if it's a study plan (contains comma and "commencing")
        if link_text and ',' in link_text and 'commencing' in link_text.lower() and 'studyplan' in link_href:
            parsed['study_plans'].append({
                'name': link_text,
                'url': link_href
            })
    
    # Extract Notes (if exists)
    notes_text = sections.get('Notes', '')
    if notes_text:
        notes_text = re.sub(r'Notes', '', notes_text, flags=re.IGNORECASE)
        notes_text = notes_text.strip()
        if notes_text and len(notes_text) > 20 and notes_text.lower() != 'none':
            parsed['notes'] = notes_text
    
    # Add links to text fields
    if parsed['overview']:
        parsed['overview'] = extract_links_in_text(parsed['overview'], links)
    if parsed['professional_recognition']:
        parsed['professional_recognition'] = extract_links_in_text(parsed['professional_recognition'], links)
    if parsed['structure_notes']:
        parsed['structure_notes'] = extract_links_in_text(parsed['structure_notes'], links)
    if parsed['inherent_requirements']:
        parsed['inherent_requirements'] = extract_links_in_text(parsed['inherent_requirements'], links)
    if parsed['notes']:
        parsed['notes'] = extract_links_in_text(parsed['notes'], links)
    
    return parsed


def read_csv_row(csv_path: str, course_code: str) -> Optional[Dict[str, Any]]:
    """Read a specific row from CSV by course code."""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Course Code', '').strip() == course_code or \
               row.get('All Course Codes', '').strip() == course_code:
                return row
    return None


def combine_data(web_data: Dict, csv_data: Dict) -> Dict[str, Any]:
    """Combine website data with CSV data into standardized format."""
    combined = {
        'course_code': web_data.get('course_code', '') or csv_data.get('Course Code', '').strip(),
        'course_name': web_data.get('course_name', '') or csv_data.get('Course Name_x', '').strip() or csv_data.get('Course Name_y', '').strip(),
        'credit_points': web_data.get('credit_points', ''),
        'cricos_code': web_data.get('cricos_code', '') or csv_data.get('CRICOS Code', '').strip(),
        'overview': web_data.get('overview', '') or csv_data.get('Overview', '').strip(),
        'awards': web_data.get('awards', []),
        'faculty': web_data.get('faculty', []),
        'study_level': web_data.get('study_level', ''),
        'location': web_data.get('location', []),
        'duration_fulltime': web_data.get('duration_fulltime', ''),
        'duration_parttime': web_data.get('duration_parttime', ''),
        'duration_sessions': csv_data.get('Course Duration (Session)', '').strip(),
        'course_fee': csv_data.get('Course Fee (A$/Session)', '').strip(),
        'course_intake': csv_data.get('Course Intake', '').strip(),
        'uac_codes': web_data.get('uac_codes', []),
        'language': web_data.get('language', ''),
        'availabilities': web_data.get('availabilities', []),
        'professional_recognition': web_data.get('professional_recognition') or csv_data.get('Professional recognition', '').strip() or None,
        'learning_outcomes': web_data.get('learning_outcomes', []),
        'structure_notes': web_data.get('structure_notes', ''),
        'structure': web_data.get('structure', {}),
        'inherent_requirements': web_data.get('inherent_requirements') or csv_data.get('Inherent (essential) requirements', '').strip() or None,
        'study_plans': web_data.get('study_plans', []),
        'notes': web_data.get('notes') or csv_data.get('Notes', '').strip() or None,
        'admission_requirements': csv_data.get('Admission requirements', '').strip() or None,
        'career_options': csv_data.get('Career options', '').strip() or None,
        'course_structure': csv_data.get('Course structure', '').strip() or None,
        'metadata': {
            'source_url': csv_data.get('Link', '').strip(),
            'crawled_at': datetime.now().isoformat(),
            'csv_source': 'merged_Admission_Courses.csv'
        }
    }
    
    # Clean up empty values
    for key, value in combined.items():
        if isinstance(value, list) and len(value) == 0:
            combined[key] = []
        elif isinstance(value, str) and value.strip() == '':
            combined[key] = None
        elif value == '':
            combined[key] = None
    
    return combined


def sanitize_filename(name: str) -> str:
    """Sanitize filename by removing invalid characters."""
    # Remove invalid filename characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    return name


async def process_single_course(csv_data: Dict, courses_dir: Path, index: int, total: int) -> bool:
    """Process a single course from CSV data."""
    course_code = csv_data.get('Course Code', '').strip()
    course_name_x = csv_data.get('Course Name_x', '').strip()
    course_name_y = csv_data.get('Course Name_y', '').strip()
    
    print(f"\n[{index}/{total}] Processing: {course_code} - {course_name_y or course_name_x}")
    print("-" * 70)
    
    # Get URL from CSV
    url = csv_data.get('Link', '').strip()
    if not url:
        print(f"⚠️  No URL found for course {course_code}, skipping...")
        return False
    
    try:
        # Crawl website
        print(f"🕷️  Crawling: {url}")
        crawled_data = await crawl_uts_course_with_expand(url)
        
        # Parse into structured format
        print("📝 Parsing into structured format...")
        web_data = parse_course_info(crawled_data)
        
        # Combine data
        combined_data = combine_data(web_data, csv_data)
        
        # Generate filename: coursenamey_coursenamex_coursecode.json
        name_parts = []
        if course_name_y:
            name_parts.append(sanitize_filename(course_name_y))
        if course_name_x and course_name_x != course_name_y:
            name_parts.append(sanitize_filename(course_name_x))
        if course_code:
            name_parts.append(course_code)
        
        if not name_parts:
            filename = f"course_{index}.json"
        else:
            filename = "_".join(name_parts) + ".json"
        
        output_file = courses_dir / filename
        
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Saved: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error processing {course_code}: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_existing_course_codes(courses_dir: Path) -> set:
    """Get set of course codes from existing JSON files."""
    existing_codes = set()
    if not courses_dir.exists():
        return existing_codes
    
    import json
    for json_file in courses_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                course_code = data.get('course_code', '').strip()
                if course_code:
                    existing_codes.add(course_code)
        except Exception:
            pass  # Skip files that can't be read
    
    return existing_codes


async def main():
    """Main function to process all courses from CSV."""
    import sys
    
    # Check for --resume flag
    resume = '--resume' in sys.argv or '-r' in sys.argv
    
    csv_path = Path(__file__).parent / "data" / "original_course_list_excel" / "merged_Admission_Courses.csv"
    courses_dir = Path(__file__).parent / "data" / "courses"
    
    # Create courses directory
    courses_dir.mkdir(exist_ok=True)
    
    print("📚 Processing courses from CSV")
    if resume:
        print("🔄 Resume mode: Skipping already crawled courses")
    print("=" * 70)
    
    # Get existing course codes if resuming
    existing_codes = set()
    if resume:
        print("📂 Checking existing course files...")
        existing_codes = get_existing_course_codes(courses_dir)
        print(f"✅ Found {len(existing_codes)} already crawled courses")
    
    # Read all CSV rows
    print("📖 Reading CSV data...")
    all_courses = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only process rows with valid course code and URL
            course_code = row.get('Course Code', '').strip()
            url = row.get('Link', '').strip()
            if course_code and url:
                # Skip if already crawled (in resume mode)
                if resume and course_code in existing_codes:
                    continue
                all_courses.append(row)
    
    total = len(all_courses)
    if resume:
        print(f"📊 Found {total} courses remaining to process")
    else:
        print(f"📊 Found {total} courses to process")
    
    if total == 0:
        if resume:
            print("✅ All courses have already been crawled!")
        else:
            print("❌ No courses found in CSV")
        return
    
    # Process each course
    success_count = 0
    failed_count = 0
    
    for index, csv_data in enumerate(all_courses, 1):
        success = await process_single_course(csv_data, courses_dir, index, total)
        if success:
            success_count += 1
        else:
            failed_count += 1
        
        # Add a small delay between requests to be respectful
        if index < total:
            await asyncio.sleep(1)
    
    print("\n" + "=" * 70)
    print(f"✅ Processing complete!")
    print(f"   Success: {success_count}/{total}")
    print(f"   Failed: {failed_count}/{total}")
    print(f"   Output directory: {courses_dir}")


if __name__ == "__main__":
    asyncio.run(main())

