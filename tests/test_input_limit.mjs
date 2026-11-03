import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { anyOver, bindLimits, INPUT_LIMITS, overBy, syncLimit } from '../studio/static/input-limit.js';

class FakeClassList {
  values = new Set();
  add(value) { this.values.add(value); }
  remove(value) { this.values.delete(value); }
  contains(value) { return this.values.has(value); }
}

class FakeHint {
  attributes = new Map();
  className = '';
  textContent = '';
  setAttribute(name, value) { this.attributes.set(name, value); }
  matches(selector) { return selector === '.limit-hint' && this.className.split(/\s+/).includes('limit-hint'); }
  remove() { this.parent.field.nextElementSibling = null; }
}

class FakeField {
  constructor(value, limit) {
    this.value = value;
    this.dataset = { limit: String(limit) };
    this.classList = new FakeClassList();
    this.attributes = new Map();
    this.listeners = new Map();
    this.nextElementSibling = null;
  }
  addEventListener(name, listener) {
    const listeners = this.listeners.get(name) || [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }
  setAttribute(name, value) { this.attributes.set(name, value); }
  removeAttribute(name) { this.attributes.delete(name); }
  insertAdjacentElement(position, element) {
    assert.equal(position, 'afterend');
    element.parent = { field: this };
    this.nextElementSibling = element;
  }
  dispatch(name) { for (const listener of this.listeners.get(name) || []) listener(); }
}

class FakeRoot {
  constructor(fields) { this.fields = fields; }
  querySelectorAll(selector) {
    assert.equal(selector, '[data-limit]');
    return this.fields;
  }
}

globalThis.document = { createElement: tag => {
  assert.equal(tag, 'small');
  return new FakeHint();
} };

assert.equal(overBy('abc', 3), 0);
assert.equal(overBy('abcd', 3), 1);
assert.equal(overBy('😀a', 1), 1, 'counts Unicode code points, not UTF-16 units');
assert.equal(overBy('😀a', 2), 0);
assert.equal(overBy(`${'字'.repeat(INPUT_LIMITS.dialogue)}字`, INPUT_LIMITS.dialogue), 1);

const field = new FakeField('abcd', 3);
assert.equal(syncLimit(field), 1);
assert.equal(field.classList.contains('is-over'), true);
assert.equal(field.attributes.get('aria-invalid'), 'true');
assert.equal(field.nextElementSibling.textContent, '超出 1 字');
assert.equal(field.nextElementSibling.attributes.get('role'), 'alert');
assert.equal(syncLimit(field), 1);
assert.equal(field.nextElementSibling.textContent, '超出 1 字');
field.value = 'abc';
assert.equal(syncLimit(field), 0);
assert.equal(field.classList.contains('is-over'), false);
assert.equal(field.attributes.has('aria-invalid'), false);
assert.equal(field.nextElementSibling, null);

const rootField = new FakeField('abcd', 3);
const root = new FakeRoot([rootField]);
bindLimits(root);
bindLimits(root);
assert.equal(rootField.listeners.get('input').length, 1, 'repeated binding adds only one listener');
assert.equal(rootField.nextElementSibling.textContent, '超出 1 字');
assert.equal(anyOver(root), true);
rootField.value = 'abc';
rootField.dispatch('input');
assert.equal(anyOver(root), false);
assert.equal(rootField.nextElementSibling, null);

const contract = await readFile(new URL('../studio/api_contract.py', import.meta.url), 'utf8');
const contractLimits = Object.fromEntries(
  [...contract.matchAll(/'(script|dialogue|style|instruction)'\s*:\s*\{[^}]*?'maxLength'\s*:\s*(\d+)/gs)]
    .map(([, name, limit]) => [name, Number(limit)]),
);
assert.deepEqual(contractLimits, INPUT_LIMITS, 'front-end limits match API contract maxLength values');

console.log('input limits: 23 assertions passed');
