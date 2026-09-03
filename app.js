const postsEl = document.querySelector('#posts');
const updatedEl = document.querySelector('#last-updated');
const countEl = document.querySelector('#story-count');

const LIKED_KEY = 'tn404_liked';
const SAVED_KEY = 'tn404_saved';
const LIKE_WORKER_URL = window.LIKE_WORKER_URL || 'https://technews404-likes.workers.dev';

const sessionLikes = new Set();
const MAX_SESSION_LIKES = 20;

function getStoredArray(key) {
  try {
    const val = localStorage.getItem(key);
    return val ? JSON.parse(val) : [];
  } catch (e) {
    return [];
  }
}

function setStoredArray(key, arr) {
  try {
    localStorage.setItem(key, JSON.stringify(arr));
  } catch (e) {}
}

function toggleStoredItem(key, id) {
  const list = getStoredArray(key);
  const index = list.indexOf(id);
  let active = false;
  if (index >= 0) {
    list.splice(index, 1);
    active = false;
  } else {
    list.push(id);
    active = true;
  }
  setStoredArray(key, list);
  return active;
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>\"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[char]));
}

function formatDate(value) {
  if (!value) return 'Recent';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, {month:'short', day:'numeric', year:'numeric'});
}

function getArticleId(post) {
  if (post && post.id) return post.id;
  if (!post || !post.source_url) return 'article-' + Math.random().toString(36).substring(2, 9);
  return post.source_url.replace(/[^a-zA-Z0-9]/g, '-').replace(/-+/g, '-').toLowerCase();
}

function renderPost(post, likedSet, savedSet, globalLikes = {}) {
  const articleId = getArticleId(post);
  const isLiked = likedSet.has(articleId);
  const isSaved = savedSet.has(articleId);
  const rawCount = globalLikes[articleId];
  const count = typeof rawCount === 'number' && rawCount > 0 ? rawCount : 0;
  const displayCount = count > 0 ? count : '';

  const sourceName = escapeHtml(post.source || 'TechCrunch');
  const dateStr = escapeHtml(formatDate(post.published));
  const title = escapeHtml(post.title || '');
  const summary = escapeHtml(post.summary || '');
  const sourceUrl = escapeHtml(post.source_url || '#');

  return `<article class="card" data-article-id="${escapeHtml(articleId)}">
    <div class="card-meta">
      <span>${sourceName}</span>
      <span class="meta-dot">•</span>
      <time datetime="${escapeHtml(post.published || '')}">${dateStr}</time>
    </div>
    <h3 class="card-title"><a href="${sourceUrl}" target="_blank" rel="noreferrer">${title}</a></h3>
    <p class="card-summary">${summary}</p>
    <div class="card-footer">
      <button type="button" class="btn-icon btn-like ${isLiked ? 'active' : ''}" aria-label="Like story">
        <svg class="icon heart-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l8.78-8.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
        </svg>
        <span class="like-count">${displayCount}</span>
      </button>
      <button type="button" class="btn-icon btn-share" aria-label="Share story" data-title="${title}" data-url="${sourceUrl}">
        <svg class="icon share-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
          <polyline points="16 6 12 2 8 6"></polyline>
          <line x1="12" y1="2" x2="12" y2="15"></line>
        </svg>
      </button>
      <button type="button" class="btn-icon btn-save ${isSaved ? 'active' : ''}" aria-label="Save story">
        <svg class="icon bookmark-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
        </svg>
      </button>
    </div>
  </article>`;
}

let toastTimeout = null;

function showToast(message) {
  let toastEl = document.querySelector('#toast');
  if (!toastEl) {
    toastEl = document.createElement('div');
    toastEl.id = 'toast';
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'status');
    toastEl.setAttribute('aria-live', 'polite');
    document.body.appendChild(toastEl);
  }
  toastEl.textContent = message;
  toastEl.classList.add('show');

  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toastEl.classList.remove('show');
  }, 3000);
}

async function shareArticle(url, title) {
  try {
    if (navigator.share) {
      await navigator.share({ title, url });
    } else {
      await navigator.clipboard.writeText(url);
      showToast('Link copied');
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      try {
        await navigator.clipboard.writeText(url);
        showToast('Link copied');
      } catch (e) {
        showToast('Could not share link');
      }
    }
  }
}

async function dispatchLike(articleId) {
  if (!LIKE_WORKER_URL || sessionLikes.has(articleId) || sessionLikes.size >= MAX_SESSION_LIKES) return;
  sessionLikes.add(articleId);
  try {
    await fetch(LIKE_WORKER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_id: articleId })
    });
  } catch (err) {
    // Ignore network error
  }
}

postsEl.addEventListener('click', (e) => {
  const likeBtn = e.target.closest('.btn-like');
  if (likeBtn) {
    const card = likeBtn.closest('.card');
    if (!card) return;
    const articleId = card.getAttribute('data-article-id');
    if (!articleId) return;

    const countSpan = likeBtn.querySelector('.like-count');
    let currentCount = parseInt(countSpan ? countSpan.textContent : '0', 10);
    if (isNaN(currentCount)) currentCount = 0;

    const isActive = toggleStoredItem(LIKED_KEY, articleId);
    likeBtn.classList.toggle('active', isActive);

    if (isActive) {
      currentCount += 1;
      dispatchLike(articleId);
    } else {
      currentCount = Math.max(0, currentCount - 1);
    }

    if (countSpan) {
      countSpan.textContent = currentCount > 0 ? currentCount : '';
    }
    return;
  }

  const shareBtn = e.target.closest('.btn-share');
  if (shareBtn) {
    const title = shareBtn.getAttribute('data-title') || document.title;
    const url = shareBtn.getAttribute('data-url') || window.location.href;
    shareArticle(url, title);
    return;
  }

  const saveBtn = e.target.closest('.btn-save');
  if (saveBtn) {
    const card = saveBtn.closest('.card');
    if (!card) return;
    const articleId = card.getAttribute('data-article-id');
    if (!articleId) return;

    const isActive = toggleStoredItem(SAVED_KEY, articleId);
    saveBtn.classList.toggle('active', isActive);
    return;
  }
});

Promise.all([
  fetch('./data/posts.json', { cache: 'no-store' }).then((r) => r.ok ? r.json() : {}).catch(() => ({})),
  fetch('./data/likes.json', { cache: 'no-store' }).then((r) => r.ok ? r.json() : {}).catch(() => ({}))
]).then(([postsData, likesData]) => {
  const posts = Array.isArray(postsData.posts) ? postsData.posts : [];
  const globalLikes = (likesData && typeof likesData === 'object') ? likesData : {};
  const likedSet = new Set(getStoredArray(LIKED_KEY));
  const savedSet = new Set(getStoredArray(SAVED_KEY));

  countEl.textContent = `${posts.length} ${posts.length === 1 ? 'story' : 'stories'}`;
  updatedEl.textContent = postsData.updated_at ? `Last checked ${formatDate(postsData.updated_at)}` : 'Waiting for the first scheduled update';
  postsEl.innerHTML = posts.length ? posts.map((post) => renderPost(post, likedSet, savedSet, globalLikes)).join('') : '<div class="empty">No stories have been summarized yet. The next scheduled workflow will check TechCrunch.</div>';
  postsEl.setAttribute('aria-busy', 'false');
}).catch(() => {
  postsEl.innerHTML = '<div class="empty">The digest is temporarily unavailable. Please try again after the next workflow run.</div>';
  postsEl.setAttribute('aria-busy', 'false');
});
