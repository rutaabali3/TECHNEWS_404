const fs = require('fs');
const path = require('path');

const articleId = process.argv[2];
if (!articleId) {
  console.error('No article_id provided');
  process.exit(1);
}

const filePath = path.join(__dirname, '..', 'data', 'likes.json');
let data = {};

try {
  if (fs.existsSync(filePath)) {
    const raw = fs.readFileSync(filePath, 'utf8');
    data = JSON.parse(raw);
  }
} catch (e) {
  data = {};
}

data[articleId] = (typeof data[articleId] === 'number' ? data[articleId] : 0) + 1;

fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');
console.log(`Updated likes for ${articleId}: ${data[articleId]}`);
