import { get } from '../api.js';
import { dataTable, fmtDateTime, h } from '../ui.js';

export async function render(box) {
  box.append(h('p', { class: 'muted' }, 'Acciones administrativas registradas (más recientes primero).'),
    dataTable({ pageSize: 20, columns: [{ label: 'Fecha', render: (a) => fmtDateTime(a.created_at) }, { label: 'Usuario', render: (a) => a.user_id ?? '—' },
      { label: 'Acción', key: 'action' }, { label: 'Entidad', render: (a) => `${a.entity}${a.entity_id ? ' #' + a.entity_id : ''}` }, { label: 'Detalle', render: (a) => a.detail ?? '—' }],
    load: (p) => get('/audit', p) }).el);
}
