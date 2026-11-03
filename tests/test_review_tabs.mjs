import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../studio/static/review-view.js', import.meta.url), 'utf8');
const withoutImports = source.replace(/^import .*?;\s*$/gm, '');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(withoutImports).toString('base64')}`;
const { nextTabIndex } = await import(moduleUrl);

const cases = [
  [0, 'ArrowLeft', 3, 2],
  [2, 'ArrowRight', 3, 0],
  [1, 'ArrowLeft', 3, 0],
  [1, 'ArrowRight', 3, 2],
  [2, 'Home', 3, 0],
  [0, 'End', 3, 2],
  [0, 'Enter', 3, null],
  [0, 'ArrowLeft', 0, null],
];

for (const [current, key, count, expected] of cases) {
  assert.equal(nextTabIndex(current, key, count), expected, `${key} from ${current} of ${count}`);
}

assert.match(source, /tablist\.addEventListener\('keydown'/, 'keyboard handling stays on the tablist');
assert.match(source, /tabindex="\$\{tab===key\?'0':'-1'\}"/, 'only the selected tab is in the tab order');
assert.doesNotMatch(source, /aria-controls=/, 'tabs do not invent panel IDs');

const shotsSource = await readFile(new URL('../studio/static/review-shots.js', import.meta.url), 'utf8');
assert.match(shotsSource, /data-hero="\$\{n\}" aria-label="第 \$\{String\(n\+1\)\.padStart\(2,'0'\)\} 镜"/, 'thumbnail buttons have their spoken shot number');
assert.match(shotsSource, /data-hero="\$\{i\}" aria-label="第 \$\{String\(i\+1\)\.padStart\(2,'0'\)\} 镜"[^>]*><i><\/i><\/button>/, 'progress buttons have their spoken shot number');

console.log(`passed ${cases.length} review tab direction cases and 5 accessibility source checks`);
