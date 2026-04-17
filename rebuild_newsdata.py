"""
rebuild_newsdata.py
기존의 깨진 newsData.js를 버리고 RSS 피드에서 완전히 새로 생성합니다.
"""
import urllib.request
import re
import os
import json
import datetime
import hashlib
import shutil
from email.utils import parsedate_tz, mktime_tz

RSS_URL = "https://rss.blog.naver.com/iansan485.xml"
IMAGE_DIR = 'images/blog'
DATA_FILE = "js/newsData.js"
DIST_DATA_FILE = "dist/js/newsData.js"
DEFAULT_IMG = "images/static/notice_placeholder.png"

def ensure_dirs():
    for d in [IMAGE_DIR, 'dist/'+IMAGE_DIR, os.path.dirname(DIST_DATA_FILE)]:
        os.makedirs(d, exist_ok=True)

def fetch_rss():
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read()
            # Try UTF-8 first, fall back to detected encoding
            try:
                return raw.decode('utf-8')
            except:
                return raw.decode('euc-kr', errors='replace')
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return None

def download_image(url):
    if not url:
        return DEFAULT_IMG
    try:
        clean_url = url.split('?')[0] if 'pstatic.net' in url or 'naver.com' in url else url
        url_hash = hashlib.md5(clean_url.encode()).hexdigest()
        ext = 'jpg'
        if 'png' in url.lower(): ext = 'png'
        elif 'gif' in url.lower(): ext = 'gif'
        filename = f"blog_fixed_{url_hash[:12]}.{ext}"
        filepath = os.path.join(IMAGE_DIR, filename)
        dist_filepath = os.path.join('dist', IMAGE_DIR, filename)
        rel_path = f"images/blog/{filename}"

        if os.path.exists(filepath):
            if not os.path.exists(dist_filepath):
                shutil.copy2(filepath, dist_filepath)
            return rel_path

        optimized_url = url
        if 'pstatic.net' in url:
            optimized_url = url.replace('type=s3', 'type=w800')

        print(f"  Downloading: {filename}")
        req = urllib.request.Request(optimized_url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://blog.naver.com/'
        })
        with urllib.request.urlopen(req, timeout=15) as res:
            data = res.read()
            with open(filepath, 'wb') as f: f.write(data)
            with open(dist_filepath, 'wb') as f: f.write(data)
        return rel_path
    except Exception as e:
        print(f"  Image download failed: {e}")
        return DEFAULT_IMG

def rebuild():
    ensure_dirs()
    
    print("▶ RSS 피드 가져오는 중...")
    xml_data = fetch_rss()
    if not xml_data:
        print("❌ RSS 피드를 가져올 수 없습니다.")
        return

    items = re.findall(r'<item>(.*?)</item>', xml_data, re.DOTALL)
    print(f"  RSS에서 {len(items)}개 글 발견")

    posts = []
    for i, item in enumerate(items):
        title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item) or re.search(r'<title>(.*?)</title>', item)
        if not title_match:
            continue
        title = title_match.group(1).strip()

        link_match = re.search(r'<guid>(.*?)</guid>', item) or re.search(r'<link>(.*?)</link>', item)
        link = link_match.group(1).strip() if link_match else ""
        # Clean up rss tracking parameters
        link = re.sub(r'\?fromRss=true.*', '', link)

        date_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
        date_str = date_match.group(1) if date_match else ""
        try:
            tt = parsedate_tz(date_str)
            ts = mktime_tz(tt)
            dt = datetime.datetime.fromtimestamp(ts)
            formatted_date = dt.strftime("%Y.%m.%d")
        except:
            formatted_date = "Unknown"

        cat_match = re.search(r'<category><!\[CDATA\[(.*?)\]\]></category>', item) or re.search(r'<category>(.*?)</category>', item)
        category = cat_match.group(1).strip() if cat_match else "알림마당"

        desc_match = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item, re.DOTALL) or re.search(r'<description>(.*?)</description>', item, re.DOTALL)
        if not desc_match:
            continue
        desc_raw = desc_match.group(1)
        desc_text = desc_raw.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&').replace('&nbsp;', ' ')

        text_only = re.sub(r'<[^>]+>', '', desc_text).strip()
        summary = text_only[:120] + ("..." if len(text_only) > 120 else "")

        img_match = re.search(r'src=["\']([^"\']*(?:jpg|jpeg|png|gif|JPEG|JPG|PNG)[^"\']*)["\']', desc_raw, re.I)
        img_url = img_match.group(1) if img_match else None
        img_local = download_image(img_url)

        post_id = len(items) - i  # newest gets highest id
        posts.append({
            "id": post_id,
            "category": category,
            "title": title,
            "date": formatted_date,
            "image": img_local,
            "summary": summary,
            "content": desc_text,
            "link": link
        })
        print(f"  [{i+1}/{len(items)}] {title[:40]}")

    if not posts:
        print("❌ 처리된 글이 없습니다.")
        return

    js_content = f"const newsData = {json.dumps(posts, ensure_ascii=False, indent=2)};\n"

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"\n✅ {DATA_FILE} 저장 완료 ({len(posts)}개 글)")

    with open(DIST_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"✅ {DIST_DATA_FILE} 저장 완료")

if __name__ == "__main__":
    rebuild()
