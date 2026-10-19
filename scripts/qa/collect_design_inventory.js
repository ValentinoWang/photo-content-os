// Collect a rendered-page inventory for check_design_contract.py.
// Run inside the page (e.g. Playwright `page.evaluate(collect, options)`), then write the result as JSON.
// options.states: { "<state>": "<css selector of that state's root>" }; defaults to every [data-design-state].
// options.withIds: false for text-only checks on pages that do not carry design ids yet.
// Visible = rendered, not visually hidden (clip/1px/opacity 0), not aria-hidden; [data-design-data] text is data.
function collectDesignInventory(options = {}) {
  const roots = options.states
    ? Object.entries(options.states).map(([state, sel]) => [state, document.querySelector(sel)])
    : [...document.querySelectorAll('[data-design-state]')].map((el) => [el.dataset.designState, el]);
  const visible = (el) => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
      if (n.getAttribute('aria-hidden') === 'true' || n.hidden) return false;
      const r = n.getBoundingClientRect();
      if ((s.position === 'absolute' || s.position === 'fixed') && r.width <= 1 && r.height <= 1) return false;
      if (s.clipPath && s.clipPath.includes('inset(50%')) return false;
    }
    return true;
  };
  const idOf = (el) => el.closest('[data-design-id]')?.dataset.designId ?? null;
  const out = { states: {} };
  for (const [state, root] of roots) {
    if (!root) continue;
    const texts = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent.replace(/\s+/g, ' ').trim();
      const el = node.parentElement;
      if (!text || !el || ['SCRIPT', 'STYLE'].includes(el.tagName) || !visible(el)) continue;
      texts.push({ text, kind: 'text', data: !!el.closest('[data-design-data]'), design_id: idOf(el) });
    }
    for (const el of root.querySelectorAll('[placeholder],[title],[aria-label],img[alt]')) {
      if (!visible(el)) continue;
      for (const name of ['placeholder', 'title', 'aria-label', 'alt']) {
        const v = (el.getAttribute(name) || '').replace(/\s+/g, ' ').trim();
        if (v) texts.push({ text: v, kind: name, data: !!el.closest('[data-design-data]'), design_id: idOf(el) });
      }
    }
    const entry = { texts };
    if (options.withIds !== false) {
      entry.ids = [...new Set([...root.querySelectorAll('[data-design-id]')].filter(visible).map((e) => e.dataset.designId))].sort();
    }
    out.states[state] = entry;
  }
  return out;
}
if (typeof module !== 'undefined') module.exports = { collectDesignInventory };
