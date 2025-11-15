#!/usr/bin/env python3
"""
Simple script to crawl a UTS course page and save to JSON.
Usage: python crawl_course.py [URL]
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "crawl"))

from uts_crawler import crawl_uts_course_with_expand


async def main():
    """Crawl a UTS course page and save to JSON."""
    # Get URL from command line or use default
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://coursehandbook.uts.edu.au/course/2026/c10162"
    
    print(f"🕷️  Crawling UTS course: {url}")
    print("=" * 70)
    
    try:
        # Crawl the course page
        result = await crawl_uts_course_with_expand(url)
        
        # Generate output filename
        course_code = result['course_info'].get('course_code', 'unknown')
        if course_code == 'unknown' or not course_code:
            # Extract from URL
            url_parts = url.split('/')
            if len(url_parts) > 0:
                course_code = url_parts[-1]
        
        output_file = f"uts_course_{course_code}.json"
        
        # Save to JSON
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 70)
        print(f"✅ Successfully crawled and saved to: {output_file}")
        print("\n📊 Summary:")
        print(f"   Course Title: {result['course_info'].get('course_title', 'N/A')}")
        print(f"   Course Code: {result['course_info'].get('course_code', 'N/A')}")
        print(f"   Credit Points: {result['course_info'].get('credit_points', 'N/A')}")
        print(f"   Sections: {len(result['course_info'].get('sections', {}))}")
        print(f"   Links: {len(result['course_info'].get('links', []))}")
        print(f"   Expand/Read More Buttons Found: {result.get('expand_buttons_found', 0)}")
        print(f"   Expanded Content Sections: {len(result['course_info'].get('expanded_content', {}))}")
        print(f"   Total Content Size: {len(result['course_info'].get('all_text_content', ''))} characters")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

