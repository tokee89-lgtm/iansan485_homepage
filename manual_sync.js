const fs = require('fs');
const https = require('https');
const crypto = require('crypto');
const path = require('path');

// Helper to download images from Naver Blog
function downloadImage(url) {
  return new Promise((resolve) => {
    if (!url || !url.startsWith('http') || (!url.includes('pstatic.net') && !url.includes('naver.com'))) {
      return resolve(url || 'images/static/notice_placeholder.png');
    }

    const cleanUrl = url.split('?')[0];
    const hash = crypto.createHash('md5').update(cleanUrl).digest('hex').substring(0, 12);
    const ext = url.toLowerCase().includes('png') ? 'png' : (url.toLowerCase().includes('gif') ? 'gif' : 'jpg');
    const filename = `blog_${hash}.${ext}`;
    const relPath = `images/blog/${filename}`;
    const targetPath = path.join(__dirname, relPath);

    if (fs.existsSync(targetPath)) return resolve(relPath);

    const dir = path.dirname(targetPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    console.log(`Downloading: ${filename}`);
    const optUrl = url.replace('type=s3', 'type=w800').replace('type=w1', 'type=w800');
    
    const request = https.get(optUrl, { 
      headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://blog.naver.com/' } 
    }, (res) => {
      if (res.statusCode !== 200) return resolve(url);
      
      const fileStream = fs.createWriteStream(targetPath);
      res.pipe(fileStream);
      fileStream.on('finish', () => {
        fileStream.close();
        // Sync to dist
        const distPath = path.join(__dirname, 'dist', relPath);
        if (fs.existsSync(path.join(__dirname, 'dist'))) {
          const distDir = path.dirname(distPath);
          if (!fs.existsSync(distDir)) fs.mkdirSync(distDir, { recursive: true });
          fs.copyFileSync(targetPath, distPath);
        }
        resolve(relPath);
      });
    });
    request.on('error', () => resolve(url));
    request.setTimeout(15000, () => { request.destroy(); resolve(url); });
  });
}

https.get('https://rss.blog.naver.com/iansan485.xml', (res) => {
  let xml = '';
  res.on('data', d => xml += d);
  res.on('end', async () => {
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
    const feedItems = items.reverse(); // Oldest first for ID assignment
    for (let item of feedItems) {
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
       
       let imgMatch = descRaw.match(/src=["'](https?:\/\/[^"']+(?:jpg|jpeg|png|gif|JPEG|JPG|PNG)[^"']*)["']/i);
       let imageUrl = imgMatch ? imgMatch[1] : '';
       
       // Download image
       let localImagePath = await downloadImage(imageUrl);
       
       // Handle inline content images
       let updatedContent = descRaw;
       const contentImgRegex = /src=["'](https?:\/\/blogthumb\.pstatic\.net\/[^"']+)["']/gi;
       let cMatch;
       while ((cMatch = contentImgRegex.exec(descRaw)) !== null) {
          const cLocal = await downloadImage(cMatch[1]);
          updatedContent = updatedContent.replace(cMatch[1], cLocal);
       }
       
       newPosts.unshift({ 
         id: ++maxId,
         category, 
         title, 
         date: formattedDate, 
         image: localImagePath, 
         summary, 
         content: updatedContent, 
         link 
       });
    }
    
    if (newPosts.length > 0) {
      existingData.unshift(...newPosts);
      
      let finalJs = `const newsData = ${JSON.stringify(existingData, null, 2)};\n`;
      fs.writeFileSync(dataFile, finalJs, 'utf8');
      if (fs.existsSync('dist/js')) fs.writeFileSync('dist/js/newsData.js', finalJs, 'utf8');
      console.log('Successfully synced ' + newPosts.length + ' new posts with images!');
    } else {
      console.log('No new posts found.');
    }
  });
});
