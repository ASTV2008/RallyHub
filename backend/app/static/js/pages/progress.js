import { get, post } from '../api.js';
import { clear, errorBox, fail, formModal, fmtDate, fullName, h, todayLocal, toast } from '../ui.js';

const SKILLS = [['serve', 'Servicio'], ['receive', 'Devolución'], ['ball_control', 'Control de pelota'], ['movement', 'Desplazamiento'], ['strategy', 'Estrategia']];
const SCALE = '1 = en inicio · 2 = en desarrollo · 3 = funcional · 4 = sólido · 5 = sobresaliente (observación pedagógica del entrenador; no es una medición oficial).';

export async function render(box, { role, me }) {
  const area = h('div');
  let students = [];
  const load = async (sid) => {
    clear(area).append(h('div', { class: 'skeleton' }));
    try {
      const s = await get(`/progress/students/${sid}`);
      clear(area);
      if (!s.records.length) { area.append(h('p', { class: 'muted' }, 'Aún no hay observaciones de progreso para este estudiante.')); }
      else {
        const last = s.records[s.records.length - 1];
        area.append(h('section', { class: 'card' }, h('h2', {}, 'Última observación'),
          SKILLS.map(([k, n]) => h('div', { class: 'bar-row' }, h('span', {}, n), h('div', { class: 'bar blue', role: 'img', 'aria-label': `${n}: ${last[k]} de 5` },
            (() => { const b = h('span'); b.style.width = last[k] * 20 + '%'; return b; })()), h('span', {}, `${last[k]}/5`))),
          s.sufficient_data ? h('p', {}, `Promedio inicial ${s.first_average} → actual ${s.last_average} (${s.records.length} observaciones).`)
            : h('p', { class: 'muted' }, 'Con una sola observación no se muestra evolución: se necesitan al menos dos.')),
        h('h2', {}, 'Historial'), h('div', { class: 'table-wrap' }, h('table', { class: 'data' }, h('thead', {}, h('tr', {}, ['Fecha', ...SKILLS.map((x) => x[1]), 'Notas'].map((x) => h('th', { scope: 'col' }, x)))),
          h('tbody', {}, [...s.records].reverse().map((r) => h('tr', {}, h('td', {}, fmtDate(r.recorded_on)), SKILLS.map(([k]) => h('td', {}, r[k])), h('td', {}, r.notes ?? '—')))))));
      }
    } catch (e) { clear(area).append(errorBox(e)); }
  };
  if (role === 'STUDENT') { box.append(h('p', { class: 'muted' }, SCALE), area); await load(me.student_id); return; }
  students = (await get('/students', { limit: 100, is_active: 'true' })).items;
  const sel = h('select', { id: 'pg-s' }, h('option', { value: '' }, '— Elige un estudiante —'), students.map((s) => h('option', { value: s.id }, fullName(s))));
  sel.addEventListener('change', () => { if (sel.value) load(sel.value); else clear(area); newBtn.disabled = !sel.value; });
  const score = (k, n) => ({ name: k, label: `${n} (1–5)`, type: 'number', min: 1, max: 5, required: true });
  const newBtn = h('button', { class: 'btn primary', disabled: true, onclick: () => formModal({ title: 'Nueva observación', wide: true, fields: [
    { name: 'recorded_on', label: 'Fecha', type: 'date', required: true, max: todayLocal() }, ...SKILLS.map(([k, n]) => score(k, n)),
    { name: 'notes', label: 'Notas', type: 'textarea', maxlength: 500 }], initial: { recorded_on: todayLocal() },
  onSubmit: async (v) => { await post('/progress', { ...v, student_id: Number(sel.value) }); toast('Observación registrada.', 'ok'); load(sel.value); } }) }, '+ Registrar observación');
  box.append(h('p', { class: 'muted' }, SCALE), role === 'ADMIN' ? h('p', { class: 'muted' }, 'El administrador consulta; solo los entrenadores registran observaciones.') : null,
    h('div', { class: 'toolbar' }, h('div', { class: 'field' }, h('label', { for: 'pg-s' }, 'Estudiante'), sel), role === 'COACH' ? newBtn : null), area);
}
