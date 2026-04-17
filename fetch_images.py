import urllib.request
import re
import os

url = "https://rss.blog.naver.com/iansan485.xml"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        xml_data = response.read().decode('utf-8')
except Exception as e:
    print(f"Error: {e}")
    exit(1)

items = re.findall(r'<item>(.*?)</item>', xml_data, re.DOTALL)
os.makedirs('images', exist_ok=True)

downloaded = []
for i, item in enumerate(items):
    if i >= 6: break
    desc_match = re.search(r'<description>(.*?)</description>', item, re.DOTALL)
    if not desc_match: continue
    desc = desc_match.group(1)
    
    # decode HTML entities
    desc = desc.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    
    img_match = re.search(r'src=["\'](http[^"\']*?)["\']', desc, re.I)
    if img_match:
        img_url = img_match.group(1)
        print(f"Found image for post {i+1}: {img_url}")
        
        img_name = f"blog_post_{i+1}.jpg"
        img_path = os.path.join('images', img_name)
        
        try:
            req_img = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://blog.naver.com/'})
            with urllib.request.urlopen(req_img) as res, open(img_path, 'wb') as out:
                out.write(res.read())
            downloaded.append((i+1, img_name))
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")

print("RESULTS:", downloaded)
