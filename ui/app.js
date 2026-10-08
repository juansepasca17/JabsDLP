'use strict';

/* ================= iconos (trazos estilo Lucide) ================= */
const ICONOS = {
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
  list: '<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  clipboard: '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  like: '<path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/>',
  calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
  video: '<path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
  refresh: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  cookie: '<path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/><path d="M8.5 8.5v.01"/><path d="M16 15.5v.01"/><path d="M12 12v.01"/><path d="M11 17v.01"/><path d="M7 14v.01"/>',
  playlist: '<path d="M12 12H3"/><path d="M16 6H3"/><path d="M12 18H3"/><path d="m16 12 5 3-5 3v-6Z"/>',
  sparkles: '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>',
  alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  wrench: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  layers: '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
  sliders: '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
  loader: '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  image: '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
  tag: '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5"/>',
  captions: '<rect width="18" height="14" x="3" y="5" rx="2" ry="2"/><path d="M7 15h4M15 15h2M7 11h2M13 11h4"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  box: '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  monitor: '<rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/>',
  film: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/>',
  hand: '<path d="M18 11V6a2 2 0 0 0-2-2a2 2 0 0 0-2 2"/><path d="M14 10V4a2 2 0 0 0-2-2a2 2 0 0 0-2 2v2"/><path d="M10 10.5V6a2 2 0 0 0-2-2a2 2 0 0 0-2 2v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>',
  zap: '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
};

const ico = (nombre, clase = '') => `<svg class="ico ${clase}" viewBox="0 0 24 24" aria-hidden="true">${ICONOS[nombre] || ''}</svg>`;

function hidratarIconos(raiz = document) {
  raiz.querySelectorAll('[data-ico]').forEach(el => {
    if (el.tagName === 'I') {
      el.outerHTML = ico(el.dataset.ico, el.getAttribute('class') || '');
    } else {
      el.insertAdjacentHTML('afterbegin', ico(el.dataset.ico));
      el.removeAttribute('data-ico');
    }
  });
}

/* ================= utilidades ================= */
const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const fmt = {
  bytes(n) {
    if (n == null || isNaN(n)) return null;
    const u = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return `${n.toFixed(n >= 100 || i === 0 ? 0 : 1)} ${u[i]}`;
  },
  kbps(k) { if (!k) return null; return k >= 1000 ? `${(k / 1000).toFixed(1)} Mbps` : `${Math.round(k)} kbps`; },
  dur(s) {
    if (s == null) return '—';
    s = Math.round(s);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60, p = n => String(n).padStart(2, '0');
    return h ? `${h}:${p(m)}:${p(x)}` : `${m}:${p(x)}`;
  },
  num(n) {
    if (n == null) return '—';
    if (n >= 1e9) return `${(n / 1e9).toFixed(1)} B`;
    if (n >= 1e6) return `${(n / 1e6).toFixed(1)} M`;
    if (n >= 1e3) return `${(n / 1e3).toFixed(1)} K`;
    return String(n);
  },
  fecha(f) {
    if (!f || String(f).length !== 8) return '—';
    const meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    f = String(f);
    return `${f.slice(6)} ${meses[+f.slice(4, 6) - 1]} ${f.slice(0, 4)}`;
  },
  vel(b) { return b ? `${fmt.bytes(b)}/s` : null; },
};

const NOMBRES = {
  codec: { auto: 'Auto', h264: 'H.264', h265: 'H.265', av1: 'AV1', vp9: 'VP9' },
  resolucion: { auto: 'Auto', 2160: '2160p', 1440: '1440p', 1080: '1080p', 720: '720p', 480: '480p', 360: '360p' },
  contenedor: { auto: 'Auto', mp4: 'MP4', mkv: 'MKV', webm: 'WEBM' },
  formato_audio: { auto: 'Auto', mp3: 'MP3', m4a: 'M4A', opus: 'OPUS', flac: 'FLAC' },
  audio: { auto: 'Con audio', no: 'Sin audio', custom: 'Personalizado' },
  audio_calidad: { alta: 'Alta (~130 kbps)', media: 'Media (~70 kbps)', baja: 'Baja (~50 kbps)' },
  criterio: { equilibrado: 'Menor tamaño sin perder calidad', ahorro: 'Menor tamaño (sacrifica calidad)', calidad: 'Mejor calidad' },
};
const ESTADOS = {
  en_cola: ['En cola', ''], iniciando: ['Iniciando', 'acento'], descargando: ['Descargando', 'acento'],
  procesando: ['Procesando', 'acento'], esperando_gpu: ['Esperando turno', 'warn'], convirtiendo: ['Convirtiendo', 'warn'],
  completado: ['Completado', 'ok'], error: ['Error', 'err'], cancelado: ['Cancelado', ''],
};
const ACTIVOS = ['en_cola', 'iniciando', 'descargando', 'procesando', 'esperando_gpu', 'convirtiendo'];
const esUrlPlaylist = u => /list=|\/playlist|\/sets\/|\/album\//i.test(u || '');

function toast(html, tipo = '') {
  const el = document.createElement('div');
  el.className = `toast ${tipo}`;
  el.innerHTML = `${ico(tipo === 'err' ? 'alert' : tipo === 'ok' ? 'check' : 'info')}<div>${html}</div>`;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), tipo === 'err' ? 7000 : 4500);
}

/* ================= estado ================= */
let API = null;
const S = {
  vista: 'descargar',
  modo: 'video',
  modoManual: false,
  analisis: null,
  cargando: false,
  error: null,
  prefs: {},
  modoSel: 'auto',      // auto (opción recomendada) | manual (Personalizado)
  seleccion: null,      // spec elegido en Personalizado
  audioId: null,        // pista elegida con Audio: Personalizado
  verManual: false,
  calc: null,
  plSel: new Set(),
  ajustes: {},
  herr: null,
  cola: [],
  resumen: {},
};

/* ================= navegación ================= */
const TITULOS = { descargar: 'Descargar', cola: 'Cola de descargas', ajustes: 'Ajustes' };
function irA(vista) {
  S.vista = vista;
  $$('.nav').forEach(b => b.classList.toggle('activo', b.dataset.vista === vista));
  $$('.vista').forEach(v => v.classList.toggle('activa', v.id === `vista-${vista}`));
  $('#titulo-vista').textContent = TITULOS[vista];
  if (vista === 'cola') refrescarCola();
  if (vista === 'ajustes') { pintarAjustes(); refrescarHerramientas(); }
}

/* ================= metadatos ================= */
function renderMeta() {
  const cont = $('#metadatos');
  const a = S.analisis;
  $('#cab-meta').textContent = a?.tipo === 'playlist' ? 'Playlist' : a?.tipo === 'lote' ? 'Lote de enlaces' : 'Metadatos';
  if (S.cargando) {
    cont.innerHTML = `
      <div class="miniatura esqueleto"></div>
      <div class="esqueleto" style="height:20px;margin:16px 0 8px;width:85%"></div>
      <div class="esqueleto" style="height:14px;width:40%;margin-bottom:14px"></div>
      <div class="esqueleto" style="height:14px;width:65%"></div>`;
    return;
  }
  if (S.error) {
    cont.innerHTML = `<div class="vacio"><div class="circulo" style="color:var(--err)">${ico('alert')}</div>
      <b>No se pudo analizar</b><small>${esc(S.error)}</small></div>`;
    return;
  }
  if (!a) {
    cont.innerHTML = `<div class="vacio"><div class="circulo">${ico('link')}</div>
      <b>Pega una URL y pulsa Analizar</b>
      <small>Funciona con videos, playlists y canales de YouTube y de cientos de sitios más. También puedes pegar varias URLs o importar un .txt.</small></div>`;
    return;
  }
  if (a.tipo === 'lote') {
    cont.innerHTML = `<div class="card pad">
      <div class="meta-titulo" style="margin-top:0">${a.cantidad} enlaces</div>
      <div class="meta-canal">Cada enlace se descargará con la opción recomendada según tus preferencias.</div>
      <div class="meta-origen">${ico('file', 'sm')}Importados o pegados</div></div>`;
    return;
  }
  const img = a.miniatura ? `<img src="${esc(a.miniatura)}" alt="" referrerpolicy="no-referrer">` : '';
  if (a.tipo === 'playlist') {
    cont.innerHTML = `
      <div class="miniatura">${img}<div class="tipo-lista">${ico('playlist', 'lg')}<span>${a.cantidad} videos</span></div></div>
      <div class="meta-titulo">${esc(a.titulo)}</div>
      <div class="meta-canal">${esc(a.canal || '')}</div>
      <div class="meta-fila">
        <span>${ico('playlist', 'sm')}${a.cantidad} videos</span>
        ${a.duracion ? `<span>${ico('clock', 'sm')}${fmt.dur(a.duracion)} en total</span>` : ''}
      </div>
      <div class="meta-origen">${ico('globe', 'sm')}Extraído de ${esc(a.extractor || 'la web')}</div>`;
    return;
  }
  const datos = [a.resolucion, fmt.kbps(a.tbr), a.fps ? `${Math.round(a.fps)} fps` : null].filter(Boolean);
  cont.innerHTML = `
    <div class="miniatura">${img}${a.duracion ? `<span class="duracion">${fmt.dur(a.duracion)}</span>` : ''}</div>
    <div class="meta-titulo" title="${esc(a.titulo)}">${esc(a.titulo)}</div>
    <div class="meta-canal">${esc(a.canal || '')}</div>
    <div class="meta-fila">
      <span>${ico('clock', 'sm')}${fmt.dur(a.duracion)}</span>
      <span>${ico('eye', 'sm')}${fmt.num(a.vistas)}</span>
      <span>${ico('like', 'sm')}${fmt.num(a.likes)}</span>
      <span>${ico('calendar', 'sm')}${fmt.fecha(a.fecha)}</span>
    </div>
    <div class="meta-datos">${datos.map(d => `<span class="dato">${esc(d)}</span>`).join('')}${a.en_vivo ? '<span class="insignia err">EN VIVO</span>' : ''}</div>
    <div class="meta-origen">${ico('globe', 'sm')}Extraído de ${esc(a.extractor || 'la web')}</div>`;
}

/* ================= opciones ================= */
const MENUS = {
  codec: { titulo: 'Códec de video', opciones: [
    ['auto', 'Auto', 'El más eficiente disponible (AV1 › VP9 › H.264)'],
    ['h264', 'H.264', 'Máxima compatibilidad'],
    ['h265', 'H.265', 'Si el video no viene así, se convierte con la GPU'],
    ['av1', 'AV1', 'El que menos pesa'],
    ['vp9', 'VP9', 'Buena eficiencia, muy común en YouTube']] },
  resolucion: { titulo: 'Resolución máxima', opciones: [
    ['auto', 'Auto', 'Según el criterio automático'], ['2160', '2160p (4K)'], ['1440', '1440p (2K)'],
    ['1080', '1080p (Full HD)'], ['720', '720p (HD)'], ['480', '480p'], ['360', '360p']] },
  contenedor: { titulo: 'Contenedor', opciones: [
    ['auto', 'Auto', 'MP4 si los códecs lo permiten; si no, MKV'], ['mp4', 'MP4', 'Se abre en cualquier reproductor'],
    ['mkv', 'MKV', 'Admite cualquier códec y varias pistas'], ['webm', 'WEBM', 'Solo VP9/AV1 con Opus']] },
  audio: { titulo: 'Audio', opciones: [
    ['auto', 'Con audio', 'La mejor pista automáticamente'], ['no', 'Sin audio', 'Solo la imagen'],
    ['custom', 'Personalizado', 'Elige la pista o la calidad del audio']] },
  extras: { titulo: 'Metadatos y extras', casillas: true },
  formato_audio: { titulo: 'Formato de audio', opciones: [
    ['auto', 'Auto', 'Sin recodificar (Opus o M4A según la fuente)'], ['mp3', 'MP3', 'Compatible con todo'],
    ['m4a', 'M4A', 'AAC, ideal para móviles y Apple'], ['opus', 'OPUS', 'El más eficiente'], ['flac', 'FLAC', 'Sin pérdida (más pesado)']] },
  criterio: { titulo: 'Selección de formato', opciones: [
    ['equilibrado', 'Auto · Menor tamaño sin perder calidad', 'Máxima resolución con el códec más eficiente'],
    ['ahorro', 'Auto · Menor tamaño (sacrifica calidad)', 'Hasta 720p, menos fps y audio medio'],
    ['calidad', 'Auto · Mejor calidad', 'El mayor bitrate disponible, sin mirar el tamaño'],
    ['-'],
    ['manual', 'Personalizado', 'Elige tú el formato de la lista']] },
};

function nombreEncoder(objetivo) {
  const e = S.calc?.encoder || S.herr?.encoder;
  if (!e) return 'ffmpeg';
  if (!e.gpu) return `CPU (${objetivo === 'h264' ? 'libx264' : 'libx265'})`;
  return `GPU ${e.nombre}`;
}

const esLista = () => S.analisis && (S.analisis.tipo === 'playlist' || S.analisis.tipo === 'lote');
const enAuto = () => S.modoSel === 'auto' || esLista();

function formatoHTML(o, recomendado) {
  const activo = recomendado ? enAuto() : (!enAuto() && S.seleccion === o.spec);
  const linea2 = o.video
    ? [fmt.bytes(o.tamano) || 'Tamaño desconocido', fmt.kbps(o.tbr), o.fps ? `${Math.round(o.fps)} fps` : null, (o.contenedor || '').toUpperCase()]
    : [fmt.bytes(o.tamano) || 'Tamaño desconocido', o.idioma, (o.contenedor || '').toUpperCase(), o.recodificar ? `convierte a ${o.recodificar.toUpperCase()}` : 'sin recodificar'];
  const etiquetas = recomendado ? (o.etiquetas || []).map((t, i) => `<span class="insignia ${i === 0 ? 'acento' : 'ok'}">${esc(t)}</span>`).join('') : '';
  const recod = o.video && o.recodificar
    ? (recomendado
      ? `<div class="recodif">${ico('zap', 'sm')}Se convertirá a ${NOMBRES.codec[o.recodificar]} con ${esc(nombreEncoder(o.recodificar))}</div>`
      : `<span class="insignia warn">→ ${NOMBRES.codec[o.recodificar]}</span>`)
    : '';
  return `<button class="formato ${recomendado ? 'recomendado' : ''} ${activo ? 'activo' : ''}" data-sel="${esc(recomendado ? 'auto' : o.spec)}">
      <span class="radio"></span>
      <span>
        <span class="linea1">${recomendado ? ico('sparkles', 'sm') : ''}${esc(o.titulo)}${o.hdr ? '<span class="insignia">HDR</span>' : ''}${etiquetas}${recomendado ? '' : recod}</span>
        <span class="linea2" style="display:block">${linea2.filter(Boolean).map(esc).join(' · ')}</span>
        ${recomendado ? recod : `<span class="linea3" style="display:block">ID ${esc(o.ids)}</span>`}
      </span>
      <span class="iconos">${o.video ? ico('video', 'sm') : ''}${o.audio ? ico('music', 'sm') : ''}</span>
    </button>`;
}

function pistaHTML(o) {
  const activo = S.audioId === o.spec;
  return `<button class="formato ${activo ? 'activo' : ''}" data-audio="${esc(o.spec)}">
      <span class="radio"></span>
      <span>
        <span class="linea1">${esc(o.titulo)}${o.idioma ? `<span class="insignia">${esc(o.idioma)}</span>` : ''}</span>
        <span class="linea2" style="display:block">${[fmt.bytes(o.tamano) || 'Tamaño desconocido', (o.contenedor || '').toUpperCase()].map(esc).join(' · ')}</span>
      </span>
      <span class="iconos">${ico('music', 'sm')}</span>
    </button>`;
}

function chips(clave, valores, nombres) {
  return `<div class="chips">${valores.map(v => {
    const activo = String(S.prefs[clave]) === String(v);
    return `<button class="chip ${activo ? 'activo' : ''}" data-pref="${clave}" data-valor="${v}">${activo ? ico('check', 'sm') : ''}${esc(nombres ? nombres[v] : v)}</button>`;
  }).join('')}</div>`;
}

function chipPref(clave, icono, etiqueta, valor, marcado) {
  return `<button class="chip-pref ${marcado ? 'marcado' : ''}" data-abrir="${clave}" title="${esc(MENUS[clave].titulo)}">${ico(icono)}
    <span><span class="k">${esc(etiqueta)}</span><span class="v">${esc(valor)}${ico('chevron')}</span></span></button>`;
}

function filaPrefsHTML() {
  const p = S.prefs;
  let html = '';
  if (p.tipo === 'audio') {
    html += chipPref('formato_audio', 'music', 'Formato', NOMBRES.formato_audio[p.formato_audio], p.formato_audio !== 'auto');
  } else {
    html += chipPref('codec', 'film', 'Códec', NOMBRES.codec[p.codec], p.codec !== 'auto');
    html += chipPref('resolucion', 'monitor', 'Resolución', NOMBRES.resolucion[p.resolucion], p.resolucion !== 'auto');
    html += chipPref('contenedor', 'box', 'Contenedor', NOMBRES.contenedor[p.contenedor], p.contenedor !== 'auto');
    html += chipPref('audio', 'music', 'Audio', NOMBRES.audio[p.audio], p.audio !== 'auto');
  }
  const extras = (p.metadatos && p.miniatura ? 1 : 0) + (p.tipo !== 'audio' && p.subtitulos ? 1 : 0);
  const valorExtras = p.metadatos ? `Metadatos${extras ? ` +${extras}` : ''}` : (extras ? 'Subtítulos' : 'Ninguno');
  html += chipPref('extras', 'tag', 'Extras', valorExtras, !p.metadatos);
  return `<div class="etiqueta-grupo" style="margin-top:14px">${ico('sliders', 'sm')}Preferencias de formato</div><div class="fila-prefs">${html}</div>`;
}

function seleccionHTML() {
  const auto = enAuto();
  return `<div class="etiqueta-grupo">${ico('sparkles', 'sm')}Selección de formato</div>
    <div class="seleccion-formato">
      <button class="chip chip-auto ${auto ? 'activo' : ''}" data-abrir="criterio">${ico(auto ? 'check' : 'sparkles', 'sm')}Auto · ${esc(NOMBRES.criterio[S.prefs.criterio])}${ico('chevron', 'flecha')}</button>
      <button class="chip chip-auto ${auto ? '' : 'activo'}" data-accion="modo-manual" ${esLista() ? 'disabled title="En playlists cada video usa Auto"' : ''}>${ico(auto ? 'hand' : 'check', 'sm')}Personalizado</button>
    </div>`;
}

function audioPersonalizadoHTML() {
  if (S.prefs.tipo === 'audio' || S.prefs.audio !== 'custom') return '';
  const pistas = S.calc?.audios || [];
  if (esLista() || !pistas.length) {
    return `<div class="etiqueta-grupo">${ico('music', 'sm')}Calidad del audio</div>
      ${chips('audio_calidad', ['alta', 'media', 'baja'], NOMBRES.audio_calidad)}`;
  }
  return `<div class="etiqueta-grupo">${ico('music', 'sm')}Pista de audio <span class="cuenta">(${pistas.length})</span></div>
    <div class="lista-formatos compacta">${pistas.map(pistaHTML).join('')}</div>`;
}

function pieHTML(texto, habilitado) {
  let destino = S.ajustes.carpeta_efectiva || '';
  if (S.analisis?.tipo === 'playlist' && S.ajustes.subcarpeta_playlist) destino += `\\${S.analisis.titulo}`;
  return `<div class="pie-opciones">
      <div class="destino" title="${esc(destino)}">${ico('folder', 'sm')}<span>${esc(destino)}</span></div>
      <div class="acciones">
        <button class="btn pildora" data-accion="cancelar-analisis">${ico('x')}Cancelar</button>
        <button class="btn pildora primario" data-accion="descargar" ${habilitado ? '' : 'disabled'}>${ico('check')}${esc(texto)}</button>
      </div>
    </div>`;
}

function listaPlaylistHTML() {
  const a = S.analisis;
  const items = a.tipo === 'playlist'
    ? a.entradas.map(e => ({ clave: e.indice, n: e.indice, titulo: e.titulo, dur: e.duracion, img: e.miniatura }))
    : a.urls.map((u, i) => ({ clave: i, n: i + 1, titulo: u, dur: null, img: null }));
  const todos = S.plSel.size === items.length;
  return `<div class="etiqueta-grupo">${ico('playlist', 'sm')}${a.tipo === 'playlist' ? 'Videos de la playlist' : 'Enlaces'}
      <span class="cuenta">(${S.plSel.size} de ${items.length})</span>
      <button class="btn chico fantasma" style="margin-left:auto" data-accion="pl-todos">${todos ? 'Desmarcar todos' : 'Marcar todos'}</button></div>
    <div class="lista-playlist">${items.map(it => `
      <div class="item-pl" data-pl="${it.clave}">
        <span class="casilla ${S.plSel.has(it.clave) ? 'on' : ''}"></span>
        <span class="n">${it.n}</span>
        ${it.img ? `<img src="${esc(it.img)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : '<span class="sin-img"></span>'}
        <span class="t" title="${esc(it.titulo)}">${esc(it.titulo)}</span>
        <span class="n">${it.dur ? fmt.dur(it.dur) : ''}</span>
      </div>`).join('')}
    </div>`;
}

function tarjetaAutoListaHTML() {
  const p = S.prefs;
  const conversion = p.tipo !== 'audio' && ['h264', 'h265'].includes(p.codec)
    ? `<div class="recodif">${ico('zap', 'sm')}Si un video no viene en ${NOMBRES.codec[p.codec]}, se convierte con ${esc(nombreEncoder(p.codec))}</div>` : '';
  return `<div class="formato recomendado activo" style="margin-top:12px"><span class="radio"></span><span>
      <span class="linea1">${ico('sparkles', 'sm')}Automático para cada video<span class="insignia acento">${esc(NOMBRES.criterio[p.criterio])}</span></span>
      <span class="linea2" style="display:block">Cada video se descarga con su opción recomendada según tus preferencias.</span>${conversion}
    </span><span class="iconos">${p.tipo === 'audio' ? ico('music', 'sm') : ico('video', 'sm') + (p.audio !== 'no' ? ico('music', 'sm') : '')}</span></div>`;
}

function renderOpciones() {
  const cont = $('#opciones');
  const scroll = [...cont.querySelectorAll('.lista-formatos, .lista-playlist, .fila-prefs')].map(e => [e.scrollTop, e.scrollLeft]);
  $$('#tipo button').forEach(b => b.classList.toggle('activo', b.dataset.tipo === (S.prefs.tipo || 'video')));
  let html = filaPrefsHTML() + seleccionHTML() + audioPersonalizadoHTML();

  if (S.cargando) {
    html += '<div class="esqueleto" style="height:84px;border-radius:12px;margin-top:14px"></div>';
    html += pieHTML('Descargar', false);
  } else if (esLista()) {
    html += tarjetaAutoListaHTML();
    html += listaPlaylistHTML();
    const n = S.plSel.size;
    html += pieHTML(`Descargar ${n} ${n === 1 ? 'video' : 'videos'}`, n > 0);
  } else {
    const rec = S.calc?.recomendado;
    const opciones = S.calc?.opciones || [];
    const mostrarRec = S.ajustes.recomendacion !== false || enAuto();
    html += '<div style="margin-top:14px"></div>';
    if (mostrarRec) {
      html += rec ? formatoHTML(rec, true)
        : `<div class="formato" style="cursor:default"><span class="radio"></span><span><span class="linea1">Sin opción recomendada</span>
           <span class="linea2" style="display:block">No hay formatos de este tipo para este enlace.</span></span><span></span></div>`;
      if (rec?.aviso) html += `<div class="aviso">${ico('alert', 'sm')}<span>${esc(rec.aviso)}</span></div>`;
    }
    if (opciones.length) {
      if (!enAuto() || S.verManual) {
        html += `<div class="etiqueta-grupo">Opciones manuales <span class="cuenta">(${opciones.length})</span>
          ${enAuto() ? `<button class="btn chico fantasma" style="margin-left:auto" data-accion="ver-manual">Ocultar</button>` : ''}</div>
          <div class="lista-formatos">${opciones.map(o => formatoHTML(o, false)).join('')}</div>`;
      } else {
        html += `<button class="btn chico fantasma mostrar-manual" data-accion="ver-manual">${ico('list', 'sm')}Ver opciones manuales (${opciones.length})</button>`;
      }
    }
    const listo = enAuto() ? !!rec : opciones.some(o => o.spec === S.seleccion);
    html += pieHTML(enAuto() || listo ? 'Descargar' : 'Elige un formato', listo);
  }
  cont.innerHTML = html;
  [...cont.querySelectorAll('.lista-formatos, .lista-playlist, .fila-prefs')].forEach((e, i) => {
    if (scroll[i]) { e.scrollTop = scroll[i][0]; e.scrollLeft = scroll[i][1]; }
  });
}

function inicioHTML() {
  return `<div class="inicio">
      <img src="logo.png" alt="">
      <h2>Pega un enlace para empezar</h2>
      <p>Videos, playlists y canales de YouTube y de cientos de sitios más. También puedes pegar varias URLs a la vez o importar un .txt.</p>
      <div class="pasos">
        <span class="paso"><b>1</b> Pega la URL y pulsa Analizar</span>
        <span class="paso"><b>2</b> Deja Auto o elige el formato</span>
        <span class="paso"><b>3</b> Descarga, en paralelo y sin límite</span>
      </div>
    </div>`;
}

function renderDescargar() {
  $$('#modo button').forEach(b => b.classList.toggle('activo', b.dataset.modo === S.modo));
  $('#btn-analizar').innerHTML = S.cargando ? `${ico('loader', 'spin')}Analizando…` : `${ico('search')}Analizar`;
  $('#btn-analizar').disabled = S.cargando;
  const hay = S.cargando || S.analisis || S.error;
  $('#inicio').innerHTML = hay ? '' : inicioHTML();
  $('#columnas').classList.toggle('oculto', !hay);
  $('#columnas').classList.toggle('solo-izq', !!S.error && !S.cargando);
  if (hay) {
    renderMeta();
    if (!S.error) renderOpciones();
  }
}

/* ================= menús desplegables ================= */
function casillasExtras() {
  const p = S.prefs;
  const filas = [
    ['metadatos', 'Metadatos', 'Título, autor, fecha y capítulos dentro del archivo', true],
    ['miniatura', p.tipo === 'audio' ? 'Portada incrustada' : 'Miniatura incrustada', 'Necesita los metadatos activados', p.metadatos],
  ];
  if (p.tipo !== 'audio') filas.push(['subtitulos', 'Subtítulos', 'Idiomas configurables en Ajustes', true]);
  return filas.map(([clave, texto, desc, habilitado]) => {
    const on = !!p[clave] && habilitado;
    return `<button class="menu-item" data-menu-casilla="${clave}" ${habilitado ? '' : 'disabled'}>
        <span class="casilla ${on ? 'on' : ''}" style="width:16px;height:16px;margin-top:1px"></span><span><b>${esc(texto)}</b><small>${esc(desc)}</small></span></button>`;
  }).join('');
}

function posicionarMenu(ancla) {
  const menu = $('#menu');
  if (!ancla || menu.classList.contains('oculto')) return;
  const r = ancla.getBoundingClientRect();
  const ancho = menu.offsetWidth, alto = menu.offsetHeight;
  menu.style.left = `${Math.max(8, Math.min(r.left, window.innerWidth - ancho - 8))}px`;
  menu.style.top = `${r.bottom + 6 + alto > window.innerHeight - 8 ? Math.max(8, r.top - alto - 6) : r.bottom + 6}px`;
  $$('.chip-pref.abierto').forEach(c => c.classList.remove('abierto'));
  ancla.classList.add('abierto');
}

function abrirMenu(clave, ancla) {
  const menu = $('#menu');
  const def = MENUS[clave];
  menu.dataset.clave = clave;
  menu.classList.remove('oculto');
  if (def.casillas) {
    menu.innerHTML = `<div class="menu-titulo">${esc(def.titulo)}</div>${casillasExtras()}`;
    return posicionarMenu(ancla);
  }
  const actual = clave === 'criterio' ? (enAuto() ? S.prefs.criterio : 'manual') : String(S.prefs[clave]);
  menu.innerHTML = `<div class="menu-titulo">${esc(def.titulo)}</div>` + def.opciones.map(([valor, texto, desc]) => {
    if (valor === '-') return '<div class="menu-sep"></div>';
    const activo = valor === actual;
    const deshabilitado = clave === 'criterio' && valor === 'manual' && esLista();
    return `<button class="menu-item ${activo ? 'activo' : ''}" data-menu-valor="${valor}" ${deshabilitado ? 'disabled' : ''}>
        ${activo ? ico('check', 'sm') : '<span></span>'}<span><b>${esc(texto)}</b>${desc ? `<small>${esc(desc)}</small>` : ''}</span></button>`;
  }).join('');
  posicionarMenu(ancla);
}

function cerrarMenu() {
  $('#menu').classList.add('oculto');
  $$('.chip-pref.abierto').forEach(c => c.classList.remove('abierto'));
}

function elegirDeMenu(valor) {
  const clave = $('#menu').dataset.clave;
  cerrarMenu();
  if (clave === 'criterio') {
    if (valor === 'manual') return activarManual();
    S.modoSel = 'auto';
    return cambiarPref('criterio', valor);
  }
  cambiarPref(clave, valor);
}

function activarManual() {
  if (esLista()) return;
  S.modoSel = 'manual';
  if (!S.seleccion && S.calc?.recomendado) S.seleccion = S.calc.recomendado.spec;
  renderOpciones();
}

/* ================= acciones de descarga ================= */
async function analizar() {
  const texto = $('#url').value.trim();
  if (!texto) { toast('Pega una URL primero.', 'err'); $('#url').focus(); return; }
  cerrarMenu();
  S.cargando = true; S.error = null; S.analisis = null; S.calc = null;
  S.seleccion = null; S.audioId = null; S.verManual = false;
  S.modoSel = S.ajustes.recomendacion === false ? 'manual' : 'auto';
  renderDescargar();
  let r;
  try {
    r = await API.analizar(texto, S.modo, S.prefs);
  } catch (e) {
    r = { ok: false, error: String(e) };
  }
  S.cargando = false;
  if (!r.ok) {
    S.error = r.error;
  } else {
    S.analisis = r.datos;
    if (r.datos.tipo === 'video') {
      S.calc = { recomendado: r.datos.recomendado, opciones: r.datos.opciones, audios: r.datos.audios,
                 audio_elegido: r.datos.audio_elegido, encoder: r.datos.encoder };
      if (S.prefs.audio === 'custom') S.audioId = r.datos.audio_elegido;
    } else if (r.datos.tipo === 'playlist') {
      S.plSel = new Set(r.datos.entradas.map(e => e.indice));
    } else {
      S.plSel = new Set(r.datos.urls.map((_, i) => i));
    }
  }
  renderDescargar();
}

async function recalcular() {
  if (S.analisis?.tipo !== 'video') { renderOpciones(); return; }
  const r = await API.opciones(S.analisis.id, S.prefs, S.prefs.audio === 'custom' ? S.audioId : null);
  S.calc = r;
  if (S.prefs.audio === 'custom' && !S.audioId) S.audioId = r.audio_elegido;
  if (S.seleccion && !r.opciones.some(o => o.spec === S.seleccion)) {
    const video = S.seleccion.split('+')[0];
    S.seleccion = r.opciones.find(o => o.spec.split('+')[0] === video)?.spec || null;
  }
  renderOpciones();
}

let temporizadorPrefs = null;
function cambiarPref(clave, valor) {
  if (valor === 'toggle') valor = !S.prefs[clave];
  else if (valor === 'true' || valor === 'false') valor = valor === 'true';
  S.prefs[clave] = valor;
  if (clave === 'tipo') { S.seleccion = null; S.verManual = false; }
  if (clave === 'audio') S.audioId = null;
  clearTimeout(temporizadorPrefs);
  temporizadorPrefs = setTimeout(() => API.guardar_ajustes({ prefs: S.prefs }).then(a => { S.ajustes = a; }), 500);
  return recalcular();
}

async function descargar() {
  const a = S.analisis;
  if (!a) return;
  let solicitud;
  if (a.tipo === 'video') {
    solicitud = { tipo: 'video', id: a.id, spec: enAuto() ? null : S.seleccion,
                  audio_id: S.prefs.audio === 'custom' ? S.audioId : null, prefs: S.prefs };
  } else if (a.tipo === 'playlist') {
    solicitud = { tipo: 'playlist', id: a.id, indices: [...S.plSel], prefs: S.prefs };
  } else {
    solicitud = { tipo: 'lote', urls: a.urls.filter((_, i) => S.plSel.has(i)), prefs: S.prefs };
  }
  const r = await API.descargar(solicitud);
  if (r.ok) toast(`${r.agregados} ${r.agregados === 1 ? 'descarga añadida' : 'descargas añadidas'} a la cola. <a data-vista="cola">Ver cola</a>`, 'ok');
  else toast(esc(r.error), 'err');
  refrescarCola();
}

function alCambiarUrl() {
  const valor = $('#url').value;
  if (!S.modoManual) {
    S.modo = esUrlPlaylist(valor) ? 'playlist' : 'video';
    $$('#modo button').forEach(b => b.classList.toggle('activo', b.dataset.modo === S.modo));
  }
}

/* ================= cola ================= */
function plantillaTrabajo() {
  return `<div class="mini"></div>
    <div class="cuerpo">
      <div class="t"></div>
      <div class="sub"></div>
      <div class="barra-progreso"><div></div></div>
      <div class="stats"></div>
    </div>
    <div class="acciones"></div>`;
}

function accionesTrabajo(t) {
  const b = (tarea, icono, titulo, extra = '') => `<button class="btn chico icono ${extra}" data-tarea="${tarea}" title="${titulo}">${ico(icono, 'sm')}</button>`;
  if (ACTIVOS.includes(t.estado)) return b('cancelar', 'x', 'Cancelar', 'peligro');
  if (t.estado === 'completado') return b('abrir', 'play', 'Abrir archivo') + b('carpeta', 'folder', 'Mostrar en la carpeta') + b('quitar', 'trash', 'Quitar de la lista');
  return b('reintentar', 'refresh', 'Reintentar') + b('quitar', 'trash', 'Quitar de la lista');
}

function actualizarTrabajo(el, t) {
  const mini = el.querySelector('.mini');
  if (mini.dataset.src !== (t.miniatura || '')) {
    mini.dataset.src = t.miniatura || '';
    mini.innerHTML = t.miniatura ? `<img src="${esc(t.miniatura)}" alt="" referrerpolicy="no-referrer">` : ico(t.tipo === 'audio' ? 'music' : 'video', 'lg');
  }
  el.querySelector('.t').textContent = t.titulo;
  el.querySelector('.t').title = t.titulo;
  const [nombreEstado, claseEstado] = ESTADOS[t.estado] || [t.estado, ''];
  el.querySelector('.sub').innerHTML = `<span class="insignia ${claseEstado}">${esc(nombreEstado)}</span>
    ${ico(t.tipo === 'audio' ? 'music' : 'video', 'sm')}<span>${esc([t.canal, t.titulo_formato, t.fase && t.fase !== nombreEstado ? t.fase : null].filter(Boolean).join(' · '))}</span>`;

  const barra = el.querySelector('.barra-progreso');
  barra.className = 'barra-progreso';
  let ancho = t.progreso * 100;
  if (t.estado === 'completado') { barra.classList.add('ok'); ancho = 100; }
  else if (t.estado === 'error') { barra.classList.add('err'); ancho = 100; }
  else if (t.estado === 'convirtiendo') { barra.classList.add('conv'); ancho = t.progreso_conversion * 100; }
  else if (['iniciando', 'procesando', 'esperando_gpu'].includes(t.estado)) barra.classList.add('indet');
  else if (t.estado === 'cancelado') ancho = 0;
  barra.firstElementChild.style.width = `${ancho.toFixed(1)}%`;

  let stats = [];
  if (t.estado === 'descargando') {
    stats = [`${(t.progreso * 100).toFixed(1)}%`,
      t.total ? `${fmt.bytes(t.descargado)} de ${fmt.bytes(t.total)}` : fmt.bytes(t.descargado),
      fmt.vel(t.velocidad), t.eta != null ? `${fmt.dur(t.eta)} restantes` : null].map(esc);
  } else if (t.estado === 'convirtiendo') {
    stats = [`${(t.progreso_conversion * 100).toFixed(1)}%`, t.velocidad_conversion ? `velocidad ${t.velocidad_conversion}` : null, t.encoder].map(esc);
  } else if (t.estado === 'completado') {
    stats = [fmt.bytes(t.total), t.encoder ? `Convertido con ${t.encoder}` : null].map(esc);
  } else if (t.estado === 'error') {
    stats = [`<span class="err">${esc(t.error)}</span>`];
  } else if (t.estado === 'en_cola') {
    stats = ['Esperando turno'];
  }
  if (t.aviso) stats.push(`<span class="warn">${esc(t.aviso)}</span>`);
  el.querySelector('.stats').innerHTML = stats.filter(Boolean).map(s => `<span>${s}</span>`).join('');

  if (el.dataset.estado !== t.estado) {
    el.dataset.estado = t.estado;
    el.querySelector('.acciones').innerHTML = accionesTrabajo(t);
  }
}

function renderCola() {
  const cont = $('#trabajos');
  const lista = [...S.cola].reverse();
  const r = S.resumen || {};
  $('#resumen').innerHTML = [
    r.activos ? `<span class="insignia acento">${r.activos} activas</span>` : '',
    r.en_cola ? `<span class="insignia">${r.en_cola} en cola</span>` : '',
    r.completados ? `<span class="insignia ok">${r.completados} completadas</span>` : '',
    r.errores ? `<span class="insignia err">${r.errores} con error</span>` : '',
  ].join('');
  if (!lista.length) {
    cont.innerHTML = `<div class="vacio"><div class="circulo">${ico('list')}</div><b>La cola está vacía</b>
      <small>Analiza un video o una playlist y pulsa Descargar.</small></div>`;
    return;
  }
  cont.querySelector('.vacio')?.remove();
  const vistos = new Set();
  lista.forEach((t, i) => {
    let el = cont.querySelector(`.trabajo[data-id="${t.id}"]`);
    if (!el) {
      el = document.createElement('div');
      el.className = 'card trabajo';
      el.dataset.id = t.id;
      el.innerHTML = plantillaTrabajo();
    }
    actualizarTrabajo(el, t);
    if (cont.children[i] !== el) cont.insertBefore(el, cont.children[i] || null);
    vistos.add(t.id);
  });
  [...cont.children].forEach(el => { if (!vistos.has(el.dataset.id)) el.remove(); });
}

async function refrescarCola() {
  try {
    const r = await API.cola();
    S.cola = r.trabajos;
    S.resumen = r.resumen;
  } catch (e) {
    return;
  }
  const pendientes = (S.resumen.activos || 0) + (S.resumen.en_cola || 0);
  const contador = $('#contador-cola');
  contador.textContent = pendientes;
  contador.classList.toggle('visible', pendientes > 0);
  if (S.vista === 'cola') renderCola();
}

function bucleCola() {
  refrescarCola().finally(() => setTimeout(bucleCola, S.vista === 'cola' ? 600 : 1500));
}

/* ================= ajustes ================= */
function pintarAjustes() {
  const a = S.ajustes;
  $$('[data-ajuste]').forEach(el => {
    const k = el.dataset.ajuste;
    if (el.type === 'checkbox') el.checked = !!a[k];
    else if (document.activeElement !== el) el.value = a[k] ?? '';
  });
  const criterio = $('[data-pref-ajuste="criterio"]');
  if (criterio && document.activeElement !== criterio) criterio.value = S.prefs.criterio || 'equilibrado';
  $('#aj-carpeta').textContent = a.carpeta_efectiva || '—';
  $('#aj-carpeta').title = a.carpeta_efectiva || '';
  $$('#aj-cookies-modo button').forEach(b => b.classList.toggle('activo', b.dataset.cookies === a.cookies_modo));
  $('#aj-fila-archivo').classList.toggle('oculto', a.cookies_modo !== 'archivo');
  $('#aj-fila-navegador').classList.toggle('oculto', a.cookies_modo !== 'navegador');
  $('#aj-cookies-archivo').textContent = a.cookies_archivo || 'Ninguno';
  $('#aj-calidad-txt').textContent = a.calidad;
  $('#aj-crf-txt').textContent = (+a.calidad || 26) + 2;
  $('#cola-limite-txt').textContent = !a.paralelo ? 'Desactivado: de una en una'
    : (+a.max_paralelo > 0 ? `Hasta ${a.max_paralelo} a la vez` : 'Sin límite');
  pintarEstado();
}

function pintarEstado() {
  const a = S.ajustes, h = S.herr;
  const pf = $('#punto-ffmpeg'), tf = $('#txt-ffmpeg');
  if (h) {
    pf.className = `punto ${h.ffmpeg ? 'ok' : 'err'}`;
    tf.textContent = h.ffmpeg ? 'ffmpeg listo' : 'Falta ffmpeg';
  }
  const pg = $('#punto-gpu'), tg = $('#txt-gpu');
  if (a.gpu === 'cpu') { pg.className = 'punto warn'; tg.textContent = 'GPU desactivada (CPU)'; }
  else if (!h || !h.gpu) { pg.className = 'punto'; tg.textContent = 'Detectando GPU…'; }
  else if (h.encoder?.gpu) { pg.className = 'punto ok'; tg.textContent = `GPU: ${h.encoder.nombre}`; }
  else { pg.className = 'punto warn'; tg.textContent = 'Sin GPU compatible: CPU'; }
  const pp = $('#punto-paralelo'), tp = $('#txt-paralelo');
  pp.className = `punto ${a.paralelo ? 'ok' : ''}`;
  tp.textContent = a.paralelo ? `Paralelo: ${+a.max_paralelo > 0 ? `máx. ${a.max_paralelo}` : 'sin límite'}` : 'Paralelo desactivado';

  if (h) {
    const nombres = { amf: 'AMD AMF', nvenc: 'NVIDIA NVENC', qsv: 'Intel QSV' };
    const detectadas = h.gpu ? Object.entries(h.gpu).filter(([, ok]) => ok).map(([k]) => nombres[k]) : null;
    $('#aj-gpu-detectadas').textContent = detectadas == null ? 'Detectando…'
      : detectadas.length ? `Detectado: ${detectadas.join(', ')}. En Auto se usa ${h.encoder?.nombre || '—'}.` : 'No se detectó GPU compatible; se usará la CPU.';
    $('#aj-ffmpeg').textContent = h.ffmpeg || 'No encontrado';
    $('#aj-ffmpeg').title = h.ffmpeg || '';
    const d = h.descarga || {};
    const btn = $('#btn-ffmpeg');
    btn.disabled = d.estado === 'descargando' || d.estado === 'extrayendo';
    btn.innerHTML = d.estado === 'descargando' ? `${ico('loader', 'sm spin')}${Math.round(d.progreso * 100)}%`
      : d.estado === 'extrayendo' ? `${ico('loader', 'sm spin')}Extrayendo` : `${ico('download', 'sm')}${h.ffmpeg ? 'Reinstalar' : 'Descargar'}`;
    $('#aj-js').textContent = h.js?.length ? `Encontrado: ${h.js.join(', ')} (necesario para YouTube).`
      : 'No encontrado. Instala Node.js o Deno para que YouTube muestre todos los formatos.';
  }
}

async function guardarAjuste(cambios) {
  S.ajustes = await API.guardar_ajustes(cambios);
  pintarAjustes();
  if ('gpu' in cambios || 'calidad' in cambios) { await refrescarHerramientas(); if (S.analisis?.tipo === 'video') recalcular(); }
  if ('recomendacion' in cambios && S.vista === 'descargar' && S.analisis) renderOpciones();
}

async function refrescarHerramientas() {
  S.herr = await API.herramientas();
  pintarEstado();
  const d = S.herr.descarga || {};
  if (d.estado === 'descargando' || d.estado === 'extrayendo' || !S.herr.gpu) {
    setTimeout(refrescarHerramientas, 1000);
  } else if (d.estado === 'error' && !refrescarHerramientas.avisado) {
    refrescarHerramientas.avisado = true;
    toast(`No se pudo descargar ffmpeg: ${esc(d.error)}`, 'err');
  } else if (d.estado === 'listo' && !refrescarHerramientas.listo) {
    refrescarHerramientas.listo = true;
    toast('ffmpeg descargado e instalado.', 'ok');
  }
}

/* ================= eventos ================= */
document.addEventListener('click', async e => {
  const menu = $('#menu');
  const itemMenu = e.target.closest('.menu-item');
  if (itemMenu) {
    if (itemMenu.disabled) return;
    if (itemMenu.dataset.menuCasilla) {
      await cambiarPref(itemMenu.dataset.menuCasilla, 'toggle');
      return abrirMenu('extras', $('[data-abrir="extras"]'));
    }
    return elegirDeMenu(itemMenu.dataset.menuValor);
  }
  if (!menu.classList.contains('oculto') && !menu.contains(e.target)) {
    const mismo = e.target.closest('[data-abrir]')?.dataset.abrir === menu.dataset.clave;
    cerrarMenu();
    if (mismo) return;
  }

  const el = e.target.closest('[data-vista],[data-modo],[data-tipo],[data-pref],[data-sel],[data-audio],[data-pl],[data-cookies],[data-abrir],[data-accion],[data-tarea]');
  if (!el || el.disabled) return;
  const d = el.dataset;
  if (d.vista) return irA(d.vista);
  if (d.abrir) {
    if (d.abrir === 'criterio' && !enAuto()) { S.modoSel = 'auto'; renderOpciones(); }
    const ancla = $(`[data-abrir="${d.abrir}"]`);
    return abrirMenu(d.abrir, ancla || el);
  }
  if (d.modo) {
    S.modo = d.modo; S.modoManual = true;
    $$('#modo button').forEach(b => b.classList.toggle('activo', b.dataset.modo === S.modo));
    if (S.analisis || S.error) analizar();
    return;
  }
  if (d.tipo) return cambiarPref('tipo', d.tipo);
  if (d.pref) return cambiarPref(d.pref, d.valor);
  if (d.sel) {
    if (d.sel === 'auto') S.modoSel = 'auto';
    else { S.modoSel = 'manual'; S.seleccion = d.sel; }
    return renderOpciones();
  }
  if (d.audio) { S.audioId = d.audio; return recalcular(); }
  if (d.pl !== undefined) {
    const clave = +d.pl;
    S.plSel.has(clave) ? S.plSel.delete(clave) : S.plSel.add(clave);
    return renderOpciones();
  }
  if (d.cookies) return guardarAjuste({ cookies_modo: d.cookies });
  if (d.tarea) {
    const id = el.closest('.trabajo').dataset.id;
    const mapa = { cancelar: 'cancelar', reintentar: 'reintentar', quitar: 'quitar', abrir: 'abrir_archivo', carpeta: 'abrir_carpeta' };
    const ok = await API[mapa[d.tarea]](id);
    if (!ok && (d.tarea === 'abrir' || d.tarea === 'carpeta')) toast('No se encontró el archivo (¿lo moviste o borraste?).', 'err');
    return refrescarCola();
  }
  switch (d.accion) {
    case 'analizar': return analizar();
    case 'pegar': {
      const texto = (await API.portapapeles() || '').trim();
      if (!texto) return toast('El portapapeles está vacío.', 'err');
      $('#url').value = texto; S.modoManual = false; alCambiarUrl();
      return analizar();
    }
    case 'importar': {
      const r = await API.importar_txt();
      if (!r) return;
      if (!r.ok) return toast(esc(r.error), 'err');
      S.analisis = { tipo: 'lote', urls: r.urls, cantidad: r.urls.length };
      S.plSel = new Set(r.urls.map((_, i) => i)); S.error = null; S.calc = null;
      $('#url').value = '';
      toast(`${r.urls.length} URLs importadas.`, 'ok');
      return renderDescargar();
    }
    case 'descargar': return descargar();
    case 'modo-manual': return activarManual();
    case 'ver-manual': S.verManual = !S.verManual; return renderOpciones();
    case 'cancelar-analisis':
      cerrarMenu();
      S.analisis = null; S.calc = null; S.error = null; S.seleccion = null; $('#url').value = ''; S.modoManual = false;
      return renderDescargar();
    case 'pl-todos': {
      const claves = S.analisis.tipo === 'playlist' ? S.analisis.entradas.map(x => x.indice) : S.analisis.urls.map((_, i) => i);
      S.plSel = S.plSel.size === claves.length ? new Set() : new Set(claves);
      return renderOpciones();
    }
    case 'abrir-carpeta': return API.abrir_carpeta(null);
    case 'limpiar': await API.limpiar(); return refrescarCola();
    case 'cancelar-todo': await API.cancelar_todo(); return refrescarCola();
    case 'elegir-carpeta': { const r = await API.elegir_carpeta(); if (r) { S.ajustes = r; pintarAjustes(); } return; }
    case 'elegir-cookies': { const r = await API.elegir_cookies(); if (r) { S.ajustes = r; pintarAjustes(); } return; }
    case 'elegir-ffmpeg': {
      const r = await API.elegir_ffmpeg();
      if (r?.aviso) toast(esc(r.aviso), 'err');
      if (r) { S.ajustes = r; pintarAjustes(); setTimeout(refrescarHerramientas, 400); }
      return;
    }
    case 'detectar-gpu': S.herr = await API.detectar_gpu(); pintarEstado(); return toast('Detección de GPU actualizada.', 'ok');
    case 'descargar-ffmpeg':
      refrescarHerramientas.avisado = refrescarHerramientas.listo = false;
      await API.descargar_ffmpeg(); return refrescarHerramientas();
  }
});

document.addEventListener('keydown', e => { if (e.key === 'Escape') cerrarMenu(); });
window.addEventListener('resize', () => posicionarMenu($(`[data-abrir="${$('#menu').dataset.clave}"]`)));
document.addEventListener('scroll', e => { if (!$('#menu').contains(e.target)) cerrarMenu(); }, true);

document.addEventListener('change', e => {
  const pref = e.target.closest('[data-pref-ajuste]');
  if (pref) {
    S.prefs[pref.dataset.prefAjuste] = pref.value;
    API.guardar_ajustes({ prefs: S.prefs }).then(a => { S.ajustes = a; });
    if (S.analisis?.tipo === 'video') recalcular();
    return;
  }
  const el = e.target.closest('[data-ajuste]');
  if (!el) return;
  let valor = el.type === 'checkbox' ? el.checked : el.value;
  if ('numero' in el.dataset) valor = Math.max(0, parseInt(valor, 10) || 0);
  guardarAjuste({ [el.dataset.ajuste]: valor });
});

document.addEventListener('input', e => {
  if (e.target.matches('[data-ajuste="calidad"]')) {
    $('#aj-calidad-txt').textContent = e.target.value;
    $('#aj-crf-txt').textContent = +e.target.value + 2;
  }
});

$('#url').addEventListener('input', () => { S.modoManual = false; alCambiarUrl(); });
$('#url').addEventListener('keydown', e => { if (e.key === 'Enter') analizar(); });

/* ================= arranque ================= */
// Miniaturas rotas: se quitan (sin manejadores inline, que la CSP bloquea)
document.addEventListener('error', e => { if (e.target.tagName === 'IMG' && !e.target.classList.contains('logo')) e.target.remove(); }, true);

function cuandoListo(fn) {
  if (window.__MOCK_API__) { API = window.__MOCK_API__; fn(); return; }
  if (window.pywebview?.api) { API = window.pywebview.api; fn(); return; }
  window.addEventListener('pywebviewready', () => { API = window.pywebview.api; fn(); }, { once: true });
}

hidratarIconos();
renderDescargar();
cuandoListo(async () => {
  const r = await API.iniciar();
  S.ajustes = r.ajustes;
  S.prefs = { ...r.ajustes.prefs };
  S.herr = r.herramientas;
  $('#version').textContent = `v${r.version}`;
  $('#aj-versiones').textContent = `${r.app} ${r.version} · yt-dlp ${r.ytdlp}`;
  pintarAjustes();
  renderDescargar();
  refrescarHerramientas();
  bucleCola();
  $('#url').focus();
});
