import { get } from '../api.js';
import { h, fmtRange, fmtDateTime, badge, label, errorBox } from '../ui.js';

const stat = (n, l) => h('div', { class: 'card stat' }, h('div', { class: 'n' }, n ?? '—'), h('div', { class: 'l' }, l));
const pct = (v) => (v === null || v === undefined ? 'Sin datos' : `${v}%`);

function classList(items, empty) {
  if (!items.length) return h('p', { class: 'muted' }, empty);
  return h('ul', { class: 'list' }, items.map((c) => h('li', {},
    h('strong', {}, c.name), ' ', badge(c.status), h('br'),
    h('span', { class: 'muted' }, `${fmtRange(c.starts_at, c.ends_at)} · ${c.coach_name}${c.table_code ? ' · Mesa ' + c.table_code : ''} · ${c.enrolled_count}/${c.capacity} inscritos`))));
}

function bars(rows, { blue = false } = {}) {
  return rows.map(({ name, value, text }) => h('div', { class: 'bar-row' }, h('span', {}, name),
    h('div', { class: 'bar' + (blue ? ' blue' : ''), role: 'img', 'aria-label': `${name}: ${text}` },
      (() => { const s = h('span'); s.style.width = Math.min(100, value) + '%'; return s; })()),
    h('span', {}, text)));
}

export async function render(box, { role }) {
  const key = role.toLowerCase();
  let d;
  try { d = await get(`/dashboard/${key}`); } catch (e) { box.append(errorBox(e)); return; }
  const foot = h('p', { class: 'muted' }, `Datos calculados en vivo: ${fmtDateTime(d.generated_at)}.`);
  if (role === 'ADMIN') {
    const lv = Object.entries(d.students_by_level);
    const total = lv.reduce((a, [, n]) => a + n, 0) || 1;
    box.append(
      h('div', { class: 'grid stats' }, stat(d.active_students, 'Estudiantes activos'), stat(d.active_coaches, 'Entrenadores activos'),
        stat(d.enabled_tables, 'Mesas habilitadas'), stat(d.reservations_today, 'Reservas hoy'),
        stat(d.reservations_week, 'Reservas esta semana'), stat(pct(d.attendance_rate_pct), `Asistencia (${d.attendance_period_days} d)`)),
      h('div', { class: 'grid two' },
        h('section', { class: 'card' }, h('h2', {}, 'Ocupación por mesa'),
          h('p', { class: 'muted' }, `Minutos con reserva o clase / minutos de operación, últimos ${d.occupancy_period_days} días.`),
          d.occupancy_by_table.length ? bars(d.occupancy_by_table.map((o) => ({ name: o.code, value: o.occupancy_pct, text: o.occupancy_pct + '%' }))) : h('p', { class: 'muted' }, 'No hay mesas activas.')),
        h('section', { class: 'card' }, h('h2', {}, 'Estudiantes por nivel'),
          lv.length ? bars(lv.map(([k, n]) => ({ name: label(k), value: (n / total) * 100, text: String(n) })), { blue: true }) : h('p', { class: 'muted' }, 'Sin estudiantes activos.'))),
      h('section', { class: 'card' }, h('h2', {}, 'Próximas clases'), classList(d.upcoming_classes, 'No hay clases próximas.')), foot);
  } else if (role === 'COACH') {
    box.append(h('div', { class: 'grid stats' }, stat(d.active_students, 'Mis estudiantes activos'),
      stat(pct(d.attendance_rate_pct), `Asistencia en mis clases (${d.attendance_period_days} d)`)),
    h('section', { class: 'card' }, h('h2', {}, 'Mis próximas clases'), classList(d.upcoming_classes, 'No tienes clases próximas.')), foot);
  } else {
    box.append(h('div', { class: 'grid stats' }, stat(d.upcoming_reservations.length, 'Reservas próximas'),
      stat(pct(d.attendance_rate_pct), `Mi asistencia (${d.attendance_period_days} d)`)),
    h('div', { class: 'grid two' },
      h('section', { class: 'card' }, h('h2', {}, 'Mis reservas próximas'),
        d.upcoming_reservations.length ? h('ul', { class: 'list' }, d.upcoming_reservations.map((r) => h('li', {},
          h('strong', {}, `Mesa ${r.table_code}`), ` · ${r.facility_name}`, h('br'), h('span', { class: 'muted' }, fmtRange(r.starts_at, r.ends_at))))) : h('p', { class: 'muted' }, 'No tienes reservas próximas.'),
        h('a', { class: 'btn primary', href: '#/reservations' }, 'Reservar una mesa')),
      h('section', { class: 'card' }, h('h2', {}, 'Mis próximas clases'), classList(d.upcoming_classes, 'No estás inscrito en clases próximas.'),
        h('a', { class: 'btn', href: '#/classes' }, 'Ver clases'))), foot);
  }
}
