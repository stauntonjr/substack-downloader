#!/usr/bin/env python3
"""
Download The Kaitchup archive - API-based version with pagination

Uses Substack's undocumented internal JSON API:
- GET /api/v1/archive with offset/limit pagination
- GET /api/v1/posts/by-id/{post_id} for full post content

This bypasses the need for browser automation and infinite scroll handling.

For public posts only (no auth required), use v3: python download_kaitchup_v3.py
For full archive with auth, use v4 with SUBSTACK_SID cookie.
"""

import os
import sys
import time
import json
import requests
from urllib.parse import urljoin, urlparse
from datetime import datetime
from pathlib import Path
import html2text


def sanitize_filename(title):
    """Create safe filename from title or URL"""
    if isinstance(title, str) and '/' in title:
        safe = title.split('/')[-1].split('?')[0]
    else:
        safe = str(title).lower().replace(' ', '-').replace('?', '').replace('/', '-')
    
    for suffix in ['-ai-on-a-budget', 'the-kaitchup-', 'the-kaitchup', '-comments']:
        if safe.endswith(suffix):
            safe = safe[:-len(suffix)]
    
    safe = safe.replace('--', '-').replace('_', '-')
    safe = ''.join(c if c.isalnum() or c == '-' else '' for c in safe)
    return safe.lower()


def get_substack_archive(subdomain, session=None, limit=50):
    """
    Fetch all posts from Substack archive using pagination.
    
    Args:
        subdomain: Substack subdomain (e.g., 'kaitchup')
        session: requests.Session() with optional authentication cookie
        limit: Number of posts per request (max 100)
    
    Returns:
        List of all post metadata dictionaries
    """
    if session is None:
        session = requests.Session()
    
    archive_url = f"https://{subdomain}.substack.com/api/v1/archive"
    all_posts = []
    offset = 0
    
    while True:
        params = {
            "sort": "new",
            "search": "",
            "offset": offset,
            "limit": limit
        }
        
        print(f"Fetching archive batch offset={offset} limit={limit}...")
        response = session.get(archive_url, params=params, timeout=30)
        response.raise_for_status()
        
        posts_batch = response.json()
        
        if not posts_batch:
            print("No more posts - archive complete")
            break
        
        all_posts.extend(posts_batch)
        print(f"  Fetched {len(posts_batch)} posts. Total so far: {len(all_posts)}")
        
        offset += limit
        time.sleep(1)  # Rate limit to avoid 429 errors
    
    return all_posts


def fetch_post_content(subdomain, post_id, session=None):
    """
    Fetch full post content by ID.
    
    Args:
        subdomain: Substack subdomain
        post_id: Post ID from archive metadata
        session: requests.Session() with optional authentication cookie
    
    Returns:
        Post dictionary with full content
    """
    if session is None:
        session = requests.Session()
    
    post_url = f"https://{subdomain}.substack.com/api/v1/posts/by-id/{post_id}"
    
    response = session.get(post_url, timeout=30)
    response.raise_for_status()
    
    return response.json().get('post', {})


def download_post(post_data, output_dir):
    """
    Download a single post and save as markdown.
    
    Args:
        post_data: Post dictionary with metadata and content
        output_dir: Directory to save the markdown file
    
    Returns:
        Path to saved file, or None if failed
    """
    post_id = post_data.get('id')
    title = post_data.get('title', f"post_{post_id}")
    body_html = post_data.get('body_html', '')
    
    # Convert HTML to markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    h.ignore_emphasis = False
    markdown_content = h.handle(body_html) if body_html else "No content available"
    
    # Create filename
    timestamp = datetime.now().strftime("%Y-%m-%d")
    safe_title = sanitize_filename(title)
    filename = f"{timestamp}_{safe_title}.md"
    
    # Save to file
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"Source: https://kaitchup.substack.com/p/{post_data.get('slug')}\n\n")
        f.write(f"Post ID: {post_id}\n\n")
        f.write(f"Published: {post_data.get('post_date', 'Unknown')}\n\n")
        f.write("---\n\n")
        f.write(markdown_content)
    
    print(f"    Saved: {filename}")
    return output_path


def already_downloaded(post_id, output_dir):
    """Check if post was already downloaded by checking for post ID in existing files"""
    existing = list(Path(output_dir).glob("*.md"))
    for f in existing:
        try:
            content = f.read_text()
            if f"Post ID: {post_id}" in content:
                return True
        except:
            pass
    return False


def main():
    base_url = "https://kaitchup.substack.com"
    subdomain = "kaitchup"
    output_dir = "/home/jrs/substack-downloader/archive/kaitchup.substack.com"
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Create session with authentication cookie if needed
    session = requests.Session()
    
    # Check if session cookie is provided
    if 'substack.sid' in os.environ:
        session.cookies.set('substack.sid', os.environ['substack.sid'])
        print("Using authenticated session for paid content")
    elif 'SUBSTACK_SID' in os.environ:
        session.cookies.set('substack.sid', os.environ['SUBSTACK_SID'])
        print("Using authenticated session for paid content")
    else:
        print("Using unauthenticated session (public posts only)")
    
    # Fetch all posts from archive
    print("\nFetching archive from Substack API...")
    all_posts = get_substack_archive(subdomain, session)
    
    print(f"\nTotal posts to download: {len(all_posts)}")
    
    # Download each post
    downloaded = 0
    skipped = 0
    failed = 0
    
    for i, post in enumerate(all_posts):
        post_id = post.get('id')
        title = post.get('title', f"Post {post_id}")
        
        if already_downloaded(post_id, output_dir):
            print(f"[{i+1}/{len(all_posts)}] Skipping (already downloaded): {title}")
            skipped += 1
            continue
        
        print(f"[{i+1}/{len(all_posts)}] {title}")
        
        try:
            # Fetch full content
            full_post = fetch_post_content(subdomain, post_id, session)
            
            # Download to markdown
            download_post(full_post, output_dir)
            downloaded += 1
        except Exception as e:
            print(f"    Error: {e}")
            failed += 1
        
        # Be polite with requests
        time.sleep(1)
    
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped:    {skipped}")
    print(f"  Failed:     {failed}")
    print(f"  Total:      {len(all_posts)}")
    print(f"\nAll files in: {output_dir}")


if __name__ == "__main__":
    main()
