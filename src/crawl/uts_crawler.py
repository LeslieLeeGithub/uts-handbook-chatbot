#!/usr/bin/env python3
"""
UTS Course Crawler (Single-file)
Combines a flexible Pyppeteer-based WebsiteCrawler and an enhanced UTS course crawler
that clicks "Expand all" buttons to reveal hidden content.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse

from pyppeteer import launch
from pyppeteer.errors import TimeoutError


class WebsiteCrawler:
    """A flexible website crawler using Pyppeteer."""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.page = None
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_browser()
    
    async def start_browser(self):
        try:
            self.browser = await launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            self.page = await self.browser.newPage()
            await self.page.setUserAgent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            await self.page.setViewport({'width': 1920, 'height': 1080})
            self.logger.info("Browser started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            raise
    
    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            self.logger.info("Browser closed")
    
    async def crawl_page(self, url: str, selectors: Dict[str, str] = None) -> Dict[str, Any]:
        if not self.page:
            await self.start_browser()
        try:
            self.logger.info(f"Crawling: {url}")
            await self.page.goto(url, waitUntil='networkidle2', timeout=self.timeout)
            await asyncio.sleep(2)
            page_data = {
                'url': url,
                'title': await self.page.title(),
                'timestamp': datetime.now().isoformat(),
                'domain': urlparse(url).netloc
            }
            if selectors:
                extracted_data = await self._extract_with_selectors(selectors)
                page_data.update(extracted_data)
            else:
                page_data['content'] = await self.page.evaluate('''() => { return document.body.innerText; }''')
            return page_data
        except TimeoutError:
            self.logger.error(f"Timeout while loading {url}")
            return {'url': url, 'error': 'Timeout', 'timestamp': datetime.now().isoformat()}
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {e}")
            return {'url': url, 'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    async def _extract_with_selectors(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        extracted = {}
        for field_name, selector in selectors.items():
            try:
                value = await self.page.evaluate(f'''
                    () => {{
                        const elements = document.querySelectorAll('{selector}');
                        if (elements.length === 0) return null;
                        if (elements.length === 1) {{
                            return elements[0].innerText.trim();
                        }} else {{
                            return Array.from(elements).map(el => el.innerText.trim());
                        }}
                    }}
                ''')
                extracted[field_name] = value
            except Exception as e:
                self.logger.warning(f"Failed to extract {field_name}: {e}")
                extracted[field_name] = None
        return extracted
    
    async def find_links(self, url: str, link_selector: str = 'a[href]') -> List[str]:
        if not self.page:
            await self.start_browser()
        try:
            await self.page.goto(url, waitUntil='networkidle2', timeout=self.timeout)
            links = await self.page.evaluate(f'''
                () => {{
                    const links = Array.from(document.querySelectorAll('{link_selector}'));
                    return links.map(link => {{
                        const href = link.getAttribute('href');
                        if (!href) return null;
                        try {{
                            return new URL(href, window.location.href).href;
                        }} catch {{
                            return null;
                        }}
                    }}).filter(href => href !== null);
                }}
            ''')
            return links
        except Exception as e:
            self.logger.error(f"Error finding links on {url}: {e}")
            return []
    
    def save_to_json(self, data: Any, filename: str):
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Data saved to {output_path}")


async def crawl_uts_course_with_expand(url: str) -> Dict[str, Any]:
    """Crawl a UTS course page and extract ALL content including expanded sections."""
    print(f"🕷️ Crawling UTS course with expand handling: {url}")
    async with WebsiteCrawler(headless=True) as crawler:
        await crawler.page.goto(url, waitUntil='networkidle2', timeout=30000)
        await asyncio.sleep(2)
        print("🔍 Looking for expand/read more buttons...")
        # Find all expand and read more buttons
        expand_buttons = await crawler.page.evaluate('''() => {
            const buttons = Array.from(document.querySelectorAll('button, span, div, a, [role="button"]'));
            return buttons.filter(btn => {
                if (!btn || !btn.textContent) return false;
                const text = btn.textContent.toLowerCase().trim();
                return (text.includes('expand') && text.includes('all')) ||
                       text.includes('read more') ||
                       text.includes('show more') ||
                       text.includes('view more') ||
                       text === 'expand' ||
                       text === 'read more' ||
                       text === 'show more';
            }).map(btn => ({
                text: btn.textContent.trim(),
                tagName: btn.tagName,
                className: btn.className,
                id: btn.id,
                ariaExpanded: btn.getAttribute('aria-expanded')
            }));
        }''')
        print(f"📋 Found {len(expand_buttons)} expand/read more buttons:")
        for i, btn in enumerate(expand_buttons):
            print(f"   {i+1}. {btn['text']} ({btn['tagName']})")
        
        # Click all expand/read more buttons
        for i, btn_info in enumerate(expand_buttons):
            try:
                print(f"🖱️ Clicking button {i+1}: {btn_info['text']}")
                # Escape the button text for JavaScript
                btn_text_escaped = btn_info['text'].replace("'", "\\'").replace('"', '\\"')
                clicked = await crawler.page.evaluate(f'''() => {{
                    const buttons = Array.from(document.querySelectorAll('button, span, div, a, [role="button"]'));
                    const targetBtn = buttons.find(btn => {{
                        if (!btn || !btn.textContent) return false;
                        const text = btn.textContent.toLowerCase().trim();
                        const targetText = '{btn_text_escaped.lower()}';
                        return text === targetText || text.includes(targetText);
                    }});
                    if (targetBtn) {{
                        // Scroll into view first
                        targetBtn.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        // Try clicking
                        try {{
                            targetBtn.click();
                            return true;
                        }} catch (e) {{
                            // If click fails, try dispatchEvent
                            const clickEvent = new MouseEvent('click', {{
                                view: window,
                                bubbles: true,
                                cancelable: true
                            }});
                            targetBtn.dispatchEvent(clickEvent);
                            return true;
                        }}
                    }}
                    return false;
                }}''')
                if clicked:
                    print("   ✅ Successfully clicked")
                    await asyncio.sleep(2)  # Wait longer for content to load
                else:
                    print("   ❌ Failed to click")
            except Exception as e:
                print(f"   ⚠️ Error clicking button: {e}")
        
        # Also try to find and click any "read more" links that might be hidden
        print("🔍 Looking for additional read more links...")
        read_more_clicked = await crawler.page.evaluate('''() => {
            let clickedCount = 0;
            const readMoreLinks = Array.from(document.querySelectorAll('a, button, span, div'));
            readMoreLinks.forEach(link => {
                if (link && link.textContent) {
                    const text = link.textContent.toLowerCase().trim();
                    if (text.includes('read more') || text.includes('show more') || text.includes('view more')) {
                        try {
                            link.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            link.click();
                            clickedCount++;
                        } catch (e) {
                            console.error('Error clicking read more:', e);
                        }
                    }
                }
            });
            return clickedCount;
        }''')
        if read_more_clicked > 0:
            print(f"   ✅ Clicked {read_more_clicked} additional read more links")
            await asyncio.sleep(2)
        await asyncio.sleep(2)
        print("📖 Extracting expanded content...")
        try:
            course_data = await crawler.page.evaluate('''() => {
                try {
                    const data = {
                        course_title: '',
                        course_code: '',
                        credit_points: '',
                        sections: {},
                        all_text_content: '',
                        links: [],
                        expanded_content: {},
                        course_details: {}
                    };
                    
                    // Extract course title and code
                    try {
                        const titleElement = document.querySelector('h1');
                        if (titleElement && titleElement.textContent) {
                            const titleText = titleElement.textContent.trim();
                            data.course_title = titleText;
                            const codeMatch = titleText.match(/^[A-Z]\\d{5}/);
                            if (codeMatch) {
                                data.course_code = codeMatch[0];
                            }
                        }
                    } catch (e) {
                        console.error('Error extracting title:', e);
                    }
                    
                    // Extract credit points
                    try {
                        const creditElement = document.querySelector('h2');
                        if (creditElement && creditElement.textContent) {
                            const creditText = creditElement.textContent.trim();
                            const creditMatch = creditText.match(/(\\d+)\\s*Credit\\s*points?/i);
                            if (creditMatch) {
                                data.credit_points = creditMatch[1];
                            }
                        }
                    } catch (e) {
                        console.error('Error extracting credit points:', e);
                    }
                    
                    // Extract sections from headings
                    try {
                        const headings = document.querySelectorAll('h1, h2, h3, h4, h5');
                        headings.forEach(heading => {
                            try {
                                if (heading && heading.textContent) {
                                    const headingText = heading.textContent.trim();
                                    if (headingText) {
                                        let content = '';
                                        try {
                                            const parentSection = heading.closest('section, div, .section, .content');
                                            if (parentSection && parentSection.textContent) {
                                                content = parentSection.textContent.trim();
                                            } else {
                                                let nextElement = heading.nextElementSibling;
                                                for (let i = 0; i < 5 && nextElement; i++) {
                                                    if (nextElement && nextElement.textContent && 
                                                        (nextElement.tagName === 'P' || nextElement.tagName === 'DIV' || 
                                                         nextElement.tagName === 'UL' || nextElement.tagName === 'OL')) {
                                                        content += nextElement.textContent.trim() + ' ';
                                                    }
                                                    nextElement = nextElement ? nextElement.nextElementSibling : null;
                                                }
                                            }
                                        } catch (e) {
                                            console.error('Error extracting section content:', e);
                                        }
                                        data.sections[headingText] = content.trim();
                                    }
                                }
                            } catch (e) {
                                console.error('Error processing heading:', e);
                            }
                        });
                    } catch (e) {
                        console.error('Error extracting headings:', e);
                    }
                    
                    // Extract detail elements
                    try {
                        const detailElements = document.querySelectorAll('[class*="detail"], [class*="info"], [class*="requirement"]');
                        detailElements.forEach(element => {
                            try {
                                if (element && element.textContent) {
                                    const text = element.textContent.trim();
                                    if (text && text.length > 10) {
                                        const className = element.className || 'unknown';
                                        data.course_details[className] = text;
                                    }
                                }
                            } catch (e) {
                                console.error('Error processing detail element:', e);
                            }
                        });
                    } catch (e) {
                        console.error('Error extracting detail elements:', e);
                    }
                    
                    // Extract all text content
                    try {
                        if (document.body && document.body.innerText) {
                            data.all_text_content = document.body.innerText;
                        }
                    } catch (e) {
                        console.error('Error extracting all text content:', e);
                    }
                    
                    // Extract links
                    try {
                        const links = document.querySelectorAll('a[href]');
                        data.links = Array.from(links).map(link => {
                            try {
                                if (link && link.href) {
                                    return {
                                        text: link.textContent ? link.textContent.trim() : '',
                                        href: link.href,
                                        title: link.title || ''
                                    };
                                }
                                return null;
                            } catch (e) {
                                return null;
                            }
                        }).filter(link => link && link.text && link.href);
                    } catch (e) {
                        console.error('Error extracting links:', e);
                    }
                    
                    // Extract expanded sections
                    try {
                        const expandedSections = document.querySelectorAll('.expanded, [aria-expanded="true"], .show, .active');
                        expandedSections.forEach(section => {
                            try {
                                if (section && section.textContent) {
                                    const sectionText = section.textContent.trim();
                                    if (sectionText) {
                                        const className = section.className || 'expanded';
                                        data.expanded_content[className] = sectionText;
                                    }
                                }
                            } catch (e) {
                                console.error('Error processing expanded section:', e);
                            }
                        });
                    } catch (e) {
                        console.error('Error extracting expanded sections:', e);
                    }
                    
                    return data;
                } catch (error) {
                    console.error('Error in course data extraction:', error);
                    return {
                        error: error.toString(),
                        course_title: '',
                        course_code: '',
                        credit_points: '',
                        sections: {},
                        all_text_content: '',
                        links: [],
                        expanded_content: {},
                        course_details: {}
                    };
                }
            }''')
        except Exception as e:
            print(f"   ❌ Error evaluating page content: {e}")
            # Return empty data structure on error
            course_data = {
                'error': str(e),
                'course_title': '',
                'course_code': '',
                'credit_points': '',
                'sections': {},
                'all_text_content': '',
                'links': [],
                'expanded_content': {},
                'course_details': {}
            }
        basic_data = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'title': await crawler.page.title(),
            'domain': crawler.page.url.split('/')[2] if '/' in crawler.page.url else ''
        }
        result = {
            **basic_data,
            'course_info': course_data,
            'expand_buttons_found': len(expand_buttons),
            'expand_buttons_info': expand_buttons
        }
        return result


async def main():
    """Main function to crawl the UTS course page with expand handling."""
    import sys
    
    # Get URL from command line argument or use default
    if len(sys.argv) > 1:
        course_url = sys.argv[1]
    else:
        # Default to the user's requested URL
        course_url = "https://coursehandbook.uts.edu.au/course/2026/c10162"
    
    print("🚀 Starting Enhanced UTS Course Crawler")
    print(f"📚 Target: {course_url}")
    print("-" * 60)
    try:
        course_data = await crawl_uts_course_with_expand(course_url)
        
        # Generate output filename
        course_code = course_data['course_info'].get('course_code', 'unknown')
        if course_code == 'unknown' or not course_code:
            # Try to extract from URL
            url_parts = course_url.split('/')
            if len(url_parts) > 0:
                course_code = url_parts[-1]  # Get last part of URL
        
        output_file = f"uts_course_expanded_{course_code}.json"
        
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(course_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Successfully crawled course data with expanded content!")
        print(f"💾 Saved to: {output_file}")
        print("\n📋 Course Information:")
        print(f"   Title: {course_data['course_info'].get('course_title', 'N/A')}")
        print(f"   Code: {course_data['course_info'].get('course_code', 'N/A')}")
        print(f"   Credit Points: {course_data['course_info'].get('credit_points', 'N/A')}")
        print(f"   Sections Found: {len(course_data['course_info'].get('sections', {}))}")
        print(f"   Links Found: {len(course_data['course_info'].get('links', []))}")
        print(f"   Expand Buttons Found: {course_data.get('expand_buttons_found', 0)}")
        print(f"   Expanded Content Sections: {len(course_data['course_info'].get('expanded_content', {}))}")
        
        sections = course_data['course_info'].get('sections', {})
        if sections:
            print("\n📖 Key Sections (including expanded content):")
            for section_name, content in list(sections.items())[:8]:
                preview = content[:150] + "..." if len(content) > 150 else content
                print(f"   • {section_name}: {preview}")
        
        expanded = course_data['course_info'].get('expanded_content', {})
        if expanded:
            print("\n🔓 Expanded Content Found:")
            for key, content in expanded.items():
                preview = content[:100] + "..." if len(content) > 100 else content
                print(f"   • {key}: {preview}")
        
        print(f"\n🎉 Enhanced crawling completed successfully!")
        print(f"📊 Total content size: {len(course_data['course_info'].get('all_text_content', ''))} characters")
    except Exception as e:
        print(f"❌ Error crawling course: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())


