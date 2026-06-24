const fs = require('fs');
const path = require('path');

// 简单加密
function xor(str, key) {
  let res = [];
  for (let i = 0; i < str.length; i++) {
    res.push(str.charCodeAt(i) ^ key.charCodeAt(i % key.length));
  }
  return String.fromCharCode.apply(null, res);
}
function encode(data, key) {
  return Buffer.from(xor(JSON.stringify(data), key), 'utf8').toString('base64');
}
function decode(str, key) {
  try {
    return JSON.parse(xor(Buffer.from(str, 'base64').toString('utf8'), key));
  } catch { return []; }
}

const DATA_FILE = path.join(__dirname, 'data', 'moods.json');
const LOG_FILE = path.join(__dirname, 'data', 'actions.log');
const PASSWORD = process.env.MOOD_PASSWORD || 'test_123_for_mood';

function ensureDir(p) {
  const dir = path.dirname(p);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function load() {
  ensureDir(DATA_FILE);
  if (!fs.existsSync(DATA_FILE)) {
    return [];
  }
  const raw = fs.readFileSync(DATA_FILE, 'utf8').trim();
  if (!raw) return [];
  return decode(raw, PASSWORD);
}

function save(moods) {
  ensureDir(DATA_FILE);
  fs.writeFileSync(DATA_FILE, encode(moods, PASSWORD), 'utf8');
}

function log(msg) {
  ensureDir(LOG_FILE);
  const time = new Date().toISOString();
  const line = `${time} - ${msg}\n`;
  fs.appendFileSync(LOG_FILE, line, 'utf8');
  console.log(line);
}

// 解析事件参数（通过环境变量）
const args = process.argv.slice(2);
const action = args[0] || 'noop';

if (action === 'send') {
  const text = process.env.MOOD_TEXT || '';
  const tag = process.env.MOOD_TAG || '😊';
  if (!text) {
    console.error('MOOD_TEXT is required');
    process.exit(1);
  }
  const moods = load();
  moods.unshift({
    id: Date.now().toString(36) + Math.random().toString(36).slice(2),
    t: new Date().toISOString(),
    text,
    tag
  });
  save(moods);
  log(`send: added mood with tag ${tag}`);
  console.log('Send done');
} else if (action === 'undo') {
  const moods = load();
  if (moods.length === 0) {
    log('undo: no data');
    console.log('No data to undo');
    process.exit(0);
  }
  const first = moods[0];
  const elapsed = Date.now() - new Date(first.t).getTime();
  if (elapsed > 24 * 60 * 60 * 1000) {
    log('undo: expired');
    console.log('Cannot undo: expired');
    process.exit(1);
  }
  moods.shift();
  save(moods);
  log('undo: removed latest');
  console.log('Undo done');
} else {
  console.log('Usage: node sync-data.js [send|undo]');
  console.log('Environment: MOOD_TEXT, MOOD_TAG, MOOD_PASSWORD');
}
