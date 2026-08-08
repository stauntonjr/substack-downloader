#!/usr/bin/env python3
"""
Download The Kaitchup archive - comprehensive version
Sources: RSS feed, archive page, tutorials, notebooks

Note: This is the free-only method (~29 posts). For the full archive (459 posts),
use v4 with API pagination: python download_kaitchup_v4.py
"""

import os
import sys
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from pathlib import Path
import feedparser

def sanitize_filename(title):
    """Create safe filename from title or URL"""
    # Extract part from URL
    if isinstance(title, str) and '/' in title:
        safe = title.split('/')[-1].split('?')[0]
    else:
        safe = str(title).lower().replace(' ', '-').replace('?', '').replace('/', '-')
    # Remove common suffixes
    for suffix in ['-ai-on-a-budget', 'the-kaitchup-', 'the-kaitchup', '-comments']:
        if safe.endswith(suffix):
            safe = safe[:-len(suffix)]
    # Clean up
    safe = safe.replace('--', '-').replace('_', '-')
    # Keep only alphanumeric and hyphens
    safe = ''.join(c if c.isalnum() or c == '-' else '' for c in safe)
    return safe.lower()

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
        
        # Create filename
        timestamp = datetime.now().strftime("%Y-%m-%d")
        safe_title = sanitize_filename(url)
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

def get_rss_posts(feed_url):
    """Get post URLs from RSS feed"""
    print(f"Parsing RSS feed: {feed_url}")
    feed = feedparser.parse(feed_url)
    
    posts = []
    for entry in feed.entries:
        if hasattr(entry, 'link'):
            posts.append(entry.link)
    
    return posts

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
            url = href.split('?')[0]
            if url not in posts:
                posts.append(url)
    
    return posts

def get_tutorials_posts(base_url):
    """Get post URLs from tutorials section"""
    url = f"{base_url}/t/tutorials"
    print(f"Parsing tutorials: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    posts = []
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'substack.com/p/' in href and href.startswith('https'):
            url = href.split('?')[0]
            if url not in posts:
                posts.append(url)
    
    return posts

def get_notebooks_posts(base_url):
    """Get post URLs from notebooks section"""
    url = f"{base_url}/p/notebooks"
    print(f"Parsing notebooks: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    posts = []
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'substack.com/p/' in href and href.startswith('https'):
            url = href.split('?')[0]
            if url not in posts:
                posts.append(url)
    
    return posts

def already_downloaded(url, output_dir):
    """Check if post was already downloaded"""
    safe_title = sanitize_filename(url)
    existing = list(Path(output_dir).glob(f"*{safe_title}*.md"))
    return len(existing) > 0

def main():
    base_url = "https://kaitchup.substack.com"
    rss_url = f"{base_url}/feed"
    archive_url = f"{base_url}/archive"
    output_dir = "/home/jrs/substack-downloader/archive/kaitchup.substack.com"
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Collect all posts from multiple sources
    all_posts = set()
    
    # RSS feed
    rss_posts = get_rss_posts(rss_url)
    print(f"RSS feed: {len(rss_posts)} posts")
    all_posts.update(rss_posts)
    
    # Archive page
    archive_posts = get_archive_posts(archive_url)
    print(f"Archive page: {len(archive_posts)} posts")
    all_posts.update(archive_posts)
    
    # Tutorials
    tutorial_posts = get_tutorials_posts(base_url)
    print(f"Tutorials: {len(tutorial_posts)} posts")
    all_posts.update(tutorial_posts)
    
    # Notebooks
    notebook_posts = get_notebooks_posts(base_url)
    print(f"Notebooks: {len(notebook_posts)} posts")
    all_posts.update(notebook_posts)
    
    # Deduplicate
    unique_posts = list(all_posts)
    print(f"\nTotal unique posts: {len(unique_posts)}")
    
    # Download posts
    downloaded = 0
    skipped = 0
    failed = 0
    
    for i, url in enumerate(sorted(unique_posts)):
        if already_downloaded(url, output_dir):
            print(f"[{i+1}/{len(unique_posts)}] Skipping (already downloaded): {sanitize_filename(url)}")
            skipped += 1
            continue
            
        print(f"[{i+1}/{len(unique_posts)}] {url}")
        if download_post(url, output_dir):
            downloaded += 1
        else:
            failed += 1
        
        # Be polite with requests
        time.sleep(1)
    
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped:    {skipped}")
    print(f"  Failed:     {failed}")
    print(f"  Total:      {len(unique_posts)}")
    print(f"\nAll files in: {output_dir}")

if __name__ == "__main__":
    main()
