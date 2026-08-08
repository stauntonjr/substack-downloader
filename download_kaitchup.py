#!/usr/bin/env python3
"""
Download The Kaitchup archive from RSS feed
"""

import os
import sys
import time
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

def download_post(url, output_dir):
    """Download a single post and save as markdown"""
    print(f"Downloading: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('h1')
        if title:
            title = title.get_text().strip()
        else:
            title = f"post_{int(time.time())}"
        
        # Extract content
        content_div = soup.find('div', class_='post-body') or soup.find('div', attrs={'data-test': 'post-content'})
        if not content_div:
            # Try to find main content area
            content_div = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        
        if content_div:
            # Remove scripts and styles
            for tag in content_div(['script', 'style', 'noscript']):
                tag.decompose()
            
            # Convert to markdown-like text
            text = content_div.get_text('\n', strip=True)
        else:
            text = "Could not extract content"
        
        # Create filename
        timestamp = datetime.now().strftime("%Y-%m-%d")
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:50]
        safe_title = safe_title.replace(' ', '-').lower()
        filename = f"{timestamp}_{safe_title}.md"
        
        # Save to file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(f"Source: {url}\n\n")
            f.write("---\n\n")
            f.write(text)
        
        print(f"  Saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"  Error: {e}")
        return False

def main():
    rss_url = "https://kaitchup.substack.com/feed"
    output_dir = "/home/jrs/substack-downloader/archive/kaitchup.substack.com"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Parse RSS feed
    print(f"Parsing RSS feed: {rss_url}")
    feed = feedparser.parse(rss_url)
    
    if feed.bozo:
        print("Error parsing RSS feed")
        sys.exit(1)
    
    print(f"Found {len(feed.entries)} posts")
    
    # Download posts
    downloaded = 0
    for i, entry in enumerate(feed.entries):
        print(f"[{i+1}/{len(feed.entries)}] {entry.title}")
        
        # Get article URL
        if hasattr(entry, 'link'):
            url = entry.link
        else:
            print(f"  Skipping: no URL")
            continue
        
        if download_post(url, output_dir):
            downloaded += 1
        
        # Be polite with requests
        time.sleep(1)
    
    print(f"\nDownloaded {downloaded} posts to {output_dir}")

if __name__ == "__main__":
    main()
