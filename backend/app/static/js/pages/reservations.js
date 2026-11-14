import { get, post, patch } from '../api.js';
import { badge, clear, confirmDialog, dataTable, fail, fmtRange, fullName, h, localToIso, options, toast, todayLocal } from '../ui.js';

export async function render(box, { role, me }) {
  const policy = await get('/reservations/policy');
  const admin = role === 'ADMIN';
  const canBook = role !== 'COACH';
  const tabs = h('div', { class: 'tabs', role: 'tablist' });
  const panel = h('div');
  const views = { list: renderList };
  if (canBook) views.book = renderBook;
  const names = { book: 'Nueva reserva', list: role === 'STUDENT' ? 'Mis reservas' : 'Listado' };
  const show = (k) => {
    [...tabs.children].forEach((b) => b.setAttribute('aria-selected', String(b.dataset.k === k)));
    clear(panel); views[k](panel);
  };
  for (const k of Object.keys(views).sort((a) => (a === 'book' ? -1 : 1))) {
    tabs.append(h('button', { role: 'tab', 'data-k': k, onclick: () => show(k) }, names[k]));
  }
  box.append(tabs, panel);
  show(canBook ? 'book' : 'list');

  function policyBox() {
    return h('aside', { class: 'card policy' }, h('strong', {}, 'Política de reservas'), h('ul', {},
      h('li', {}, `Horario: ${policy.opening_time}–${policy.closing_time} (${policy.timezone}).`),
      h('li', {}, `Duración: entre ${policy.min_minutes} y ${policy.max_minutes} minutos, en bloques de 15 min.`),
      h('li', {}, `Antelación máxima: ${policy.max_advance_days} días. No se reserva en el pasado.`),
      h('li', {}, `Los estudiantes pueden cancelar hasta ${policy.cancel_min_hours_before} horas antes del inicio.`),
      h('li', {}, 'Una mesa no puede tener dos reservas solapadas; las consecutivas sí.')));
  }

  async function renderBook(p) {
    const students = admin ? (await get('/students', { limit: 100, is_active: 'true' })).items : [];
    const date = h('input', { type: 'date', id: 'rb-d', value: todayLocal(), min: todayLocal() });
    const from = h('input', { type: 'time', id: 'rb-f', value: '16:00', step: 900 });
    const to = h('input', { type: 'time', id: 'rb-t', value: '17:00', step: 900 });
    const who = admin ? h('select', { id: 'rb-s' }, students.map((s) => h('option', { value: s.id }, fullName(s)))) : null;
    const results = h('div', { class: 'avail', 'aria-live': 'polite' });
    const msg = h('div', { role: 'alert' });
    const search = async (ev) => {
      ev?.preventDefault(); clear(msg); clear(results);
      const s = localToIso(`${date.value}T${from.value}`), e = localToIso(`${date.value}T${to.value}`);
      if (!s || !e) { msg.append(h('div', { class: 'alert err' }, 'Completa fecha y horas.')); return; }
      if (new Date(e) <= new Date(s)) { msg.append(h('div', { class: 'alert err' }, 'La hora final debe ser posterior a la inicial.')); return; }
      try {
        const tables = await get('/tables/availability', { starts_at: s, ends_at: e });
        if (!tables.length) results.append(h('p', { class: 'muted' }, 'No hay mesas registradas.'));
        for (const t of tables) {
          results.append(h('div', { class: 'card' + (t.available ? '' : ' busy') }, h('strong', {}, `Mesa ${t.code}`), h('br'),
            h('span', { class: 'muted' }, t.facility_name), h('br'),
            t.available ? [h('span', { class: 'badge ok' }, 'Disponible'), h('br'), h('button', { class: 'btn primary sm', onclick: () => book(t, s, e) }, 'Reservar')]
              : [h('span', { class: 'badge err' }, 'No disponible'), h('br'), h('span', { class: 'muted' }, t.reason ?? 'Ocupada en ese horario')]));
        }
      } catch (er) { fail(er); }
    };
    const book = async (t, s, e) => {
      if (!(await confirmDialog(`¿Reservar la mesa ${t.code} (${t.facility_name}) el ${fmtRange(s, e)}?`, { okLabel: 'Reservar' }))) return;
      try {
        await post('/reservations', { table_id: t.id, starts_at: s, ends_at: e, ...(admin ? { student_id: Number(who.value) } : {}) });
        toast('Reserva confirmada.', 'ok'); search();
      } catch (er) { fail(er); if (er.status === 409) search(); }
    };
    p.append(h('div', { class: 'grid two' }, h('form', { class: 'card', onsubmit: search },
      h('h2', {}, 'Consultar disponibilidad'),
      admin ? h('div', { class: 'field' }, h('label', { for: 'rb-s' }, 'Reservar para'), who) : null,
      h('div', { class: 'field' }, h('label', { for: 'rb-d' }, 'Fecha'), date),
      h('div', { class: 'field' }, h('label', { for: 'rb-f' }, 'Desde'), from),
      h('div', { class: 'field' }, h('label', { for: 'rb-t' }, 'Hasta'), to),
      h('button', { class: 'btn primary', type: 'submit' }, 'Buscar mesas libres')), policyBox()), msg, h('h2', {}, 'Resultados'), results);
  }

  const canStudentCancel = (r) => new Date(r.starts_at).getTime() - Date.now() >= policy.cancel_min_hours_before * 3600 * 1000;

  function renderList(p) {
    let t;
    const act = async (fn, ok) => { try { await fn(); toast(ok, 'ok'); t.reload(); } catch (e) { fail(e); } };
    const columns = [
      { label: 'Mesa', render: (r) => `${r.table_code} · ${r.facility_name}` },
      ...(role !== 'STUDENT' ? [{ label: 'Estudiante', key: 'student_name' }] : []),
      { label: 'Horario', render: (r) => fmtRange(r.starts_at, r.ends_at) }, { label: 'Estado', render: (r) => badge(r.status) },
      { label: 'Acciones', render: (r) => h('div', { class: 'actions' },
        role === 'STUDENT' && r.status === 'CONFIRMED' && !canStudentCancel(r) ? h('span', { class: 'muted' }, `Cancelación cerrada (menos de ${policy.cancel_min_hours_before} h)`) : null,
        (admin || (role === 'STUDENT' && canStudentCancel(r))) && r.status === 'CONFIRMED' ? h('button', { class: 'btn sm danger', onclick: async () => {
          if (await confirmDialog(`¿Cancelar la reserva de la mesa ${r.table_code}?`, { okLabel: 'Cancelar reserva', danger: true })) act(() => post(`/reservations/${r.id}/cancel`), 'Reserva cancelada.'); } }, 'Cancelar') : null,
        admin && r.status === 'CONFIRMED' && new Date(r.starts_at) < new Date() ? [
          h('button', { class: 'btn sm', onclick: () => act(() => patch(`/reservations/${r.id}/status`, { status: 'COMPLETED' }), 'Marcada como completada.') }, 'Completada'),
          h('button', { class: 'btn sm', onclick: () => act(() => patch(`/reservations/${r.id}/status`, { status: 'NO_SHOW' }), 'Marcada como no asistió.') }, 'No asistió')] : null) },
    ];
    t = dataTable({ columns, filters: [{ name: 'status_filter', label: 'Estado', options: options(['CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW']) }],
      load: (q) => get('/reservations', { ...q, sort_by: 'starts_at', order: 'desc' }), emptyText: 'No hay reservas.' });
    p.append(role === 'COACH' ? h('p', { class: 'muted' }, 'Se muestran las reservas de tus estudiantes.') : null,
      admin ? h('div', { class: 'toolbar' }, h('a', { class: 'btn', href: '/api/v1/reservations/export.csv', download: 'reservas.csv' }, 'Exportar CSV')) : null, t.el, policyBox());
  }
}
