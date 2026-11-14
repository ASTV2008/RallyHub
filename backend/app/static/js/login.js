import { api, ApiError } from './api.js';

const form = document.getElementById('form');
const msg = document.getElementById('msg');
const go = document.getElementById('go');

api('/auth/me').then(() => { location.href = '/'; }).catch(() => { /* sin sesión: mostrar formulario */ });

form.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  msg.replaceChildren();
  const email = form.email.value.trim();
  const password = form.password.value;
  if (!email || !password) { show('Ingresa tu correo y contraseña.'); return; }
  go.disabled = true;
  try {
    await api('/auth/login', { method: 'POST', body: { email, password } });
    location.href = '/';
  } catch (e) {
    show(e instanceof ApiError ? e.message : 'No fue posible iniciar sesión.');
  } finally { go.disabled = false; }
});

function show(text) {
  const d = document.createElement('div');
  d.className = 'alert err';
  d.textContent = text;
  msg.append(d);
}
