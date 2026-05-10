import urllib.request
import re
rss = urllib.request.urlopen('https://rss.blog.naver.com/iansan485.xml').read().decode('utf-8')
items = re.findall(r'<item>(.*?)</item>', rss, re.DOTALL)
for item in items:
    title = re.search(r'<title>(.*?)</title>', item, re.DOTALL).group(1)
    date = re.search(r'<pubDate>(.*?)</pubDate>', item).group(1)
    desc = re.search(r'<description>(.*?)</description>', item, re.DOTALL).group(1)
    if 'May' in date and '08' in date:
        print('Title:', title)
        print('Date:', date)
        print('Images:', len(re.findall(r'<img', desc, re.I)))
