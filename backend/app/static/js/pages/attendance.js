import { get, patch, post } from '../api.js';
import { badge, clear, dataTable, fail, fmtDateTime, fmtRange, h, options, toast } from '../ui.js';

const STATES = options(['PRESENT', 'ABSENT', 'JUSTIFIED']);

export async function render(box, { role }) {
  if (role === 'STUDENT') {
    box.append(h('p', { class: 'muted' }, 'Tu historial de asistencia registrado por los entrenadores.'),
      dataTable({ columns: [{ label: 'Clase', render: (a) => `Clase #${a.class_id}` }, { label: 'Estado', render: (a) => badge(a.status) },
        { label: 'Observación', key: 'notes' }, { label: 'Registrada', render: (a) => fmtDateTime(a.recorded_at) }],
      load: (p) => get('/attendances', p), emptyText: 'Aún no tienes asistencias registradas.' }).el);
    return;
  }
  const now = new Date().toISOString();
  const classes = (await get('/classes', { limit: 100, status_filter: 'PUBLISHED', date_to: now, sort_by: 'starts_at', order: 'desc' })).items;
  const sel = h('select', { id: 'at-c' }, h('option', { value: '' }, '— Elige una clase ya iniciada —'),
    classes.map((c) => h('option', { value: c.id }, `${c.name} · ${fmtRange(c.starts_at, c.ends_at)}`)));
  const area = h('div');
  sel.addEventListener('change', async () => {
    clear(area);
    if (!sel.value) return;
    try {
      const [enr, att] = await Promise.all([get('/enrollments', { class_id: sel.value, limit: 100, status_filter: 'ENROLLED' }), get('/attendances', { class_id: sel.value, limit: 100 })]);
      const byEnr = new Map(att.items.map((a) => [a.enrollment_id, a]));
      if (!enr.items.length) { area.append(h('p', { class: 'muted' }, 'La clase no tiene inscritos.')); return; }
      area.append(h('div', { class: 'table-wrap' }, h('table', { class: 'data' }, h('thead', {}, h('tr', {}, ['Estudiante', 'Estado', 'Observación', ''].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', {}, enr.items.map((e) => {
          const cur = byEnr.get(e.id);
          const st = h('select', { 'aria-label': `Estado de ${e.student_name}` }, cur ? null : h('option', { value: '' }, '— Sin registrar —'), STATES.map((o) => h('option', { value: o.value }, o.label)));
          st.value = cur?.status ?? '';
          const nt = h('input', { 'aria-label': `Observación de ${e.student_name}`, maxlength: 300, value: cur?.notes ?? '' });
          const save = h('button', { class: 'btn sm primary', onclick: async () => {
            if (!st.value) { toast('Elige un estado.', 'err'); return; }
            try {
              const saved = cur ? await patch(`/attendances/${cur.id}`, { status: st.value, notes: nt.value || null }) : await post('/attendances', { enrollment_id: e.id, status: st.value, notes: nt.value || null });
              byEnr.set(e.id, saved); toast(cur ? 'Asistencia corregida.' : 'Asistencia registrada.', 'ok'); sel.dispatchEvent(new Event('change'));
            } catch (er) { fail(er); } } }, cur ? 'Corregir' : 'Registrar');
          return h('tr', {}, h('td', {}, e.student_name), h('td', {}, st), h('td', {}, nt), h('td', {}, save));
        })))));
    } catch (e) { fail(e); }
  });
  box.append(h('p', { class: 'muted' }, 'Solo se registra asistencia en clases ya iniciadas. Cada estudiante tiene un único registro por clase; puede corregirse (queda en auditoría).'),
    h('div', { class: 'field' }, h('label', { for: 'at-c' }, 'Clase'), sel), area);
}
