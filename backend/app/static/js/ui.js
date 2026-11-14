// Utilidades de interfaz. Todo texto de usuario se inserta como nodo de texto (nunca innerHTML).
import { ApiError } from './api.js';

export const TZ = 'America/Bogota';

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'text') el.textContent = v;
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

export const clear = (el) => { el.replaceChildren(); return el; };

// ---- formato de fechas (siempre en la zona del club; el servidor responde en UTC) -----------------
export function fmtDateTime(iso) {
  if (!iso) return '—';
  return new Intl.DateTimeFormat('es-CO', { timeZone: TZ, dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso));
}
export function fmtDate(v) {
  if (!v) return '—';
  const d = /^\d{4}-\d{2}-\d{2}$/.test(v) ? new Date(v + 'T12:00:00Z') : new Date(v);
  return new Intl.DateTimeFormat('es-CO', { timeZone: v.length === 10 ? 'UTC' : TZ, dateStyle: 'medium' }).format(d);
}
export function fmtRange(a, b) {
  const t = new Intl.DateTimeFormat('es-CO', { timeZone: TZ, timeStyle: 'short' });
  return `${fmtDateTime(a)} – ${t.format(new Date(b))}`;
}

/** 'YYYY-MM-DDTHH:mm' (hora local del club) -> ISO UTC. Cálculo del desplazamiento con Intl (sin DST fijo). */
export function localToIso(value, tz = TZ) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value || '');
  if (!m) return null;
  const [y, mo, d, hh, mi] = m.slice(1).map(Number);
  const asUtc = Date.UTC(y, mo - 1, d, hh, mi);
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit' }).formatToParts(new Date(asUtc));
  const g = (t) => Number(parts.find((p) => p.type === t).value);
  const shown = Date.UTC(g('year'), g('month') - 1, g('day'), g('hour'), g('minute'));
  return new Date(asUtc - (shown - asUtc)).toISOString();
}
export function isoToLocalInput(iso, tz = TZ) {
  if (!iso) return '';
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit' }).formatToParts(new Date(iso));
  const g = (t) => parts.find((p) => p.type === t).value;
  return `${g('year')}-${g('month')}-${g('day')}T${g('hour')}:${g('minute')}`;
}
export function todayLocal() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date());
}

// ---- etiquetas ---------------------------------------------------------------------------------
const LABELS = {
  ADMIN: 'Administrador', COACH: 'Entrenador', STUDENT: 'Estudiante',
  BEGINNER: 'Principiante', INTERMEDIATE: 'Intermedio', ADVANCED: 'Avanzado',
  ACTIVE: 'Activa', MAINTENANCE: 'En mantenimiento', OUT_OF_SERVICE: 'Fuera de servicio',
  CONFIRMED: 'Confirmada', CANCELLED: 'Cancelada', COMPLETED: 'Completada', NO_SHOW: 'No asistió',
  DRAFT: 'Borrador', PUBLISHED: 'Publicada', ENROLLED: 'Inscrito', WITHDRAWN: 'Retirado',
  PRESENT: 'Presente', ABSENT: 'Ausente', JUSTIFIED: 'Justificada',
  OPEN: 'Abierto', IN_PROGRESS: 'En curso', FINISHED: 'Finalizado', SINGLES: 'Individual',
};
export const label = (v) => LABELS[v] ?? v;
const TONE = { ACTIVE: 'ok', CONFIRMED: 'ok', PUBLISHED: 'ok', PRESENT: 'ok', COMPLETED: 'ok', OPEN: 'ok', ENROLLED: 'ok',
  CANCELLED: 'err', OUT_OF_SERVICE: 'err', ABSENT: 'err', NO_SHOW: 'err', WITHDRAWN: 'err',
  MAINTENANCE: 'warn', DRAFT: 'warn', JUSTIFIED: 'warn', IN_PROGRESS: 'warn' };
export const badge = (v) => h('span', { class: 'badge ' + (TONE[v] ?? '') }, label(v));
export const yesNo = (b) => h('span', { class: 'badge ' + (b ? 'ok' : 'err') }, b ? 'Activo' : 'Inactivo');
export const options = (values) => values.map((v) => ({ value: v, label: label(v) }));
export const LEVELS = options(['BEGINNER', 'INTERMEDIATE', 'ADVANCED']);

// ---- toasts ------------------------------------------------------------------------------------
export function toast(msg, type = 'info') {
  const box = document.getElementById('toasts');
  const t = h('div', { class: 'toast ' + type, role: type === 'err' ? 'alert' : 'status' }, msg);
  box.append(t);
  setTimeout(() => t.remove(), type === 'err' ? 7000 : 4000);
}
/** Error con mensaje apto para mostrar al usuario (validaciones locales, acciones canceladas). */
export class UserError extends Error {}
export const errMsg = (e) => {
  if (e instanceof ApiError) {
    const details = e.errors
      ?.map((item) => `${item.field}: ${item.message}`)
      .join(' | ');

    return details
      ? `${e.message} (${details})`
      : e.message;
  }

  return e instanceof UserError
    ? e.message
    : 'Ocurrió un error inesperado.';
};
export const fail = (e) => toast(errMsg(e), 'err');

// ---- diálogos accesibles (<dialog> nativo: foco atrapado, Esc cierra) --------------------------------
export function dialog(title, body, { footer, wide = false, onClose } = {}) {
  const dlg = h('dialog', { class: wide ? 'wide' : '', 'aria-labelledby': 'dlg-title' });
  const close = () => dlg.close();
  dlg.append(
    h('div', { class: 'dlg-head' }, h('h2', { id: 'dlg-title' }, title),
      h('button', { type: 'button', 'aria-label': 'Cerrar', onclick: close }, '×')),
    h('div', { class: 'dlg-body' }, body),
    footer ? h('div', { class: 'dlg-foot' }, footer) : null,
  );
  dlg.addEventListener('close', () => { dlg.remove(); onClose?.(); });
  document.body.append(dlg);
  dlg.showModal();
  return { el: dlg, close };
}

export function confirmDialog(message, { okLabel = 'Confirmar', danger = false } = {}) {
  return new Promise((resolve) => {
    let answer = false;
    const ok = h('button', { class: 'btn ' + (danger ? 'danger' : 'primary'), type: 'button',
      onclick: () => { answer = true; d.close(); } }, okLabel);
    const cancel = h('button', { class: 'btn', type: 'button', onclick: () => d.close() }, 'Cancelar');
    const d = dialog('Confirmar acción', h('p', {}, message), { footer: [cancel, ok], onClose: () => resolve(answer) });
    cancel.focus();
  });
}

/** Formulario modal. fields: {name,label,type,required,options,help,min,max,step,maxlength,rows,value}. */
export function formModal({ title, fields, initial = {}, submitLabel = 'Guardar', onSubmit, wide = false }) {
  const form = h('form', { novalidate: true });
  const alertBox = h('div', { role: 'alert' });
  const inputs = {};
  const errBoxes = {};
  for (const f of fields) {
    const id = 'f-' + f.name;
    const val = initial[f.name] ?? f.value ?? '';
    let input;
    if (f.type === 'select') {
      input = h('select', { id, name: f.name }, (f.required ? [] : [h('option', { value: '' }, '— Ninguno —')]),
        f.options.map((o) => h('option', { value: o.value }, o.label)));
      input.value = String(val);
      if (f.required && !input.value && f.options.length) input.value = String(f.options[0].value);
    } else if (f.type === 'textarea') {
      input = h('textarea', { id, name: f.name, rows: f.rows ?? 3, maxlength: f.maxlength }, val);
    } else if (f.type === 'checkbox') {
      input = h('input', { id, name: f.name, type: 'checkbox' });
      input.checked = Boolean(val);
    } else {
      input = h('input', { id, name: f.name, type: f.type ?? 'text', min: f.min, max: f.max, step: f.step,
        maxlength: f.maxlength, autocomplete: f.autocomplete ?? 'off' });
      input.value = val;
    }
    if (f.required) input.setAttribute('aria-required', 'true');
    if (f.disabled) input.disabled = true;
    const err = h('div', { class: 'err', id: id + '-err' });
    input.setAttribute('aria-describedby', id + '-err');
    inputs[f.name] = input; errBoxes[f.name] = err;
    form.append(h('div', { class: 'field' },
      f.type === 'checkbox' ? h('label', {}, input, ' ', f.label) : [h('label', { for: id }, f.label + (f.required ? ' *' : '')), input],
      f.help ? h('div', { class: 'help' }, f.help) : null, err));
  }
  const values = () => {
    const out = {};
    for (const f of fields) {
      const el = inputs[f.name];
      if (f.type === 'checkbox') out[f.name] = el.checked;
      else if (el.value === '') out[f.name] = null;
      else if (f.type === 'number' || f.asNumber) out[f.name] = Number(el.value);
      else out[f.name] = el.value;
    }
    return out;
  };
  const submit = h('button', { class: 'btn primary', type: 'submit' }, submitLabel);
  const d = dialog(title, [alertBox, form], {
    wide, footer: [h('button', { class: 'btn', type: 'button', onclick: () => d.close() }, 'Cancelar'), submit],
  });
  submit.setAttribute('form', 'f-form'); form.id = 'f-form';
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    clear(alertBox);
    Object.values(errBoxes).forEach((b) => { b.textContent = ''; });
    for (const f of fields) {   // validación de cliente: solo ayuda; el servidor es la fuente de verdad
      const el = inputs[f.name];
      if (f.required && f.type !== 'checkbox' && el.value === '') { errBoxes[f.name].textContent = 'Campo obligatorio.'; el.focus(); return; }
    }
    submit.disabled = true;
    try {
      await onSubmit(values());
      d.close();
    } catch (e) {
      if (e instanceof ApiError && e.errors?.length) {
        for (const er of e.errors) {
          const box = errBoxes[er.field.split('.').pop()];
          if (box) box.textContent = er.message; else alertBox.append(h('div', { class: 'alert err' }, er.message));
        }
      } else alertBox.append(h('div', { class: 'alert err' }, errMsg(e)));
    } finally { submit.disabled = false; }
  });
  inputs[fields[0].name]?.focus();
  return d;
}

// ---- tabla de datos con búsqueda, filtros y paginación ---------------------------------------------
export function dataTable({ columns, load, filters = [], search = false, pageSize = 10, emptyText = 'No hay registros.' }) {
  const state = { offset: 0, q: '', f: {} };
  const root = h('div');
  const body = h('tbody');
  const pager = h('div', { class: 'pager' });
  const status = h('div', { role: 'status' });
  const tools = h('div', { class: 'toolbar' });
  let timer;
  if (search) {
    const s = h('input', { type: 'search', id: 'dt-q', placeholder: 'Buscar…', 'aria-label': 'Buscar' });
    s.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => { state.q = s.value.trim(); state.offset = 0; reload(); }, 300); });
    tools.append(h('div', { class: 'field' }, h('label', { for: 'dt-q' }, 'Buscar'), s));
  }
  for (const f of filters) {
    const id = 'dt-' + f.name;
    const sel = h('select', { id }, h('option', { value: '' }, 'Todos'), f.options.map((o) => h('option', { value: o.value }, o.label)));
    sel.addEventListener('change', () => { state.f[f.name] = sel.value; state.offset = 0; reload(); });
    tools.append(h('div', { class: 'field' }, h('label', { for: id }, f.label), sel));
  }
  const table = h('table', { class: 'data' },
    h('thead', {}, h('tr', {}, columns.map((c) => h('th', { scope: 'col' }, c.label)))), body);
  root.append(tools, status, h('div', { class: 'table-wrap' }, table), pager);

  async function reload() {
    clear(status).append(h('div', { class: 'skeleton' }));
    try {
      const page = await load({ limit: pageSize, offset: state.offset, q: state.q, ...state.f });
      clear(status); clear(body);
      if (!page.items.length) {
        status.append(h('div', { class: 'empty' }, emptyText));
      }
      for (const row of page.items) {
        body.append(h('tr', {}, columns.map((c) => h('td', {}, c.render ? c.render(row) : (row[c.key] ?? '—')))));
      }
      clear(pager);
      const from = page.total ? state.offset + 1 : 0, to = state.offset + page.items.length;
      pager.append(h('span', {}, `${from}–${to} de ${page.total}`), h('span', { class: 'spacer' }),
        h('button', { class: 'btn sm', disabled: state.offset === 0, onclick: () => { state.offset = Math.max(0, state.offset - pageSize); reload(); } }, '← Anterior'),
        h('button', { class: 'btn sm', disabled: to >= page.total, onclick: () => { state.offset += pageSize; reload(); } }, 'Siguiente →'));
    } catch (e) {
      clear(status).append(h('div', { class: 'error-box' }, errMsg(e), ' ', h('button', { class: 'btn sm', onclick: reload }, 'Reintentar')));
    }
  }
  reload();
  return { el: root, reload };
}

export const skeleton = () => h('div', {}, h('div', { class: 'skeleton' }), h('div', { class: 'skeleton' }), h('div', { class: 'skeleton' }));
export const errorBox = (e, retry) => h('div', { class: 'error-box' }, errMsg(e), ' ', retry ? h('button', { class: 'btn sm', onclick: retry }, 'Reintentar') : null);
export const fullName = (o) => `${o.first_name} ${o.last_name}`;
