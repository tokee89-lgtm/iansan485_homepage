const fs = require('fs');
const https = require('https');

https.get('https://rss.blog.naver.com/iansan485.xml', (res) => {
  let xml = '';
  res.on('data', d => xml += d);
  res.on('end', () => {
    let items = [];
    let itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match;
    while ((match = itemRegex.exec(xml)) !== null) {
      items.push(match[1]);
    }
    
    let existingData = [];
    const dataFile = 'js/newsData.js';
    if (fs.existsSync(dataFile)) {
      const content = fs.readFileSync(dataFile, 'utf8');
      const dataMatch = content.match(/const newsData = (\[[\s\S]*?\]);/);
      if (dataMatch) {
         try {
           existingData = JSON.parse(dataMatch[1]);
         } catch(e) {}
      }
    }
    
    let existingLinks = new Set(existingData.map(d => d.link && d.link.split('?')[0]));
    let maxId = existingData.reduce((m, d) => Math.max(m, d.id || 0), 0);
    
    let newPosts = [];
    for (let item of items) {
       let linkMatch = item.match(/<link><!\[CDATA\[(.*?)\]\]><\/link>/) || item.match(/<link>(.*?)<\/link>/);
       let link = linkMatch ? linkMatch[1] : '';
       let cleanLink = link.split('?')[0];
       
       if (existingLinks.has(cleanLink) || !cleanLink) continue;
       
       let titleMatch = item.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>/) || item.match(/<title>(.*?)<\/title>/);
       let title = titleMatch ? titleMatch[1] : '';
       
       let catMatch = item.match(/<category><!\[CDATA\[(.*?)\]\]><\/category>/) || item.match(/<category>(.*?)<\/category>/);
       let category = catMatch ? catMatch[1] : '알림마당';
       
       let dateMatch = item.match(/<pubDate>(.*?)<\/pubDate>/);
       let dateStr = dateMatch ? dateMatch[1] : '';
       let dt = new Date(dateStr);
       let formattedDate = `${dt.getFullYear()}.${String(dt.getMonth()+1).padStart(2,'0')}.${String(dt.getDate()).padStart(2,'0')}`;
       
       let descMatch = item.match(/<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>/) || item.match(/<description>([\s\S]*?)<\/description>/);
       let descRaw = descMatch ? descMatch[1] : '';
       
       let textOnly = descRaw.replace(/<[^>]+>/g, '').trim();
       let summary = textOnly.substring(0, 120) + (textOnly.length > 120 ? '...' : '');
       
       let imgMatch = descRaw.match(/src=["'](http[^"']+(?:jpg|jpeg|png|gif|JPEG|JPG|PNG)[^"']*)["']/i);
       let image = imgMatch ? imgMatch[1] : 'images/static/notice_placeholder.png';
       
       // Optimize image size if pstatic
       if (image.includes('pstatic.net')) {
           image = image.replace('type=s3', 'type=w800').replace('type=w1', 'type=w800');
       }
       
       newPosts.push({ category, title, date: formattedDate, image, summary, content: descRaw, link });
    }
    
    if (newPosts.length > 0) {
      newPosts.reverse();
      newPosts.forEach(p => p.id = ++maxId);
      existingData.unshift(...newPosts.reverse());
      
      let finalJs = `const newsData = ${JSON.stringify(existingData, null, 2)};\n`;
      fs.writeFileSync(dataFile, finalJs, 'utf8');
      if (fs.existsSync('dist/js')) fs.writeFileSync('dist/js/newsData.js', finalJs, 'utf8');
      console.log('Successfully added ' + newPosts.length + ' posts!');
    } else {
      console.log('No new posts needed to update.');
    }
  });
});
