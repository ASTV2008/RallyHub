import { api, get, post } from '../api.js';
import { UserError, confirmDialog, dataTable, fail, formModal, h, toast, yesNo } from '../ui.js';

/** Reintenta cancelando reservas futuras si el servidor lo advierte y el admin confirma. */
async function withRelease(fn, question) {
  try { return await fn(false); } catch (e) {
    if (e.code !== 'has_future_reservations') throw e;
    if (!(await confirmDialog(`${e.message} ${question}`, { okLabel: 'Cancelar reservas y continuar', danger: true }))) throw new UserError('No se realizó ningún cambio.');
    return fn(true);
  }
}
const cancelParam = (cancel) => (cancel ? { cancel_reservations: 'true' } : undefined);

const fields = (edit) => [
  { name: 'name', label: 'Nombre', required: true, maxlength: 120 },
  { name: 'address', label: 'Dirección', maxlength: 200 },
  { name: 'description', label: 'Descripción', type: 'textarea', maxlength: 2000 },
  ...(edit ? [{ name: 'is_active', label: 'Activa', type: 'checkbox' }] : []),
];

export async function render(box, { role }) {
  const admin = role === 'ADMIN';
  let t;
  const columns = [{ label: 'Nombre', key: 'name' }, { label: 'Dirección', key: 'address' }, { label: 'Descripción', key: 'description' },
    { label: 'Estado', render: (f) => yesNo(f.is_active) },
    ...(admin ? [{ label: 'Acciones', render: (f) => h('div', { class: 'actions' },
      h('button', { class: 'btn sm', onclick: () => formModal({ title: `Editar ${f.name}`, fields: fields(true), initial: f,
        onSubmit: async (v) => { await withRelease((c) => api(`/facilities/${f.id}`, { method: 'PATCH', body: v, params: cancelParam(c) }), '¿Cancelarlas y desactivar la instalación?'); toast('Instalación actualizada.', 'ok'); t.reload(); } }) }, 'Editar'),
      f.is_active ? h('button', { class: 'btn sm danger', onclick: async () => {
        if (!(await confirmDialog(`¿Desactivar ${f.name}? Sus mesas dejarán de estar disponibles.`, { okLabel: 'Desactivar', danger: true }))) return;
        try { await withRelease((c) => api(`/facilities/${f.id}`, { method: 'DELETE', params: cancelParam(c) }), '¿Cancelarlas y desactivar la instalación?'); toast('Instalación desactivada.', 'ok'); t.reload(); } catch (e) { fail(e); } } }, 'Desactivar') : null) }] : []),
  ];
  t = dataTable({ columns, search: true, load: (p) => get('/facilities', p) });
  box.append(admin ? h('div', { class: 'toolbar' }, h('button', { class: 'btn primary', onclick: () => formModal({ title: 'Nueva instalación', fields: fields(false),
    onSubmit: async (v) => { await post('/facilities', v); toast('Instalación creada.', 'ok'); t.reload(); } }) }, '+ Nueva instalación')) : null, t.el);
}
