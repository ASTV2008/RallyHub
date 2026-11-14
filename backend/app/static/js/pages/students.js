import { del, get, patch, post } from '../api.js';
import { LEVELS, confirmDialog, dataTable, fail, formModal, fullName, h, toast, yesNo, badge, fmtDate } from '../ui.js';

const fields = (create) => [
  ...(create ? [{ name: 'email', label: 'Correo', type: 'email', required: true, autocomplete: 'off' },
    { name: 'password', label: 'Contraseña inicial', type: 'password', required: true, help: 'Mínimo 10 caracteres, con letras y números. El estudiante debería cambiarla.', autocomplete: 'new-password' }] : []),
  { name: 'first_name', label: 'Nombres', required: true, maxlength: 80 },
  { name: 'last_name', label: 'Apellidos', required: true, maxlength: 80 },
  { name: 'birth_date', label: 'Fecha de nacimiento', type: 'date' },
  { name: 'phone', label: 'Teléfono', type: 'tel', maxlength: 30 },
  { name: 'guardian_name', label: 'Acudiente (si es menor)', maxlength: 120 },
  { name: 'level', label: 'Nivel', type: 'select', options: LEVELS, required: true },
  ...(create ? [] : [{ name: 'is_active', label: 'Activo', type: 'checkbox' }]),
];

export async function render(box, { role }) {
  const admin = role === 'ADMIN';
  let t;
  const columns = [
    { label: 'Nombre', render: (s) => fullName(s) }, { label: 'Correo', key: 'email' },
    { label: 'Nivel', render: (s) => badge(s.level) }, { label: 'Estado', render: (s) => yesNo(s.is_active) },
    ...(admin ? [{ label: 'Acciones', render: (s) => h('div', { class: 'actions' },
      h('button', { class: 'btn sm', onclick: () => edit(s) }, 'Editar'),
      s.is_active ? h('button', { class: 'btn sm danger', onclick: () => deactivate(s) }, 'Desactivar') : null) }] : []),
  ];
  const edit = (s) => formModal({ title: `Editar a ${fullName(s)}`, fields: fields(false), initial: s,
    onSubmit: async (v) => { await patch(`/students/${s.id}`, v); toast('Estudiante actualizado.', 'ok'); t.reload(); } });
  const deactivate = async (s) => {
    if (!(await confirmDialog(`¿Desactivar a ${fullName(s)}? Se conserva su historial y no podrá iniciar sesión.`, { okLabel: 'Desactivar', danger: true }))) return;
    try { await del(`/students/${s.id}`); toast('Estudiante desactivado.', 'ok'); t.reload(); } catch (e) { fail(e); }
  };
  t = dataTable({ columns, search: true, filters: [{ name: 'level', label: 'Nivel', options: LEVELS }, { name: 'is_active', label: 'Estado', options: [{ value: 'true', label: 'Activos' }, { value: 'false', label: 'Inactivos' }] }],
    load: (p) => get('/students', p), emptyText: 'No hay estudiantes que coincidan.' });
  box.append(
    admin ? h('div', { class: 'toolbar' }, h('button', { class: 'btn primary', onclick: () => formModal({ title: 'Nuevo estudiante', fields: fields(true), initial: { level: 'BEGINNER' },
      onSubmit: async (v) => { await post('/students', v); toast('Estudiante creado.', 'ok'); t.reload(); } }) }, '+ Nuevo estudiante'),
    h('span', { class: 'spacer' }), h('a', { class: 'btn', href: '/api/v1/students/export.csv', download: 'estudiantes.csv' }, 'Exportar CSV')) : h('p', { class: 'muted' }, 'Se muestran los estudiantes inscritos en tus clases.'),
    t.el);
}
