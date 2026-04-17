import os
import re
import urllib.request
import hashlib

# Configuration
BASE_DIR = r"c:\Users\이젠\.gemini\antigravity\scratch\iansan485_homepage"
IMAGE_DIR = os.path.join(BASE_DIR, "images", "static")
TARGET_FILES = [
    "index.html",
    "about.html",
    "projects.html",
    "news.html",
    "admin.html",
    "js/main.js",
    "js/newsData.js"
]

def ensure_dir():
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        print(f"Created: {IMAGE_DIR}")

def download_image(url):
    try:
        # Create unique filename based on URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        filename = f"static_{url_hash[:10]}.jpg"
        filepath = os.path.join(IMAGE_DIR, filename)

        if os.path.exists(filepath):
            return f"images/static/{filename}"

        print(f"Downloading: {url} ...")
        # Use urllib instead of requests
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            with open(filepath, "wb") as f:
                f.write(response.read())
            return f"images/static/{filename}"
    except Exception as e:
        print(f"Failed to download {url}: {e}")
    return url

def process_files():
    # Regex for Unsplash links
    unsplash_pattern = re.compile(r'https?://images\.unsplash\.com/[^\s"\'>]+')

    for rel_path in TARGET_FILES:
        filepath = os.path.join(BASE_DIR, rel_path.replace("/", os.sep))
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        urls = unsplash_pattern.findall(content)
        if not urls:
            continue

        print(f"Processing {rel_path}: {len(urls)} images found.")
        new_content = content
        for url in set(urls):
            local_path = download_image(url)
            if local_path != url:
                new_content = new_content.replace(url, local_path)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated: {rel_path}")

if __name__ == "__main__":
    ensure_dir()
    process_files()
    print("\n✅ Static asset localization complete.")
