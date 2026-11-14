import { api, del, get, post } from '../api.js';
import { UserError, badge, clear, confirmDialog, dataTable, dialog, fail, fmtRange, formModal, h, localToIso, options, toast } from '../ui.js';

const STATUS = options(['ACTIVE', 'MAINTENANCE', 'OUT_OF_SERVICE']);

/** Ejecuta `fn(cancel)`; si el servidor avisa de reservas futuras, pide confirmación y reintenta cancelándolas. */
async function withRelease(fn, question) {
  try { return await fn(false); } catch (e) {
    if (e.code !== 'has_future_reservations') throw e;
    if (!(await confirmDialog(`${e.message} ${question}`, { okLabel: 'Cancelar reservas y continuar', danger: true }))) {
      throw new UserError('No se realizó ningún cambio.');
    }
    return fn(true);
  }
}
const cancelParam = (cancel) => (cancel ? { cancel_reservations: 'true' } : undefined);

export async function render(box, { role }) {
  const admin = role === 'ADMIN';
  const facilities = (await get('/facilities', { limit: 100, is_active: 'true' })).items;
  const facOpts = facilities.map((f) => ({ value: f.id, label: f.name }));
  let t;
  const fields = (edit) => [
    { name: 'facility_id', label: 'Instalación', type: 'select', options: facOpts, required: true, asNumber: true, disabled: edit },
    { name: 'code', label: 'Código', required: true, maxlength: 30 },
    { name: 'table_type', label: 'Tipo', maxlength: 60, help: 'Ej.: competición, entrenamiento.' },
    { name: 'description', label: 'Descripción', type: 'textarea', maxlength: 2000 },
    { name: 'status', label: 'Estado', type: 'select', options: STATUS, required: true },
  ];
  const maintenance = async (tb) => {
    const body = h('div');
    const load = async () => {
      clear(body);
      const blocks = await get(`/tables/${tb.id}/maintenance`);
      const now = Date.now();
      const when = (b) => (new Date(b.ends_at) < now ? ['Finalizado', ''] : new Date(b.starts_at) <= now ? ['En curso', 'warn'] : ['Programado', 'ok']);
      body.append(blocks.length ? h('ul', { class: 'list' }, blocks.map((b) => h('li', {}, h('span', { class: 'badge ' + when(b)[1] }, when(b)[0]), ' ', fmtRange(b.starts_at, b.ends_at),
        b.reason ? ` · ${b.reason}` : '', ' ',
        h('button', { class: 'btn sm danger', onclick: async () => {
          if (!(await confirmDialog('¿Quitar este bloqueo de mantenimiento?', { okLabel: 'Quitar', danger: true }))) return;
          try { await del(`/tables/${tb.id}/maintenance/${b.id}`); toast('Bloqueo eliminado.', 'ok'); load(); } catch (e) { fail(e); } } }, 'Quitar'))))
        : h('p', { class: 'muted' }, 'Sin bloqueos de mantenimiento programados.'));
    };
    await load();
    dialog(`Mantenimiento · Mesa ${tb.code}`, body, { footer: h('button', { class: 'btn primary', onclick: () => formModal({ title: 'Nuevo bloqueo', fields: [
      { name: 'starts_at', label: 'Inicio', type: 'datetime-local', required: true }, { name: 'ends_at', label: 'Fin', type: 'datetime-local', required: true },
      { name: 'reason', label: 'Motivo', maxlength: 200 }], onSubmit: async (v) => {
      const send = (cancel) => post(`/tables/${tb.id}/maintenance`, { starts_at: localToIso(v.starts_at), ends_at: localToIso(v.ends_at), reason: v.reason, cancel_conflicts: cancel });
      await withRelease(send, '¿Cancelarlas y programar el mantenimiento?');
      toast('Bloqueo creado.', 'ok'); load(); } }) }, '+ Programar bloqueo') });
  };
  const columns = [{ label: 'Código', key: 'code' }, { label: 'Instalación', key: 'facility_name' }, { label: 'Tipo', key: 'table_type' },
    { label: 'Estado', render: (r) => badge(r.status) },
    { label: 'Acciones', render: (r) => h('div', { class: 'actions' }, admin ? h('button', { class: 'btn sm', onclick: () => maintenance(r) }, 'Mantenimiento') : null,
      admin ? [h('button', { class: 'btn sm', onclick: () => formModal({ title: `Editar mesa ${r.code}`, fields: fields(true), initial: r,
        onSubmit: async (v) => {
          const { facility_id, ...rest } = v;
          await withRelease((cancel) => api(`/tables/${r.id}`, { method: 'PATCH', body: rest, params: cancelParam(cancel) }), '¿Cancelarlas y cambiar el estado de la mesa?');
          toast('Mesa actualizada.', 'ok'); t.reload(); } }) }, 'Editar'),
      r.status !== 'OUT_OF_SERVICE' ? h('button', { class: 'btn sm danger', onclick: async () => {
        if (!(await confirmDialog(`¿Marcar la mesa ${r.code} como fuera de servicio?`, { okLabel: 'Confirmar', danger: true }))) return;
        try {
          await withRelease((cancel) => api(`/tables/${r.id}`, { method: 'DELETE', params: cancelParam(cancel) }), '¿Cancelarlas y dar de baja la mesa?');
          toast('Mesa fuera de servicio.', 'ok'); t.reload();
        } catch (e) { fail(e); } } }, 'Fuera de servicio') : null] : null) },
  ];
  t = dataTable({ columns, search: true, load: (p) => get('/tables', p),
    filters: [{ name: 'facility_id', label: 'Instalación', options: facOpts }, { name: 'status', label: 'Estado', options: STATUS }] });
  box.append(h('p', { class: 'muted' }, 'La disponibilidad se calcula con las reservas, clases y bloqueos; no existe un estado "reservada" manual.'),
    admin ? h('div', { class: 'toolbar' }, h('button', { class: 'btn primary', onclick: () => formModal({ title: 'Nueva mesa', fields: fields(false), initial: { status: 'ACTIVE' },
      onSubmit: async (v) => { await post('/tables', v); toast('Mesa creada.', 'ok'); t.reload(); } }) }, '+ Nueva mesa')) : null, t.el);
}
