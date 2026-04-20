import urllib.request
import re
import os
import json
import datetime
import hashlib
import time
from email.utils import parsedate_tz, mktime_tz

# Configuration
RSS_URL = "https://rss.blog.naver.com/iansan485.xml"
IMAGE_DIR = 'images/blog'
DATA_FILE = "js/newsData.js"
DEFAULT_IMG = "images/static/notice_placeholder.png"

def ensure_dirs():
    # Use generic paths for cross-platform compatibility
    dirs = [
        IMAGE_DIR, 
        os.path.join('dist', IMAGE_DIR), 
        os.path.dirname(DATA_FILE), 
        os.path.join('dist', os.path.dirname(DATA_FILE))
    ]
    for d in dirs:
        if d: os.makedirs(d, exist_ok=True)

def fetch_rss():
    print(f"Fetching RSS from {RSS_URL}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    req = urllib.request.Request(RSS_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return None

def download_image(url):
    if not url or not url.startswith('http'): 
        return url if url else DEFAULT_IMG
    
    # We only care about Naver/pstatic images for downloading logic
    if 'pstatic.net' not in url and 'naver.com' not in url:
        return url

    try:
        # Create unique filename based on URL hash
        clean_url = url.split('?')[0]
        url_hash = hashlib.md5(clean_url.encode()).hexdigest()
        
        # Determine extension
        ext = 'jpg'
        if 'png' in url.lower(): ext = 'png'
        elif 'gif' in url.lower(): ext = 'gif'
        
        filename = f"blog_{url_hash[:12]}.{ext}"
        filepath = os.path.join(IMAGE_DIR, filename)
        rel_path = f"images/blog/{filename}"

        if os.path.exists(filepath):
            # Sync to dist if currently missing
            dist_filepath = os.path.join('dist', IMAGE_DIR, filename)
            if not os.path.exists(dist_filepath) and os.path.exists('dist'):
                import shutil
                os.makedirs(os.path.dirname(dist_filepath), exist_ok=True)
                shutil.copy2(filepath, dist_filepath)
            return rel_path

        # Optimize Naver image size if possible
        optimized_url = url
        if 'pstatic.net' in url:
            optimized_url = url.replace('type=s3', 'type=w800').replace('type=s1', 'type=w800').replace('type=w1', 'type=w800')
        
        print(f"  Downloading: {filename}")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://blog.naver.com/'
        }
        req = urllib.request.Request(optimized_url, headers=headers)
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.1)
        
        with urllib.request.urlopen(req, timeout=20) as res:
            image_content = res.read()
            # Save to root
            with open(filepath, 'wb') as f:
                f.write(image_content)
            
            # Save to dist if exists
            dist_filepath = os.path.join('dist', IMAGE_DIR, filename)
            if os.path.exists('dist'):
                os.makedirs(os.path.dirname(dist_filepath), exist_ok=True)
                with open(dist_filepath, 'wb') as f:
                    f.write(image_content)
                
        return rel_path
    except Exception as e:
        print(f"  Failed to download image {url}: {e}")
        return url

def sync():
    ensure_dirs()
    
    # --- 1. Load existing data ---
    existing_data = []
    max_id = 0
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r'const newsData = (\[.*?\]);', content, re.DOTALL)
                if match:
                    existing_data = json.loads(match.group(1))
                    if existing_data:
                        max_id = max(item.get('id', 0) for item in existing_data)
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")
    
    existing_links = {item.get('link').split('?')[0] for item in existing_data if item.get('link')}

    # --- 2. Fetch and parse RSS ---
    xml_data = fetch_rss()
    if not xml_data: return

    items = re.findall(r'<item>(.*?)</item>', xml_data, re.DOTALL)
    new_posts = []

    # Process items in reverse to maintain chronological ID order
    for item in reversed(items):
        link_match = re.search(r'<link>(.*?)</link>', item)
        link = link_match.group(1).strip() if link_match else ""
        clean_link = link.split('?')[0]

        if clean_link in existing_links:
            continue

        title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item) or re.search(r'<title>(.*?)</title>', item)
        title = title_match.group(1).strip() if title_match else "No Title"

        date_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
        date_str = date_match.group(1) if date_match else ""
        try:
            tt = parsedate_tz(date_str)
            ts = mktime_tz(tt)
            dt = datetime.datetime.fromtimestamp(ts)
            formatted_date = dt.strftime("%Y.%m.%d")
        except:
            formatted_date = "Unknown"

        category_match = re.search(r'<category><!\[CDATA\[(.*?)\]\]></category>', item) or re.search(r'<category>(.*?)</category>', item)
        category = category_match.group(1) if category_match else "알림마당"
        
        desc_match = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item, re.DOTALL) or re.search(r'<description>(.*?)</description>', item, re.DOTALL)
        desc_raw = desc_match.group(1) if desc_match else ""
        
        # Normalize HTML entities
        desc_text = desc_raw.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&').replace('&nbsp;', ' ')
        
        text_only = re.sub(r'<[^>]+>', '', desc_text).strip()
        summary = text_only[:120] + ("..." if len(text_only) > 120 else "")
        
        # Main thumbnail
        img_match = re.search(r'src=["\'](http[^"\']*(?:jpg|jpeg|png|gif|JPEG|JPG|PNG)[^"\']*)["\']', desc_raw, re.I)
        img_url = img_match.group(1) if img_match else None
        
        print(f"Processing new post: {title}")
        img_path = download_image(img_url)

        # Content images handling (replace remote with local in HTML)
        content_images = re.findall(r'src=["\'](https?://blogthumb\.pstatic\.net/[^"\']+)["\']', desc_text, re.I)
        for c_url in set(content_images):
            c_path = download_image(c_url)
            desc_text = desc_text.replace(c_url, c_path)

        max_id += 1
        new_posts.insert(0, {
            "id": max_id,
            "category": category,
            "title": title,
            "date": formatted_date,
            "image": img_path,
            "summary": summary,
            "content": desc_text,
            "link": link
        })

    # --- 3. Save Data ---
    if new_posts:
        final_data = new_posts + existing_data
        js_content = f"const newsData = {json.dumps(final_data, ensure_ascii=False, indent=2)};\n"
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(js_content)
        
        dist_data_file = os.path.join('dist', DATA_FILE)
        if os.path.exists(os.path.dirname(dist_data_file)):
            with open(dist_data_file, "w", encoding="utf-8") as f:
                f.write(js_content)
        
        print(f"✅ Sync complete: Added {len(new_posts)} new posts. Total: {len(final_data)}")
    else:
        # Check if existing posts need image repair
        repair_count = 0
        for item in existing_data:
            if item.get('image', '').startswith('http') and ('pstatic.net' in item['image'] or 'naver.com' in item['image']):
                print(f"Repairing image for post {item['id']}...")
                item['image'] = download_image(item['image'])
                repair_count += 1
        
        if repair_count > 0:
            js_content = f"const newsData = {json.dumps(existing_data, ensure_ascii=False, indent=2)};\n"
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write(js_content)
            print(f"✅ Repaired {repair_count} images.")
        else:
            print("No new posts and no images to repair.")

if __name__ == "__main__":
    sync()
