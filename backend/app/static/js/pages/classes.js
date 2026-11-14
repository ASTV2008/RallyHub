import { del, get, patch, post } from '../api.js';
import { LEVELS, badge, clear, confirmDialog, dataTable, dialog, fail, fmtRange, formModal, h, isoToLocalInput, localToIso, options, toast, fullName, label } from '../ui.js';

export async function render(box, { role, me }) {
  const staff = role !== 'STUDENT';
  const admin = role === 'ADMIN';
  const [coaches, tables] = staff ? await Promise.all([
    admin ? get('/coaches', { limit: 100, is_active: 'true' }) : { items: [] }, get('/tables', { limit: 100, status: 'ACTIVE' })]) : [{ items: [] }, { items: [] }];
  const myEnrollments = role === 'STUDENT' ? new Map((await get('/enrollments', { limit: 100, status_filter: 'ENROLLED' })).items.map((e) => [e.class_id, e])) : new Map();
  let t;
  const refresh = () => t.reload();
  const fields = (edit) => [
    { name: 'name', label: 'Nombre', required: true, maxlength: 120 },
    { name: 'description', label: 'Descripción', type: 'textarea', maxlength: 2000 },
    ...(admin && !edit ? [{ name: 'coach_id', label: 'Entrenador', type: 'select', required: true, asNumber: true, options: coaches.items.map((c) => ({ value: c.id, label: fullName(c) })) }] : []),
    { name: 'table_id', label: 'Mesa', type: 'select', asNumber: true, options: tables.items.map((x) => ({ value: x.id, label: `${x.code} · ${x.facility_name}` })), help: 'Opcional. Bloquea la mesa en ese horario.' },
    { name: 'level', label: 'Nivel', type: 'select', options: LEVELS, required: true },
    { name: 'capacity', label: 'Capacidad', type: 'number', min: 1, max: 100, required: true },
    { name: 'starts_at', label: 'Inicio', type: 'datetime-local', required: true },
    { name: 'ends_at', label: 'Fin', type: 'datetime-local', required: true },
  ];
  const toBody = (v, edit) => {
    const b = { ...v, starts_at: localToIso(v.starts_at), ends_at: localToIso(v.ends_at) };
    if (edit) { b.clear_table = v.table_id === null; }
    return b;
  };
  const roster = async (c) => {
    const body = h('div');
    const page = await get('/enrollments', { class_id: c.id, limit: 100, status_filter: 'ENROLLED' });
    body.append(page.items.length ? h('ul', { class: 'list' }, page.items.map((e) => h('li', {}, e.student_name))) : h('p', { class: 'muted' }, 'Aún no hay inscritos.'));
    dialog(`Inscritos · ${c.name}`, body);
  };
  const act = (fn, ok) => async () => { try { await fn(); toast(ok, 'ok'); refresh(); } catch (e) { fail(e); } };
  const columns = [
    { label: 'Clase', render: (c) => h('span', {}, h('strong', {}, c.name), h('br'), h('span', { class: 'muted' }, `${label(c.level)} · ${c.coach_name}`)) },
    { label: 'Horario', render: (c) => fmtRange(c.starts_at, c.ends_at) }, { label: 'Mesa', render: (c) => c.table_code ?? '—' },
    { label: 'Cupo', render: (c) => `${c.enrolled_count}/${c.capacity}` }, { label: 'Estado', render: (c) => badge(c.status) },
    { label: 'Acciones', render: (c) => {
      const future = new Date(c.ends_at) > new Date();
      if (!staff) {
        const enr = myEnrollments.get(c.id);
        if (!future || c.status !== 'PUBLISHED') return '—';
        return enr ? h('button', { class: 'btn sm danger', onclick: async () => { if (await confirmDialog(`¿Retirarte de "${c.name}"?`, { okLabel: 'Retirarme', danger: true })) { try { await del(`/enrollments/${enr.id}`); toast('Te retiraste de la clase.', 'ok'); myEnrollments.delete(c.id); refresh(); } catch (e) { fail(e); } } } }, 'Retirarme')
          : h('button', { class: 'btn primary sm', disabled: c.enrolled_count >= c.capacity, onclick: async () => { try { const e = await post('/enrollments', { class_id: c.id }); myEnrollments.set(c.id, e); toast('Inscripción confirmada.', 'ok'); refresh(); } catch (er) { fail(er); } } }, c.enrolled_count >= c.capacity ? 'Cupo lleno' : 'Inscribirme');
      }
      const mine = admin || c.coach_id === me.coach_id;
      return h('div', { class: 'actions' }, h('button', { class: 'btn sm', onclick: () => roster(c) }, 'Inscritos'),
        mine && future && c.status !== 'CANCELLED' ? [
          h('button', { class: 'btn sm', onclick: () => formModal({ title: `Editar ${c.name}`, fields: fields(true), wide: true,
            initial: { ...c, starts_at: isoToLocalInput(c.starts_at), ends_at: isoToLocalInput(c.ends_at) },
            onSubmit: async (v) => { await patch(`/classes/${c.id}`, toBody(v, true)); toast('Clase actualizada.', 'ok'); refresh(); } }) }, 'Editar'),
          c.status === 'DRAFT' ? h('button', { class: 'btn sm', onclick: act(() => post(`/classes/${c.id}/publish`), 'Clase publicada.') }, 'Publicar')
            : h('button', { class: 'btn sm', onclick: act(() => post(`/classes/${c.id}/unpublish`), 'Clase oculta (borrador).') }, 'Ocultar'),
          h('button', { class: 'btn sm danger', onclick: async () => { if (await confirmDialog(`¿Cancelar la clase "${c.name}"?`, { okLabel: 'Cancelar clase', danger: true })) act(() => post(`/classes/${c.id}/cancel`), 'Clase cancelada.')(); } }, 'Cancelar')] : null);
    } },
  ];
  t = dataTable({ columns, filters: staff ? [{ name: 'status_filter', label: 'Estado', options: options(['DRAFT', 'PUBLISHED', 'CANCELLED']) }, { name: 'level', label: 'Nivel', options: LEVELS }] : [{ name: 'level', label: 'Nivel', options: LEVELS }],
    load: (p) => get('/classes', { ...p, sort_by: 'starts_at' }), emptyText: 'No hay clases.' });
  box.append(staff ? h('div', { class: 'toolbar' }, h('button', { class: 'btn primary', onclick: () => formModal({ title: 'Nueva clase', fields: fields(false), wide: true, initial: { level: 'BEGINNER', capacity: 6 },
    onSubmit: async (v) => { await post('/classes', toBody(v, false)); toast('Clase creada como borrador. Publícala para abrir inscripciones.', 'ok'); refresh(); } }) }, '+ Nueva clase'))
    : h('p', { class: 'muted' }, 'Solo se muestran clases publicadas. El cupo y los duplicados los valida el servidor.'), t.el);
}
