import { del, get, patch, post } from '../api.js';
import { badge, clear, confirmDialog, dataTable, dialog, fail, fmtDate, formModal, fullName, h, label, options, toast } from '../ui.js';

const STATUS = options(['OPEN', 'IN_PROGRESS', 'FINISHED', 'CANCELLED']);

export async function render(box, { role, me }) {
  const admin = role === 'ADMIN';
  let t;
  const base = [
    { name: 'name', label: 'Nombre', required: true, maxlength: 120 }, { name: 'category', label: 'Categoría', maxlength: 60 },
    { name: 'starts_on', label: 'Inicio', type: 'date', required: true }, { name: 'ends_on', label: 'Fin', type: 'date', required: true },
    { name: 'location', label: 'Lugar', maxlength: 200 }, { name: 'capacity', label: 'Cupo de participantes', type: 'number', min: 2, max: 512, required: true },
  ];
  const detail = async (tr) => {
    const body = h('div');
    const draw = async () => {
      clear(body);
      const [parts, matches, cur] = await Promise.all([get(`/tournaments/${tr.id}/participants`), get(`/tournaments/${tr.id}/matches`), get(`/tournaments/${tr.id}`)]);
      const mine = parts.find((p) => p.student_id === me.student_id);
      const name = new Map(parts.map((p) => [p.id, p.student_name]));
      body.append(h('p', {}, `${fmtDate(cur.starts_on)} – ${fmtDate(cur.ends_on)} · ${cur.location ?? 'Lugar por definir'} · ${cur.participant_count}/${cur.capacity} inscritos · `, badge(cur.status)),
        role === 'STUDENT' && cur.status === 'OPEN' ? (mine ? h('button', { class: 'btn danger sm', onclick: async () => { try { await del(`/tournaments/${tr.id}/participants/${mine.id}`); toast('Inscripción retirada.', 'ok'); draw(); t.reload(); } catch (e) { fail(e); } } }, 'Retirar mi inscripción')
          : h('button', { class: 'btn primary sm', onclick: async () => { try { await post(`/tournaments/${tr.id}/participants`, {}); toast('Inscripción confirmada.', 'ok'); draw(); t.reload(); } catch (e) { fail(e); } } }, 'Inscribirme')) : null,
        h('h2', {}, 'Participantes'), parts.length ? h('ul', { class: 'list' }, parts.map((p) => h('li', {}, p.student_name, ' ', admin && cur.status === 'OPEN' ? h('button', { class: 'btn sm danger', onclick: async () => { try { await del(`/tournaments/${tr.id}/participants/${p.id}`); draw(); t.reload(); } catch (e) { fail(e); } } }, 'Retirar') : null))) : h('p', { class: 'muted' }, 'Sin participantes.'),
        admin && cur.status === 'OPEN' ? h('button', { class: 'btn sm', onclick: async () => {
          const st = (await get('/students', { limit: 100, is_active: 'true' })).items;
          formModal({ title: 'Inscribir estudiante', fields: [{ name: 'student_id', label: 'Estudiante', type: 'select', required: true, asNumber: true, options: st.map((s) => ({ value: s.id, label: fullName(s) })) }],
            onSubmit: async (v) => { await post(`/tournaments/${tr.id}/participants`, v); toast('Estudiante inscrito.', 'ok'); draw(); t.reload(); } }); } }, '+ Inscribir estudiante') : null,
        h('h2', {}, 'Resultados'), h('p', { class: 'muted' }, 'Registro manual de partidos (marcador en sets). RallyHub no genera cuadros automáticamente.'),
        matches.length ? h('ul', { class: 'list' }, matches.map((m) => h('li', {}, `${m.round_name}: `, h('strong', {}, name.get(m.participant_a_id) ?? '?'), ` ${m.score_a} – ${m.score_b} `, h('strong', {}, name.get(m.participant_b_id) ?? '?'), ' · Ganó: ', name.get(m.winner_id) ?? '—'))) : h('p', { class: 'muted' }, 'Sin resultados.'),
        admin && parts.length >= 2 && !['CANCELLED', 'FINISHED'].includes(cur.status) ? h('button', { class: 'btn sm', onclick: () => formModal({ title: 'Registrar resultado', fields: [
          { name: 'round_name', label: 'Ronda', required: true, maxlength: 60 },
          { name: 'participant_a_id', label: 'Jugador A', type: 'select', required: true, asNumber: true, options: parts.map((p) => ({ value: p.id, label: p.student_name })) },
          { name: 'participant_b_id', label: 'Jugador B', type: 'select', required: true, asNumber: true, options: parts.map((p) => ({ value: p.id, label: p.student_name })) },
          { name: 'score_a', label: 'Sets de A', type: 'number', min: 0, max: 99, required: true }, { name: 'score_b', label: 'Sets de B', type: 'number', min: 0, max: 99, required: true }],
        onSubmit: async (v) => { await post(`/tournaments/${tr.id}/matches`, v); toast('Resultado registrado.', 'ok'); draw(); } }) }, '+ Registrar resultado') : null);
    };
    await draw();
    dialog(tr.name, body, { wide: true });
  };
  const columns = [{ label: 'Torneo', render: (r) => h('span', {}, h('strong', {}, r.name), h('br'), h('span', { class: 'muted' }, `${r.category ?? 'Sin categoría'} · ${label(r.modality)}`)) },
    { label: 'Fechas', render: (r) => `${fmtDate(r.starts_on)} – ${fmtDate(r.ends_on)}` }, { label: 'Inscritos', render: (r) => `${r.participant_count}/${r.capacity}` },
    { label: 'Estado', render: (r) => badge(r.status) },
    { label: 'Acciones', render: (r) => h('div', { class: 'actions' }, h('button', { class: 'btn sm', onclick: () => detail(r) }, 'Ver detalle'),
      admin ? h('button', { class: 'btn sm', onclick: () => formModal({ title: `Editar ${r.name}`, fields: [...base.filter((f) => !['starts_on', 'ends_on'].includes(f.name)), { name: 'status', label: 'Estado', type: 'select', options: STATUS, required: true }], initial: r,
        onSubmit: async (v) => { await patch(`/tournaments/${r.id}`, v); toast('Torneo actualizado.', 'ok'); t.reload(); } }) }, 'Editar') : null) }];
  t = dataTable({ columns, load: (p) => get('/tournaments', p), emptyText: 'No hay torneos.' });
  box.append(admin ? h('div', { class: 'toolbar' }, h('button', { class: 'btn primary', onclick: () => formModal({ title: 'Nuevo torneo', fields: base, wide: true, initial: { capacity: 8 },
    onSubmit: async (v) => { await post('/tournaments', v); toast('Torneo creado.', 'ok'); t.reload(); } }) }, '+ Nuevo torneo')) : null, t.el);
}
