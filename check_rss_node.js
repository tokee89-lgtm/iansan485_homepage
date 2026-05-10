const https = require('https');
https.get('https://rss.blog.naver.com/iansan485.xml', (res) => {
  let xml = '';
  res.on('data', d => xml += d);
  res.on('end', () => {
    let items = [];
    let itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match;
    while ((match = itemRegex.exec(xml)) !== null) items.push(match[1]);
    
    for (let item of items) {
       if (item.includes('5월 8일') || item.includes('May 08') || item.includes('08 May')) {
           console.log("Found post!");
           let title = item.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>/) || item.match(/<title>(.*?)<\/title>/);
           console.log("Title:", title ? title[1] : "");
           let desc = item.match(/<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>/) || item.match(/<description>([\s\S]*?)<\/description>/);
           let descText = desc ? desc[1] : "";
           let imgs = descText.match(/<img[^>]+src=["'](.*?)["']/gi);
           console.log("Images found in RSS:", imgs ? imgs.length : 0);
           console.log("Image tags:", imgs);
       }
       if (item.includes('08 May 2026') || item.includes('2026-05-08')) {
           // alternate date format
       }
    }
  });
});
