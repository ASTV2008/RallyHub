import { api, post } from './api.js';
import { clear, h, label, errorBox, skeleton } from './ui.js';

const NAV = {
  dashboard: { title: 'Panel', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  reservations: { title: 'Reservas', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  classes: { title: 'Clases', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  attendance: { title: 'Asistencia', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  progress: { title: 'Progreso', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  tournaments: { title: 'Torneos', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  students: { title: 'Estudiantes', roles: ['ADMIN', 'COACH'] },
  coaches: { title: 'Entrenadores', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  facilities: { title: 'Instalaciones', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  tables: { title: 'Mesas', roles: ['ADMIN', 'COACH', 'STUDENT'] },
  audit: { title: 'Auditoría', roles: ['ADMIN'] },
  profile: { title: 'Mi perfil', roles: ['ADMIN', 'COACH', 'STUDENT'] },
};

const ctx = { me: null, role: null };
const $ = (id) => document.getElementById(id);

async function start() {
  try {
    ctx.me = await api('/auth/me');
  } catch {
    location.href = '/login';
    return;
  }
  ctx.role = ctx.me.user.role;
  $('who').replaceChildren(ctx.me.display_name, h('span', { class: 'role-badge' }, label(ctx.role)));
  const nav = $('nav');
  for (const [key, def] of Object.entries(NAV)) {
    if (def.roles.includes(ctx.role)) nav.append(h('li', {}, h('a', { href: '#/' + key, 'data-route': key }, def.title)));
  }
  $('logout').addEventListener('click', async () => {
    try { await post('/auth/logout'); } finally { location.href = '/login'; }
  });
  $('menu').addEventListener('click', () => {
    const open = $('side').classList.toggle('open');
    $('menu').setAttribute('aria-expanded', String(open));
  });
  window.addEventListener('hashchange', route);
  route();
}

let token = 0;
async function route() {
  const key = (location.hash.replace(/^#\//, '').split('?')[0]) || 'dashboard';
  const def = NAV[key];
  const view = $('view');
  $('side').classList.remove('open');
  if (!def || !def.roles.includes(ctx.role)) {
    $('title').textContent = 'No disponible';
    clear(view).append(h('div', { class: 'alert err' }, 'Esta sección no existe o no está disponible para tu rol.'));
    return;
  }
  const mine = ++token;
  document.querySelectorAll('[data-route]').forEach((a) => {
    if (a.dataset.route === key) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  $('crumbs').textContent = 'Inicio / ' + def.title;
  $('title').textContent = def.title;
  document.title = `${def.title} · RallyHub`;
  clear(view).append(skeleton());
  try {
    const mod = await import(`./pages/${key}.js`);
    if (mine !== token) return;
    const box = h('div');
    await mod.render(box, ctx);
    if (mine !== token) return;
    clear(view).append(box);
    $('main').focus({ preventScroll: true });
  } catch (e) {
    if (mine === token) clear(view).append(errorBox(e, route));
  }
}

start();
