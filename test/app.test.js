const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { formatDate } = require('../app.js');

describe('formatDate', () => {
  describe('falsy and missing inputs', () => {
    it('returns "Recent" when value is undefined', () => {
      assert.equal(formatDate(undefined), 'Recent');
    });

    it('returns "Recent" when called with no arguments', () => {
      assert.equal(formatDate(), 'Recent');
    });

    it('returns "Recent" when value is null', () => {
      assert.equal(formatDate(null), 'Recent');
    });

    it('returns "Recent" when value is an empty string', () => {
      assert.equal(formatDate(''), 'Recent');
    });

    it('returns "Recent" when value is false', () => {
      assert.equal(formatDate(false), 'Recent');
    });

    it('returns "Recent" when value is 0', () => {
      assert.equal(formatDate(0), 'Recent');
    });
  });

  describe('invalid date values', () => {
    it('returns original string when value is an invalid date string', () => {
      assert.equal(formatDate('not-a-date'), 'not-a-date');
    });

    it('returns original input when value is an out-of-range date string', () => {
      assert.equal(formatDate('2023-99-99'), '2023-99-99');
    });
  });

  describe('valid date values', () => {
    it('formats valid ISO date string correctly', () => {
      const input = '2023-10-15T12:00:00Z';
      const expected = new Date(input).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
      assert.equal(formatDate(input), expected);
    });

    it('formats Date object correctly', () => {
      const dateObj = new Date('2024-01-01T00:00:00Z');
      const expected = dateObj.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
      assert.equal(formatDate(dateObj), expected);
    });

    it('formats numeric timestamp correctly', () => {
      const timestamp = 1700000000000;
      const expected = new Date(timestamp).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
      assert.equal(formatDate(timestamp), expected);
    });

    it('contains month, day, and year parts in output for a valid date', () => {
      const result = formatDate('2023-05-12T00:00:00Z');
      assert.match(result, /2023/);
      assert.match(result, /12|May/i);
    });
  });
});
