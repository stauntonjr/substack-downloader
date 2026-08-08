#!/usr/bin/env python3
"""
Download The Kaitchup archive using the archive page (more posts than RSS)
"""

import os
import sys
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from pathlib import Path

def download_post(url, output_dir):
    """Download a single post and save as markdown"""
    print(f"  Downloading: {url}")
    
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
            content_div = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        
        if content_div:
            for tag in content_div(['script', 'style', 'noscript']):
                tag.decompose()
            text = content_div.get_text('\n', strip=True)
        else:
            text = "Could not extract content"
        
        # Create filename with title
        timestamp = datetime.now().strftime("%Y-%m-%d")
        # Use URL-based title for uniqueness
        url_part = url.split('/')[-1].split('?')[0]
        # Remove common suffixes
        for suffix in ['-ai-on-a-budget', 'the-kaitchup-', 'the-kaitchup']:
            if url_part.endswith(suffix):
                url_part = url_part.replace(suffix, '').rstrip('-')
        # Clean up the title
        safe_title = url_part.replace('--', '-').replace('_', '-')
        filename = f"{timestamp}_{safe_title}.md"
        
        # Save to file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(f"Source: {url}\n\n")
            f.write("---\n\n")
            f.write(text)
        
        print(f"    Saved: {filename}")
        return True
        
    except Exception as e:
        print(f"    Error: {e}")
        return False

def get_archive_posts(archive_url):
    """Get all post URLs from the archive page"""
    print(f"Parsing archive: {archive_url}")
    response = requests.get(archive_url, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    posts = []
    
    # Find all post links
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'substack.com/p/' in href and href.startswith('https'):
            # Clean up the URL
            url = href.split('?')[0]  # Remove query params
            if url not in posts:
                posts.append(url)
    
    return posts

def main():
    archive_url = "https://kaitchup.substack.com/archive"
    output_dir = "/home/jrs/substack-downloader/archive/kaitchup.substack.com"
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Get posts from archive
    posts = get_archive_posts(archive_url)
    print(f"Found {len(posts)} unique posts")
    
    # Download posts
    downloaded = 0
    skipped = 0
    
    for i, url in enumerate(posts):
        # Check if already downloaded
        safe_title = url.split('/')[-1].split('?')[0]
        existing_files = list(Path(output_dir).glob(f"*{safe_title}*.md"))
        if existing_files:
            print(f"[{i+1}/{len(posts)}] Skipping (already downloaded): {safe_title}")
            skipped += 1
            continue
            
        print(f"[{i+1}/{len(posts)}] {url}")
        if download_post(url, output_dir):
            downloaded += 1
        
        # Be polite with requests
        time.sleep(1)
    
    print(f"\nDownloaded {downloaded} posts, skipped {skipped} existing")
    print(f"All files in: {output_dir}")

if __name__ == "__main__":
    main()
