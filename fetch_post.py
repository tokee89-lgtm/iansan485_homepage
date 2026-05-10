import urllib.request
import re

url = "https://blog.naver.com/PostView.naver?blogId=iansan485&logNo=224279071626"
html = urllib.request.urlopen(url).read().decode('utf-8')

# Naver blog post images are often inside div with class "se-component se-image" or similar
imgs = re.findall(r'src=["\'](https?://mblogthumb-phinf\.pstatic\.net/[^"\']+type=[^"\']+)["\']', html)
if not imgs:
    imgs = re.findall(r'src=["\'](https?://blogthumb\.pstatic\.net/[^"\']+)["\']', html)
    
print("Found images:", len(imgs))
for img in imgs:
    print(img)
