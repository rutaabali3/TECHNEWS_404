const { test, describe } = require('node:test');
const assert = require('node:assert');
const { escapeHtml } = require('../app.js');

describe('escapeHtml utility function', () => {
  test('returns empty string when called with no arguments or undefined', () => {
    assert.strictEqual(escapeHtml(), '');
    assert.strictEqual(escapeHtml(undefined), '');
  });

  test('returns empty string when given empty string input', () => {
    assert.strictEqual(escapeHtml(''), '');
  });

  test('returns unchanged string when no special characters exist', () => {
    assert.strictEqual(escapeHtml('hello world 123!'), 'hello world 123!');
  });

  test('correctly escapes individual HTML special characters', () => {
    assert.strictEqual(escapeHtml('&'), '&amp;');
    assert.strictEqual(escapeHtml('<'), '&lt;');
    assert.strictEqual(escapeHtml('>'), '&gt;');
    assert.strictEqual(escapeHtml('"'), '&quot;');
    assert.strictEqual(escapeHtml("'"), '&#039;');
  });

  test('escapes all special characters in complex strings', () => {
    const input = '<script>alert("xss & \'more\'")</script>';
    const expected = '&lt;script&gt;alert(&quot;xss &amp; &#039;more&#039;&quot;)&lt;/script&gt;';
    assert.strictEqual(escapeHtml(input), expected);
  });

  test('handles HTML attributes with quotes and ampersands correctly', () => {
    const input = 'href="https://example.com/search?q=1&v=2"';
    const expected = 'href=&quot;https://example.com/search?q=1&amp;v=2&quot;';
    assert.strictEqual(escapeHtml(input), expected);
  });

  test('converts non-string inputs to string before escaping', () => {
    assert.strictEqual(escapeHtml(12345), '12345');
    assert.strictEqual(escapeHtml(true), 'true');
    assert.strictEqual(escapeHtml(false), 'false');
    assert.strictEqual(escapeHtml(null), 'null');
  });

  test('escapes typical XSS payloads safely', () => {
    const payloads = [
      {
        input: '<img src="x" onerror="alert(1)">',
        expected: '&lt;img src=&quot;x&quot; onerror=&quot;alert(1)&quot;&gt;',
      },
      {
        input: '"><script>alert(document.cookie)</script>',
        expected: '&quot;&gt;&lt;script&gt;alert(document.cookie)&lt;/script&gt;',
      },
      {
        input: "javascript:alert('XSS')",
        expected: "javascript:alert(&#039;XSS&#039;)",
      },
    ];

    for (const { input, expected } of payloads) {
      assert.strictEqual(escapeHtml(input), expected);
    }
  });
});
