const test = require('node:test');
const assert = require('node:assert/strict');
const {
  escapeHtml,
  formatDate,
  getArticleId,
  renderPost
} = require('../app.js');

test('escapeHtml', async (t) => {
  await t.test('escapes special HTML characters', () => {
    assert.equal(escapeHtml('<script>alert("xss") & \'test\'</script>'), '&lt;script&gt;alert(&quot;xss&quot;) &amp; &#039;test&#039;&lt;/script&gt;');
  });

  await t.test('handles empty or default input', () => {
    assert.equal(escapeHtml(), '');
    assert.equal(escapeHtml(''), '');
  });

  await t.test('converts non-string values to string and escapes', () => {
    assert.equal(escapeHtml(123), '123');
    assert.equal(escapeHtml(null), 'null');
    assert.equal(escapeHtml(undefined), '');
  });
});

test('formatDate', async (t) => {
  await t.test('returns "Recent" for falsy values', () => {
    assert.equal(formatDate(null), 'Recent');
    assert.equal(formatDate(''), 'Recent');
    assert.equal(formatDate(undefined), 'Recent');
  });

  await t.test('formats valid date strings correctly', () => {
    const formatted = formatDate('2023-10-15T12:00:00Z');
    assert.ok(formatted.includes('Oct') || formatted.includes('10'), 'Should contain month');
    assert.ok(formatted.includes('2023'), 'Should contain year');
  });

  await t.test('returns raw string for invalid date strings', () => {
    assert.equal(formatDate('not-a-date'), 'not-a-date');
  });
});

test('getArticleId', async (t) => {
  await t.test('uses post.id if available', () => {
    assert.equal(getArticleId({ id: 'custom-id-123' }), 'custom-id-123');
  });

  await t.test('generates slugified ID from source_url', () => {
    const post = { source_url: 'https://techcrunch.com/2023/10/15/some-article/' };
    assert.equal(getArticleId(post), 'https-techcrunch-com-2023-10-15-some-article-');
  });

  await t.test('generates random fallback ID if post or source_url is missing', () => {
    const id1 = getArticleId(null);
    const id2 = getArticleId({});
    assert.match(id1, /^article-[a-z0-9]+$/);
    assert.match(id2, /^article-[a-z0-9]+$/);
  });
});

test('renderPost', async (t) => {
  const basePost = {
    id: 'test-post-1',
    source: 'TechCrunch',
    published: '2023-10-15T12:00:00Z',
    title: 'Test Article Title',
    summary: 'Test summary content.',
    source_url: 'https://techcrunch.com/test-article',
    image: 'https://techcrunch.com/image.jpg'
  };

  await t.test('renders standard post with image correctly', () => {
    const html = renderPost(basePost, new Set(), new Set(), {});

    assert.ok(html.includes('data-article-id="test-post-1"'));
    assert.ok(html.includes('<img class="card-image" src="https://techcrunch.com/image.jpg" alt="" loading="lazy">'));
    assert.ok(html.includes('<span>TechCrunch</span>'));
    assert.ok(html.includes('<h3 class="card-title"><a href="https://techcrunch.com/test-article" target="_blank" rel="noreferrer">Test Article Title</a></h3>'));
    assert.ok(html.includes('<p class="card-summary">Test summary content.</p>'));
  });

  await t.test('renders post without image when image property is missing', () => {
    const postNoImage = { ...basePost, image: null };
    const html = renderPost(postNoImage, new Set(), new Set(), {});

    assert.ok(!html.includes('<img class="card-image"'));
  });

  await t.test('applies defaults for missing post properties', () => {
    const minimalPost = { id: 'min-1' };
    const html = renderPost(minimalPost, new Set(), new Set(), {});

    assert.ok(html.includes('<span>TechCrunch</span>'));
    assert.ok(html.includes('Recent'));
    assert.ok(html.includes('href="#"'));
  });

  await t.test('handles liked and saved active states', () => {
    const likedSet = new Set(['test-post-1']);
    const savedSet = new Set(['test-post-1']);

    const activeHtml = renderPost(basePost, likedSet, savedSet, {});
    assert.ok(activeHtml.includes('btn-like active'));
    assert.ok(activeHtml.includes('btn-save active'));

    const inactiveHtml = renderPost(basePost, new Set(), new Set(), {});
    assert.ok(inactiveHtml.includes('btn-like '));
    assert.ok(!inactiveHtml.includes('btn-like active'));
    assert.ok(inactiveHtml.includes('btn-save '));
    assert.ok(!inactiveHtml.includes('btn-save active'));
  });

  await t.test('formats global likes count correctly', () => {
    const likesData = { 'test-post-1': 42 };
    const htmlWithLikes = renderPost(basePost, new Set(), new Set(), likesData);
    assert.ok(htmlWithLikes.includes('<span class="like-count">42</span>'));

    const zeroLikesData = { 'test-post-1': 0 };
    const htmlWithZeroLikes = renderPost(basePost, new Set(), new Set(), zeroLikesData);
    assert.ok(htmlWithZeroLikes.includes('<span class="like-count"></span>'));

    const invalidLikesData = { 'test-post-1': -5 };
    const htmlWithInvalidLikes = renderPost(basePost, new Set(), new Set(), invalidLikesData);
    assert.ok(htmlWithInvalidLikes.includes('<span class="like-count"></span>'));
  });

  await t.test('escapes HTML special characters in post fields to prevent XSS', () => {
    const xssPost = {
      id: 'xss-post',
      source: '<script>alert("source")</script>',
      published: '2023-10-15" onload="alert(1)',
      title: '<b>Title</b> & "Quotes"',
      summary: '<img src=x onerror=alert(1)>',
      source_url: 'https://example.com/"javascript:alert(1)',
      image: 'https://example.com/img.jpg" onerror="alert(1)'
    };

    const html = renderPost(xssPost, new Set(), new Set(), {});

    assert.ok(!html.includes('<script>'));
    assert.ok(html.includes('&lt;script&gt;alert(&quot;source&quot;)&lt;/script&gt;'));
    assert.ok(!html.includes('<b>Title</b>'));
    assert.ok(html.includes('&lt;b&gt;Title&lt;/b&gt; &amp; &quot;Quotes&quot;'));
    assert.ok(html.includes('&lt;img src=x onerror=alert(1)&gt;'));
    assert.ok(html.includes('https://example.com/img.jpg&quot; onerror=&quot;alert(1)'));
  });
});

test('formatDate handles additional falsy, invalid, and timestamp inputs', () => {
  assert.equal(formatDate(), 'Recent');
  assert.equal(formatDate(false), 'Recent');
  assert.equal(formatDate(0), 'Recent');
  assert.equal(formatDate('2023-99-99'), '2023-99-99');

  const dateObj = new Date('2024-01-01T00:00:00Z');
  assert.equal(formatDate(dateObj), dateObj.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  }));

  const timestamp = 1700000000000;
  assert.equal(formatDate(timestamp), new Date(timestamp).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  }));

  const result = formatDate('2023-05-12T00:00:00Z');
  assert.match(result, /2023/);
  assert.match(result, /12|May/i);
});
