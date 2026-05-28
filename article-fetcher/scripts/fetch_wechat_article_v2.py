#!/usr/bin/env python3
"""
Fetch WeChat article content using Playwright.
Saves article as PDF, HTML, or screenshot with title-based filenames.
"""

import sys
import argparse
from playwright.sync_api import sync_playwright
import time
import os
import re


def sanitize_filename(title):
    """Convert title to safe filename."""
    # Remove special characters
    safe = re.sub(r'[\\/*?:"<>|]', '', title)
    safe = re.sub(r'\s+', '_', safe)
    # Keep only alphanumeric and underscore
    safe = re.sub(r'[^\w]', '', safe)
    return safe[:50]  # Limit to 50 chars


def fetch_article(url, output_dir, wait_time=5):
    """
    Fetch a WeChat article and save with title-based filenames.
    
    Args:
        url: WeChat article URL
        output_dir: Output directory (should be skill's references folder)
        wait_time: Seconds to wait for page load
    
    Returns:
        dict: Contains title, content, and output paths
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            device_scale_factor=2,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            # Navigate to article
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
            except:
                page.goto(url, wait_until='load', timeout=30000)
            
            # Wait for content
            try:
                page.wait_for_selector('#js_content', timeout=20000)
            except:
                pass
            
            time.sleep(wait_time)
            
            # Get title
            title = page.title()
            safe_title = sanitize_filename(title)
            
            # Create output paths based on title
            pdf_path = os.path.join(output_dir, f"{safe_title}.pdf")
            html_path = os.path.join(output_dir, f"{safe_title}.html")
            screenshot_path = os.path.join(output_dir, f"{safe_title}.png")
            
            # Extract content
            try:
                content = page.inner_text('#js_content')
            except:
                content = "Content extraction failed"
            
            # Save as PDF
            page.pdf(
                path=pdf_path,
                format='A4',
                print_background=True,
                margin={'top': '20px', 'right': '20px', 'bottom': '20px', 'left': '20px'}
            )
            
            # Save as HTML
            html_content = page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Save screenshot
            page.screenshot(path=screenshot_path, full_page=True)
            
            context.close()
            browser.close()
            
            return {
                'title': title,
                'safe_title': safe_title,
                'content': content,
                'pdf_path': pdf_path,
                'html_path': html_path,
                'screenshot_path': screenshot_path,
                'success': True
            }
            
        except Exception as e:
            context.close()
            browser.close()
            return {
                'title': '',
                'safe_title': '',
                'content': '',
                'success': False,
                'error': str(e)
            }


def main():
    parser = argparse.ArgumentParser(description='Fetch WeChat article with title-based filenames')
    parser.add_argument('url', help='WeChat article URL')
    parser.add_argument('-o', '--output-dir', default='.', help='Output directory (use skill references folder)')
    parser.add_argument('-w', '--wait', type=int, default=5, help='Wait time in seconds')
    args = parser.parse_args()
    
    # Create output directory if not exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    result = fetch_article(args.url, args.output_dir, args.wait)
    
    if result['success']:
        print(f"✓ Title: {result['title']}")
        print(f"✓ Safe filename: {result['safe_title']}")
        print(f"\n✓ Content preview (first 1000 chars):\n{result['content'][:1000]}...")
        print(f"\n✓ PDF saved to: {result['pdf_path']}")
        print(f"✓ HTML saved to: {result['html_path']}")
        print(f"✓ Screenshot saved to: {result['screenshot_path']}")
    else:
        print(f"✗ Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
