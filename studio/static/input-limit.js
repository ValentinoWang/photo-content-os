export const INPUT_LIMITS = Object.freeze({
  script: 20000,
  dialogue: 2000,
  style: 4000,
  instruction: 200,
});

const boundFields = new WeakSet();

export function overBy(value, limit) {
  return Math.max(0, [...value].length - limit);
}

export function syncLimit(field) {
  const limit = Number(field.dataset.limit);
  const excess = overBy(field.value, limit);
  let hint = field.nextElementSibling;
  if (!hint?.matches?.('.limit-hint')) hint = null;

  if (excess > 0) {
    field.classList.add('is-over');
    field.setAttribute('aria-invalid', 'true');
    if (!hint) {
      hint = document.createElement('small');
      hint.className = 'limit-hint';
      hint.setAttribute('role', 'alert');
      field.insertAdjacentElement('afterend', hint);
    }
    hint.textContent = `超出 ${excess} 字`;
  } else {
    field.classList.remove('is-over');
    field.removeAttribute('aria-invalid');
    hint?.remove();
  }

  return excess;
}

export function bindLimits(root) {
  root.querySelectorAll('[data-limit]').forEach(field => {
    if (!boundFields.has(field)) {
      field.addEventListener('input', () => syncLimit(field));
      boundFields.add(field);
    }
    syncLimit(field);
  });
}

export function anyOver(root) {
  return [...root.querySelectorAll('[data-limit]')]
    .some(field => overBy(field.value, Number(field.dataset.limit)) > 0);
}
