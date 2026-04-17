document.addEventListener('DOMContentLoaded', () => {
  // ── Mobile Menu Toggle ──────────────────────────────────────────────────
  const menuToggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('nav');
  if (menuToggle) {
    menuToggle.addEventListener('click', () => nav.classList.toggle('active'));
    nav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => nav.classList.remove('active'));
    });
  }

  // ── Scroll Animations ───────────────────────────────────────────────────
  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        obs.unobserve(entry.target);
      }
    });
  }, { rootMargin: '0px', threshold: 0.1 });

  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

  // ── Header Shrink on Scroll ─────────────────────────────────────────────
  const header = document.querySelector('header');
  const headerContainer = document.querySelector('.header-container');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      header.style.boxShadow = '0 4px 12px rgba(0,0,0,0.12)';
      if (headerContainer) headerContainer.style.height = '64px';
    } else {
      header.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';
      if (headerContainer) headerContainer.style.height = '80px';
    }
  });

  // ── Scroll-to-Top Button ────────────────────────────────────────────────
  const scrollBtn = document.createElement('button');
  scrollBtn.className = 'scroll-top-btn';
  scrollBtn.innerHTML = '<i class="fa-solid fa-chevron-up"></i>';
  scrollBtn.setAttribute('aria-label', '맨 위로');
  document.body.appendChild(scrollBtn);

  window.addEventListener('scroll', () => {
    scrollBtn.classList.toggle('visible', window.scrollY > 300);
  });
  scrollBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  // ── Page Routing ────────────────────────────────────────────────────────
  if (document.getElementById('news-grid')) {
    initNewsPage();
  }
  if (document.getElementById('detail-container')) {
    renderNewsDetail();
  }
});

// ── Data: Merge Local + Naver Posts ────────────────────────────────────────
function getLocalPosts() {
  return JSON.parse(localStorage.getItem('localPosts') || '[]')
    .map(p => ({ ...p, source: 'local' }));
}

let allPostsCache = null;

async function getAllPosts() {
  if (allPostsCache) return allPostsCache;
  const local = getLocalPosts();
  let naver = (typeof newsData !== 'undefined' ? newsData : [])
    .map(p => ({ ...p, source: 'naver' }));

  allPostsCache = [...local, ...naver];
  return allPostsCache;
}

// ── News Page ─────────────────────────────────────────────────────────────
const ITEMS_PER_PAGE = 6;
let currentPage = 1;
let currentCategory = '전체';
let currentSearch = '';

function initNewsPage() {
  // Wire up filter buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // Use data-category if available, otherwise fallback to text
      currentCategory = btn.getAttribute('data-category') || btn.textContent.trim();
      currentPage = 1;
      renderNews(1);
    });
  });

  // Wire up search
  const searchInput = document.querySelector('.search-box input');
  const searchBtn = document.querySelector('.search-box button');
  if (searchBtn) {
    searchBtn.addEventListener('click', () => {
      currentSearch = searchInput ? searchInput.value.trim() : '';
      currentPage = 1;
      renderNews(1);
    });
  }
  if (searchInput) {
    searchInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        currentSearch = searchInput.value.trim();
        currentPage = 1;
        renderNews(1);
      }
    });
  }

  renderNews(1);
}

async function getFilteredPosts() {
  let posts = await getAllPosts();
  
  if (currentCategory && currentCategory !== 'all' && currentCategory !== '전체') {
    // Normalize mapping for exact blog category matching
    posts = posts.filter(p => {
      const pCat = (p.category || "").replace(/\s/g, '').trim();
      const targetCat = currentCategory.replace(/\s/g, '').trim();
      return pCat === targetCat;
    });
  }
  
  if (currentSearch) {
    const q = currentSearch.toLowerCase();
    posts = posts.filter(p =>
      (p.title && p.title.toLowerCase().includes(q)) ||
      (p.summary && p.summary.toLowerCase().includes(q))
    );
  }
  return posts;
}

async function renderNews(page = 1) {
  const newsGrid = document.getElementById('news-grid');
  if (!newsGrid) return;

  const isIndexPage =
    window.location.pathname.endsWith('index.html') ||
    window.location.pathname === '/' ||
    window.location.pathname.endsWith('\\') ||
    window.location.pathname === '';

  if (isIndexPage) {
    // Index: show 3 newest posts
    const all = await getAllPosts();
    const posts = all.slice(0, 3);
    newsGrid.innerHTML = renderCards(posts);
    return;
  }

  // News page: filtered + paginated
  currentPage = page;
  const allFiltered = await getFilteredPosts();
  const startIndex = (page - 1) * ITEMS_PER_PAGE;
  const dataToRender = allFiltered.slice(startIndex, startIndex + ITEMS_PER_PAGE);

  if (dataToRender.length === 0) {
    newsGrid.innerHTML = `
      <div style="grid-column:1/-1; text-align:center; padding:60px 20px; color:var(--text-muted);">
        <i class="fa-solid fa-inbox" style="font-size:3rem; margin-bottom:16px; display:block; opacity:0.4;"></i>
        <p style="font-size:1.1rem;">검색 결과가 없습니다.</p>
      </div>`;
    const paginationContainer = document.querySelector('.pagination');
    if (paginationContainer) paginationContainer.style.display = 'none';
    return;
  }

  newsGrid.innerHTML = renderCards(dataToRender);
  renderPagination(allFiltered.length);
}

function renderCards(posts) {
  return posts.map(post => {
    const fallback = "images/static/static_f0a251dd7c.jpg";
    const img = post.image || fallback;
    const localBadge = post.source === 'local'
      ? `<span style="display:inline-block;background:rgba(26,79,139,0.12);color:var(--primary-color);border-radius:20px;padding:2px 10px;font-size:0.75rem;font-weight:600;margin-bottom:8px;">
           <i class="fa-solid fa-pencil" style="margin-right:4px;"></i>직접 작성
         </span>`
      : '';
    const categoryBadge = post.category
      ? `<span style="display:inline-block;background:rgba(247,171,27,0.15);color:#b45309;border-radius:20px;padding:2px 10px;font-size:0.75rem;font-weight:600;margin-bottom:8px;margin-left:4px;">${post.category}</span>`
      : '';

    return `
      <a href="news_detail.html?id=${post.id}&src=${post.source || 'naver'}" class="card">
        <img src="${img}" alt="${post.title}" class="card-img"
          referrerpolicy="no-referrer"
          onerror="this.src='${fallback}'">
        <div class="card-content">
          <div>${localBadge}${categoryBadge}</div>
          <span class="card-date">${post.date}</span>
          <h3>${post.title}</h3>
          <p>${post.summary || ''}</p>
          <span class="card-link">자세히 보기 <i class="fa-solid fa-arrow-right"></i></span>
        </div>
      </a>`;
  }).join('');
}

function renderPagination(totalItems) {
  const paginationContainer = document.querySelector('.pagination');
  if (!paginationContainer) return;

  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
  if (totalPages <= 1) {
    paginationContainer.style.display = 'none';
    return;
  }

  paginationContainer.style.display = 'flex';

  // Show up to 9 page numbers around current page
  const range = 4;
  let startP = Math.max(1, currentPage - range);
  let endP = Math.min(totalPages, currentPage + range);
  if (endP - startP < range * 2) {
    if (startP === 1) endP = Math.min(totalPages, startP + range * 2);
    else startP = Math.max(1, endP - range * 2);
  }

  let html = '';
  html += `<div class="page-link${currentPage <= 1 ? ' disabled' : ''}" onclick="if(currentPage>1)renderNews(currentPage-1)">
    <i class="fa-solid fa-chevron-left"></i></div>`;

  if (startP > 1) {
    html += `<div class="page-link" onclick="renderNews(1)">1</div>`;
    if (startP > 2) html += `<div class="page-link" style="pointer-events:none;">…</div>`;
  }

  for (let i = startP; i <= endP; i++) {
    html += `<div class="page-link ${i === currentPage ? 'active' : ''}" onclick="renderNews(${i})">${i}</div>`;
  }

  if (endP < totalPages) {
    if (endP < totalPages - 1) html += `<div class="page-link" style="pointer-events:none;">…</div>`;
    html += `<div class="page-link" onclick="renderNews(${totalPages})">${totalPages}</div>`;
  }

  html += `<div class="page-link${currentPage >= totalPages ? ' disabled' : ''}" onclick="if(currentPage<${totalPages})renderNews(currentPage+1)">
    <i class="fa-solid fa-chevron-right"></i></div>`;

  paginationContainer.innerHTML = html;
}

// ── News Detail View ──────────────────────────────────────────────────────
async function renderNewsDetail() {
  const container = document.getElementById('detail-container');
  if (!container) return;

  const urlParams = new URLSearchParams(window.location.search);
  const idParam = urlParams.get('id');
  const srcParam = urlParams.get('src') || 'naver';

  if (!idParam) {
    container.innerHTML = notFoundHTML('게시물 ID가 누락되었습니다.');
    return;
  }

  let post = null;

  if (srcParam === 'local') {
    const localPosts = JSON.parse(localStorage.getItem('localPosts') || '[]');
    post = localPosts.find(p => p.id === parseInt(idParam) || String(p.id) === idParam);
  }

  if (!post) {
    const all = await getAllPosts();
    post = all.find(p => String(p.id) === idParam);
  }

  if (!post) {
    container.innerHTML = notFoundHTML('삭제되었거나 잘못된 주소입니다.');
    return;
  }

  const fallback = "images/static/static_f0a251dd7c.jpg";
  const heroImg = post.image
    ? `<img src="${post.image}" alt="${post.title}"
         style="width:100%; height:auto; max-height:600px; object-fit:contain; background:#f8fafc; border-radius:12px; margin-bottom:30px;"
         onerror="this.style.display='none'">`
    : '';

  container.innerHTML = `
    <div class="detail-header fade-in">
      ${heroImg}
      ${post.category ? `<span style="display:inline-block;background:rgba(247,171,27,0.15);color:#b45309;border-radius:20px;padding:4px 14px;font-size:0.85rem;font-weight:600;margin-bottom:12px;">${post.category}</span>` : ''}
      <h1>${post.title}</h1>
      <span class="detail-date"><i class="fa-regular fa-calendar"></i> ${post.date}</span>
      <hr>
    </div>
    <div class="detail-body fade-in" style="transition-delay:0.2s;">
      ${post.content.replace(/<img/gi, '<img referrerpolicy="no-referrer"')}
    </div>
    <div class="detail-footer fade-in" style="text-align:center;margin-top:60px;padding-top:30px;border-top:1px solid #E5E7EB;transition-delay:0.4s;">
      <a href="news.html" class="btn btn-outline" style="min-width:200px;padding:15px;">
        <i class="fa-solid fa-arrow-left" style="margin-right:8px;"></i>목록으로 돌아가기
      </a>
    </div>
  `;

  setTimeout(() => {
    container.querySelectorAll('.fade-in').forEach(el => el.classList.add('visible'));
  }, 100);
}

function notFoundHTML(msg) {
  return `<div style="text-align:center;padding:60px 20px;">
    <i class="fa-solid fa-triangle-exclamation" style="font-size:3rem;color:#f59e0b;margin-bottom:20px;display:block;"></i>
    <h2 style="margin-bottom:12px;">존재하지 않는 게시물입니다.</h2>
    <p style="color:var(--text-muted);margin-bottom:28px;">${msg}</p>
    <a href="news.html" class="btn btn-primary">목록으로 돌아가기</a>
  </div>`;
}
