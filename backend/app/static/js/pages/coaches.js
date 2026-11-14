import { del, get, patch, post } from '../api.js';
import { confirmDialog, dataTable, fail, formModal, fullName, h, toast, yesNo } from '../ui.js';

const fields = (create) => [
  ...(create ? [{ name: 'email', label: 'Correo', type: 'email', required: true },
    { name: 'password', label: 'Contraseña inicial', type: 'password', required: true, help: 'Mínimo 10 caracteres, con letras y números.', autocomplete: 'new-password' }] : []),
  { name: 'first_name', label: 'Nombres', required: true, maxlength: 80 },
  { name: 'last_name', label: 'Apellidos', required: true, maxlength: 80 },
  { name: 'specialty', label: 'Especialidad', maxlength: 120 },
  { name: 'phone', label: 'Teléfono', type: 'tel', maxlength: 30 },
  { name: 'bio', label: 'Biografía', type: 'textarea', maxlength: 2000 },
  ...(create ? [] : [{ name: 'is_active', label: 'Activo', type: 'checkbox' }]),
];

export async function render(box, { role }) {
  const admin = role === 'ADMIN';
  let t;
  const columns = [
    { label: 'Nombre', render: (c) => fullName(c) }, { label: 'Especialidad', key: 'specialty' },
    ...(admin ? [{ label: 'Correo', key: 'email' }] : []),
    { label: 'Estado', render: (c) => yesNo(c.is_active) },
    ...(admin ? [{ label: 'Acciones', render: (c) => h('div', { class: 'actions' },
      h('button', { class: 'btn sm', onclick: () => formModal({ title: `Editar a ${fullName(c)}`, fields: fields(false), initial: c,
        onSubmit: async (v) => { await patch(`/coaches/${c.id}`, v); toast('Entrenador actualizado.', 'ok'); t.reload(); } }) }, 'Editar'),
      c.is_active ? h('button', { class: 'btn sm danger', onclick: async () => {
        if (!(await confirmDialog(`¿Desactivar a ${fullName(c)}?`, { okLabel: 'Desactivar', danger: true }))) return;
        try { await del(`/coaches/${c.id}`); toast('Entrenador desactivado.', 'ok'); t.reload(); } catch (e) { fail(e); } } }, 'Desactivar') : null) }] : []),
  ];
  t = dataTable({ columns, search: true, load: (p) => get('/coaches', { ...p, is_active: admin ? p.is_active : 'true' }),
    filters: admin ? [{ name: 'is_active', label: 'Estado', options: [{ value: 'true', label: 'Activos' }, { value: 'false', label: 'Inactivos' }] }] : [] });
  box.append(admin ? h('div', { class: 'toolbar' }, h('button', { class: 'btn primary', onclick: () => formModal({ title: 'Nuevo entrenador', fields: fields(true),
    onSubmit: async (v) => { await post('/coaches', v); toast('Entrenador creado.', 'ok'); t.reload(); } }) }, '+ Nuevo entrenador')) : null, t.el);
}
