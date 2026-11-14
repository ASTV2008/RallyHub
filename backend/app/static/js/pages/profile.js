import { get, patch, post } from '../api.js';
import { UserError, formModal, fmtDate, h, label, toast } from '../ui.js';

const PASSWORD_HELP = 'Mínimo 10 caracteres, con letras y números.';

export async function render(box, { me, role }) {
  const rows = [['Nombre', me.display_name], ['Correo', me.user.email], ['Rol', label(role)]];
  const card = h('section', { class: 'card' }, h('h2', {}, 'Mi cuenta'),
    h('dl', {}, rows.map(([k, v]) => [h('dt', { class: 'muted' }, k), h('dd', {}, v)])));
  const btns = h('div', { class: 'actions' });
  const edit = (title, path, record, fields, okMsg) => formModal({ title, initial: record, fields,
    onSubmit: async (v) => { await patch(path, v); toast(okMsg, 'ok'); setTimeout(() => location.reload(), 600); } });

  if (role === 'STUDENT') {
    const s = await get(`/students/${me.student_id}`);
    card.append(h('p', {}, `Nivel: ${label(s.level)} · Teléfono: ${s.phone ?? '—'} · Acudiente: ${s.guardian_name ?? '—'} · Nacimiento: ${fmtDate(s.birth_date)}`));
    btns.append(h('button', { class: 'btn', onclick: () => edit('Editar mis datos', `/students/${me.student_id}`, s, [
      { name: 'first_name', label: 'Nombres', required: true, maxlength: 80 },
      { name: 'last_name', label: 'Apellidos', required: true, maxlength: 80 },
      { name: 'phone', label: 'Teléfono', type: 'tel', maxlength: 30 },
      { name: 'guardian_name', label: 'Acudiente', maxlength: 120 }], 'Datos actualizados.') }, 'Editar mis datos'));
  }
  if (role === 'COACH') {
    const c = await get(`/coaches/${me.coach_id}`);
    card.append(h('p', {}, `Especialidad: ${c.specialty ?? '—'} · Teléfono: ${c.phone ?? '—'}`));
    if (c.bio) card.append(h('p', { class: 'muted' }, c.bio));
    btns.append(h('button', { class: 'btn', onclick: () => edit('Editar mi perfil', `/coaches/${me.coach_id}`, c, [
      { name: 'first_name', label: 'Nombres', required: true, maxlength: 80 },
      { name: 'last_name', label: 'Apellidos', required: true, maxlength: 80 },
      { name: 'specialty', label: 'Especialidad', maxlength: 120 },
      { name: 'phone', label: 'Teléfono', type: 'tel', maxlength: 30 },
      { name: 'bio', label: 'Biografía', type: 'textarea', maxlength: 2000 }], 'Perfil actualizado.') }, 'Editar mi perfil'));
  }
  btns.append(h('button', { class: 'btn', onclick: () => formModal({ title: 'Cambiar correo de acceso', submitLabel: 'Cambiar', fields: [
    { name: 'new_email', label: 'Correo nuevo', type: 'email', required: true, maxlength: 254, autocomplete: 'email' },
    { name: 'current_password', label: 'Contraseña actual', type: 'password', required: true, autocomplete: 'current-password',
      help: 'Se pide para confirmar que eres tú.' }],
  onSubmit: async (v) => { await post('/auth/change-email', v); toast('Correo actualizado.', 'ok'); setTimeout(() => location.reload(), 600); } }) }, 'Cambiar correo'));
  btns.append(h('button', { class: 'btn primary', onclick: () => formModal({ title: 'Cambiar contraseña', submitLabel: 'Cambiar', fields: [
    { name: 'current_password', label: 'Contraseña actual', type: 'password', required: true, autocomplete: 'current-password' },
    { name: 'new_password', label: 'Contraseña nueva', type: 'password', required: true, autocomplete: 'new-password', help: PASSWORD_HELP },
    { name: 'confirm', label: 'Repite la contraseña nueva', type: 'password', required: true, autocomplete: 'new-password' }],
  onSubmit: async (v) => {
    if (v.new_password !== v.confirm) throw new UserError('Las contraseñas nuevas no coinciden.');
    await post('/auth/change-password', { current_password: v.current_password, new_password: v.new_password });
    toast('Contraseña actualizada. Inicia sesión de nuevo.', 'ok');
    setTimeout(() => { location.href = '/login'; }, 1200);
  } }) }, 'Cambiar contraseña'));
  box.append(card, h('div', { class: 'toolbar' }, btns));
}
