const postsEl = document.querySelector('#posts');
const updatedEl = document.querySelector('#last-updated');
const countEl = document.querySelector('#story-count');

function escapeHtml(value = '') {
  return String(value).replace(/[&<>\"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[char]));
}

function formatDate(value) {
  if (!value) return 'Recent';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, {month:'short', day:'numeric', year:'numeric'});
}

function renderPost(post) {
  const points = Array.isArray(post.key_points) && post.key_points.length
    ? `<ul class="points">${post.key_points.map((point) => `<li>${escapeHtml(point)}</li>`).join('')}</ul>` : '';
  const image = post.image ? `<img class="post-image" src="${escapeHtml(post.image)}" alt="" loading="lazy">` : '';
  return `<article class="post">${image}<div class="post-body">
    <div class="post-kicker"><span>${escapeHtml((post.topics || ['Technology'])[0])}</span><span>${escapeHtml(formatDate(post.published))}</span></div>
    <h3>${escapeHtml(post.title)}</h3>
    <div class="author">By ${escapeHtml(post.author || 'TechCrunch')}</div>
    <p class="summary">${escapeHtml(post.summary || '')}</p>${points}
    <div class="post-footer"><span>${escapeHtml(post.credit || 'Shared via TechNews WhatsApp Channel')}</span><a href="${escapeHtml(post.source_url)}" target="_blank" rel="noreferrer">Read full article ↗</a></div>
  </div></article>`;
}

fetch('./data/posts.json', {cache: 'no-store'})
  .then((response) => { if (!response.ok) throw new Error('posts.json unavailable'); return response.json(); })
  .then((data) => {
    const posts = Array.isArray(data.posts) ? data.posts : [];
    countEl.textContent = `${posts.length} ${posts.length === 1 ? 'story' : 'stories'}`;
    updatedEl.textContent = data.updated_at ? `Last checked ${formatDate(data.updated_at)}` : 'Waiting for the first scheduled update';
    postsEl.innerHTML = posts.length ? posts.map(renderPost).join('') : '<div class="empty">No stories have been summarized yet. The next scheduled workflow will check TechCrunch.</div>';
  })
  .catch(() => { postsEl.innerHTML = '<div class="empty">The digest is temporarily unavailable. Please try again after the next workflow run.</div>'; });
