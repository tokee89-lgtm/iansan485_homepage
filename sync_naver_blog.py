import urllib.request
import re
import os
import json
import datetime
import hashlib
from email.utils import parsedate_tz, mktime_tz

# Configuration
RSS_URL = "https://rss.blog.naver.com/iansan485.xml"
IMAGE_DIR = 'images/blog'
DATA_FILE = "js/newsData.js"
DEFAULT_IMG = "images/static/notice_placeholder.png"

def ensure_dirs():
    dirs = [IMAGE_DIR, os.path.join('dist', IMAGE_DIR), os.path.dirname(DATA_FILE), os.path.join('dist', os.path.dirname(DATA_FILE))]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def fetch_rss():
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return None

def download_image(url):
    if not url: return DEFAULT_IMG
    
    try:
        # Create unique filename based on URL hash to avoid duplicates and handle Naver's temporary links
        # Strip query parameters for better hashing if it's a known thumbnail service
        clean_url = url.split('?')[0] if 'pstatic.net' in url or 'naver.com' in url else url
        url_hash = hashlib.md5(clean_url.encode()).hexdigest()
        
        # Determine extension
        ext = 'jpg'
        if 'png' in url.lower(): ext = 'png'
        elif 'gif' in url.lower(): ext = 'gif'
        
        filename = f"blog_{url_hash[:12]}.{ext}"
        filepath = os.path.join(IMAGE_DIR, filename)
        dist_filepath = os.path.join('dist', IMAGE_DIR, filename)
        rel_path = f"images/blog/{filename}"

        if os.path.exists(filepath):
            # Also ensure it exists in dist
            if not os.path.exists(dist_filepath):
                import shutil
                if os.path.exists(os.path.dirname(dist_filepath)):
                    shutil.copy2(filepath, dist_filepath)
            return rel_path

        # Optimize Naver image size if possible
        optimized_url = url
        if 'pstatic.net' in url:
            optimized_url = url.replace('type=s3', 'type=w800').replace('type=w1', 'type=w800')
        
        print(f"Downloading blog image: {optimized_url}")
        req = urllib.request.Request(optimized_url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://blog.naver.com/'
        })
        with urllib.request.urlopen(req, timeout=15) as res:
            image_content = res.read()
            with open(filepath, 'wb') as f:
                f.write(image_content)
            
            # Ensure dist copy
            os.makedirs(os.path.dirname(dist_filepath), exist_ok=True)
            with open(dist_filepath, 'wb') as f:
                f.write(image_content)
                
        return rel_path
    except Exception as e:
        print(f"Failed to download image {url}: {e}")
        return DEFAULT_IMG

def sync():
    ensure_dirs()
    
    # --- 1. Load existing data ---
    existing_data = []
    max_id = 0
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                # Extract JSON array from "const newsData = [...];"
                match = re.search(r'const newsData = (\[.*?\]);', content, re.DOTALL)
                if match:
                    existing_data = json.loads(match.group(1))
                    if existing_data:
                        max_id = max(item.get('id', 0) for item in existing_data)
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")
    
    # Create lookup for existing posts
    existing_links = {item.get('link') for item in existing_data if item.get('link')}

    # --- 2. Fetch and parse RSS ---
    xml_data = fetch_rss()
    if not xml_data: return

    items = re.findall(r'<item>(.*?)</item>', xml_data, re.DOTALL)
    new_posts_found = 0

    # We process items in reverse order to maintain correct ID generation for new posts
    # but the final list should be newest first.
    rss_posts = []
    for item in items:
        title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item) or re.search(r'<title>(.*?)</title>', item)
        if not title_match: continue
        title = title_match.group(1).strip()

        link_match = re.search(r'<link>(.*?)</link>', item)
        link = link_match.group(1).strip() if link_match else ""

        # Skip if already exists
        if link in existing_links:
            continue

        date_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
        date_str = date_match.group(1) if date_match else ""
        try:
            # Handle Naver RSS date format correctly
            tt = parsedate_tz(date_str)
            ts = mktime_tz(tt)
            dt = datetime.datetime.fromtimestamp(ts)
            formatted_date = dt.strftime("%Y.%m.%d")
        except:
            formatted_date = date_str[:16] if date_str else "Unknown Date"

        category_match = re.search(r'<category><!\[CDATA\[(.*?)\]\]></category>', item) or re.search(r'<category>(.*?)</category>', item)
        category = category_match.group(1) if category_match else "알림마당"
        
        desc_match = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item, re.DOTALL) or re.search(r'<description>(.*?)</description>', item, re.DOTALL)
        if not desc_match: continue
        desc_raw = desc_match.group(1)
        
        # Normalize HTML entities
        desc_text = desc_raw.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&').replace('&nbsp;', ' ')
        
        text_only = re.sub(r'<[^>]+>', '', desc_text).strip()
        summary = text_only[:120] + ("..." if len(text_only) > 120 else "")
        
        img_match = re.search(r'src=["\'](http[^"\']*(?:jpg|jpeg|png|gif|JPEG|JPG|PNG)[^"\']*)["\']', desc_raw, re.I)
        img_url = img_match.group(1) if img_match else None
        img_local_path = download_image(img_url)

        rss_posts.append({
            "id": 0, # Placeholder
            "category": category,
            "title": title,
            "date": formatted_date,
            "image": img_local_path,
            "summary": summary,
            "content": desc_text,
            "link": link
        })
        new_posts_found += 1

    # --- 3. Merge and Save ---
    if new_posts_found > 0:
        # Assign IDs to new posts (reversing rss_posts to keep chronological ID order)
        for post in reversed(rss_posts):
            max_id += 1
            post['id'] = max_id
        
        # Merge: Newest posts first
        final_data = rss_posts + existing_data
    else:
        final_data = existing_data
        # Special case: fix broken external images in existing data
        fixed_count = 0
        for item in final_data:
            if item.get('image', '').startswith('http') and ('pstatic.net' in item['image'] or 'naver.com' in item['image']):
                print(f"Fixing external image for post ID {item['id']}...")
                item['image'] = download_image(item['image'])
                fixed_count += 1
        if fixed_count > 0:
            print(f"Fixed {fixed_count} external images.")
        else:
            print("No new posts found and no images to fix.")
            return

    js_content = f"const newsData = {json.dumps(final_data, ensure_ascii=False, indent=2)};\n"
    
    # Write to root
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)
    
    # Write to dist
    dist_data_file = os.path.join('dist', DATA_FILE)
    if os.path.exists(os.path.dirname(dist_data_file)):
        with open(dist_data_file, "w", encoding="utf-8") as f:
            f.write(js_content)
    
    print(f"✅ Sync complete: Added {new_posts_found} new posts. Total: {len(final_data)}")


if __name__ == "__main__":
    sync()
