/* JabsDLP 1.7: pestaña Ver. Reproductor propio sobre <video> + hls.js, con listas de reproducción desde las
   colecciones (siguiente/anterior, automático, aleatorio, repetir y "continuar donde lo dejaste"). */

const V = {
  datos: null, hls: null, offset: 0,          // offset: segundo desde el que arrancó el remux de ffmpeg
  lista: [], actual: -1, coleccion: null, nombreLista: '',
  aleatorio: false, repetir: 'no',            // no | lista | uno
  guardado: 0, ocultarTimer: null, velocidad: 1, subActual: -1, cargando: false,
};
const video = () => $('#video');

/* ---------- tiempo (en remux el <video> empieza en 0 aunque estemos en el segundo V.offset) ---------- */
function duracionVer() {
  const v = video();
  if (V.datos?.modo === 'remux') return V.datos.duracion || 0;
  return Number.isFinite(v.duration) && v.duration > 0 ? v.duration : V.datos?.duracion || 0;
}
// remux: ?t= segundo de inicio, &a= pista de audio elegida
function srcRemux(t) { return `${V.datos.src}?t=${t.toFixed(2)}${V.audioRemux ? `&a=${V.audioRemux}` : ''}`; }
function tiempoVer() { return (V.datos?.modo === 'remux' ? V.offset : 0) + (video().currentTime || 0); }

function saltarA(t) {
  const d = duracionVer();
  t = Math.max(0, d ? Math.min(t, d - 0.5) : t);
  const v = video();
  if (V.datos?.modo === 'remux') {
    const reproduciendo = !v.paused;
    V.offset = t;
    v.src = srcRemux(t);
    if (reproduciendo) v.play().catch(() => {});
  } else {
    v.currentTime = t;
  }
  pintarTiempo();
}

/* ---------- cargar y reproducir ---------- */
async function verOrigen(origen, opciones = {}) {
  origen = (origen || '').trim();
  if (!origen) return toast('Pega un enlace o elige un archivo.', 'err');
  const esTorrent = /^magnet:\?/i.test(origen) || /\.torrent(\?|$)/i.test(origen);
  if (esTorrent && !(await confirmarAviso(['torrent_ver']))) return false;
  if (S.vista !== 'ver') irA('ver');
  V.cargando = true;
  V.inicioCarga = Date.now(); V.inicioAnotado = false;
  limpiarReproductor();   // el anterior deja de sonar y de descargar mientras se prepara este
  $('#ver-detalle')?.remove();
  pintarEstadoVer(esTorrent ? 'Conectando con el torrent…' : 'Preparando…', true);
  $('#reproductor').classList.remove('oculto');
  $('#ver-inicio').innerHTML = '';
  let r;
  try { r = await API.ver(origen, opciones.referer || null); } catch (e) { r = { ok: false, error: String(e) }; }
  V.cargando = false;
  if (!r.ok) {
    limpiarReproductor();
    V.datos = null;
    errorVer(r.error, r.detalle);
    $('#ver-info').innerHTML = `<div class="ver-titulo"><div class="txt"></div><div class="acciones">
      <button class="btn chico" data-accion="ver-cerrar" title="Quitar y volver al inicio">${ico('x', 'sm')}Cerrar</button></div></div>`;
    return false;
  }
  cargarFuente(r.datos, opciones.desde || 0);
  return true;
}

/* Error en el reproductor; con «Mostrar log completo» también el detalle y «Copiar log», como en la Cola */
function errorVer(texto, detalle = null) {
  pintarEstadoVer(texto, false, true);
  // los errores al preparar el video ya los anota Python; aquí, los del reproductor (con el video cargado)
  if (V.datos) anotarErrorUi(`Reproductor (${V.datos.modo}): ${texto}${detalle ? ' · ' + detalle : ''}`);
  $('#ver-detalle')?.remove();
  if (!S.ajustes.log_completo) return;
  const info = detalle || `${texto}\nOrigen: ${V.datos?.origen || $('#ver-url').value || ''}\nModo: ${V.datos?.modo || '-'}`;
  $('#ver-info').insertAdjacentHTML('beforebegin', `<div class="detalle no-traducir" id="ver-detalle">
      <pre>${esc(info)}</pre>
      <div class="detalle-acciones"><button class="btn chico" data-accion="ver-copiar-log">${ico('copy', 'sm')}Copiar log</button></div></div>`);
  $('#ver-detalle').dataset.texto = info;
}

/* Pista de audio inicial: la original del video (YouTube con doblajes) o, si no, la del idioma del sistema */
function elegirAudioInicial() {
  const pistas = V.hls?.audioTracks || [];
  if (pistas.length < 2 || V.audioElegido) return;
  V.audioElegido = true;
  const idioma = p => (p.lang || '').toLowerCase();
  const original = (V.datos?.audio_original || '').toLowerCase();
  const sistema = (navigator.language || 'es').slice(0, 2).toLowerCase();
  let i = original ? pistas.findIndex(p => idioma(p) === original) : -1;
  if (i < 0 && original) i = pistas.findIndex(p => idioma(p).split('-')[0] === original.split('-')[0]);
  if (i < 0) i = pistas.findIndex(p => /original/i.test(p.name || ''));
  if (i < 0) i = pistas.findIndex(p => idioma(p).startsWith(sistema));
  if (i >= 0 && i !== V.hls.audioTrack) V.hls.audioTrack = i;
}

function nombreAudio(p, i) {
  let nombre = p.name || p.lang || `Pista ${i + 1}`;
  try { if (p.lang && !p.name) nombre = new Intl.DisplayNames([window.I18N?.idioma || 'es'], { type: 'language' }).of(p.lang); } catch { /* idioma raro */ }
  const original = V.datos?.audio_original;
  if (original && (p.lang || '').toLowerCase().split('-')[0] === original.toLowerCase().split('-')[0] && !/original/i.test(nombre)) nombre += ' (original)';
  return nombre;
}

/* X: quita el video y deja la pestaña como antes de cargarlo */
function cerrarVer() {
  guardarProgresoVer();
  limpiarReproductor();
  V.datos = null; V.lista = []; V.actual = -1; V.coleccion = null; V.nombreLista = '';
  clearInterval(temporizadorTorrent);
  avisarMusica();   // quita la notificación de lo que sonaba
  API.detener_ver();
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  if (V.completaCss) completaCss(false);
  $('#reproductor').classList.add('oculto');
  pintarEstadoVer('');
  $('#ver-detalle')?.remove();
  $('#ver-info').innerHTML = '';
  $('#ver-url').value = '';
  pintarListaVer();
  pintarInicioVer();
}

function limpiarReproductor() {
  const v = video();
  if (V.hls) { V.hls.destroy(); V.hls = null; }
  v.pause();
  v.removeAttribute('src');
  [...v.querySelectorAll('track')].forEach(t => { if (t.src.startsWith('blob:')) URL.revokeObjectURL(t.src); t.remove(); });
  v.load();
}

function cargarFuente(datos, desde) {
  limpiarReproductor();
  V.datos = datos;
  V.offset = 0;
  V.subActual = -1;
  V.guardado = 0;
  const v = video();
  v.playbackRate = V.velocidad;
  $('#reproductor').classList.toggle('solo-audio', !!datos.solo_audio);
  const portada = datos.miniatura || V.lista[V.actual]?.miniatura;
  $('#reproductor').style.setProperty('--fondo-audio', portada ? `url("${portada.replace(/"/g, '')}")` : 'none');
  $('#reproductor').classList.toggle('con-portada', !!portada);
  if (!portada && V.lista[V.actual]?.ruta) miniaturaLocal(V.lista[V.actual]);
  V.audioElegido = false;
  V.audioRemux = 0;
  try { v.currentTime = 0; } catch { /* sin medio */ }   // el siguiente empieza en 0:00, no donde iba el anterior
  if (datos.modo === 'hls') {
    if (window.Hls?.isSupported()) {
      // buffer moderado: en pausa hls.js deja de pedir segmentos al llenarlo (y tras un rato se para del todo)
      V.hls = new Hls({ maxBufferLength: 30, maxMaxBufferLength: 60, backBufferLength: 30, enableWorker: true, startPosition: desde || 0 });
      V.hls.on(Hls.Events.ERROR, (_, e) => { if (e.fatal) errorVer('No se pudo cargar el video (error de red o enlace caducado).', `${e.type}: ${e.details}${e.response?.code ? ` (HTTP ${e.response.code})` : ''}`); });
      V.hls.on(Hls.Events.MANIFEST_PARSED, () => { elegirAudioInicial(); v.play().catch(() => {}); });
      V.hls.on(Hls.Events.AUDIO_TRACKS_UPDATED, () => { elegirAudioInicial(); actualizarBotonesVer(); });
      V.hls.on(Hls.Events.AUDIO_TRACK_SWITCHED, actualizarBotonesVer);
      V.hls.loadSource(datos.src);
      V.hls.attachMedia(v);
    } else {
      v.src = datos.src;
    }
  } else if (datos.modo === 'remux') {
    V.offset = desde || 0;
    v.src = srcRemux(V.offset);
  } else {
    v.src = datos.src;
    const inicio = desde || 0;
    v.addEventListener('loadedmetadata', () => { if (Math.abs(v.currentTime - inicio) > 0.5) v.currentTime = inicio; }, { once: true });
  }
  // Las pistas se crean vacías: el VTT se descarga al activarla (ver activarSubtitulo)
  (datos.subtitulos || []).forEach((s, i) => {
    const t = document.createElement('track');
    Object.assign(t, { kind: 'subtitles', label: s.nombre, srclang: (s.idioma || 'und').slice(0, 8) });
    v.appendChild(t);
    t.track.mode = 'disabled';
    t.dataset.n = i;
  });
  if (datos.modo !== 'hls') v.play().catch(() => {});
  pintarEstadoVer('', false);
  $('#ver-detalle')?.remove();
  pintarInfoVer();
  pintarListaVer();
  actualizarBotonesVer();
  vigilarTorrent();
}

// Estado del torrent (pares, velocidad, progreso) mientras se ve
let temporizadorTorrent = null;
function vigilarTorrent() {
  clearInterval(temporizadorTorrent);
  if (!V.datos?.torrent) return;
  const pintar = async () => {
    const e = await API.estado_torrent();
    const el = $('#ver-torrent');
    if (!e || !V.datos?.torrent) { clearInterval(temporizadorTorrent); el?.remove(); return; }
    const texto = `Torrent · ${e.pares} pares · ${fmt.vel(e.bajada) || '0 B/s'} · ${Math.round(e.progreso * 100)} % descargado · sin compartir al cerrar`;
    if (el) el.textContent = texto;
    else $('.ver-titulo .meta-fila')?.insertAdjacentHTML('beforeend', `<span id="ver-torrent" class="no-traducir-num">${esc(texto)}</span>`);
    if (!video().readyState || $('#rp-estado').classList.contains('visible') && !$('#rp-estado').classList.contains('error')) {
      pintarEstadoVer(e.pares ? `Descargando el principio del video… (${e.pares} pares, ${fmt.vel(e.bajada) || '0 B/s'})` : 'Buscando pares…', true);
    }
  };
  pintar();
  temporizadorTorrent = setInterval(pintar, 1500);
}

/* ---------- estado, información y controles ---------- */
function pintarEstadoVer(texto, girando = false, error = false) {
  const el = $('#rp-estado');
  el.className = `rp-estado ${texto ? 'visible' : ''} ${error ? 'error' : ''}`;
  el.innerHTML = texto ? `${girando ? ico('loader', 'lg spin') : error ? ico('alert', 'lg') : ''}<span>${esc(texto)}</span>` : '';
}

function itemActual() { return V.lista[V.actual] || null; }

function pintarInfoVer() {
  const d = V.datos;
  if (!d) { $('#ver-info').innerHTML = ''; return; }
  const enLista = V.lista.length > 1 ? `<span>${ico('playlist', 'sm')}${esc(V.nombreLista || 'Lista')} · ${V.actual + 1} de ${V.lista.length}</span>` : '';
  const remoto = /^https?:\/\//i.test(d.origen || '');
  $('#ver-info').innerHTML = `<div class="ver-titulo">
      <div class="txt"><b class="no-traducir">${esc(d.titulo)}</b>
        <div class="meta-fila">${d.canal ? `<span class="no-traducir">${esc(d.canal)}</span>` : ''}
          ${d.duracion ? `<span>${ico('clock', 'sm')}${fmt.dur(d.duracion)}</span>` : ''}${enLista}
          ${d.modo === 'remux' ? `<span title="El video y el audio llegan por separado y se unen al vuelo: saltar en la línea de tiempo tarda un par de segundos.">${ico('zap', 'sm')}Unido al vuelo</span>` : ''}</div></div>
      <div class="acciones">
        <button class="btn chico" data-accion="ver-guardar" title="Guardar en una colección">${ico('star', 'sm')}Guardar</button>
        ${remoto ? `<button class="btn chico" data-accion="ver-descargar" title="Descargarlo">${ico('download', 'sm')}Descargar</button>` : ''}
        <button class="btn chico" data-accion="ver-lista-panel" title="Listas y colecciones">${ico('playlist', 'sm')}Listas</button>
        <button class="btn chico icono" data-accion="ver-cerrar" title="Quitar el video y volver al inicio">${ico('x', 'sm')}</button>
      </div></div>`;
}

function actualizarBotonesVer() {
  const v = video();
  $('#rp-play').innerHTML = ico(v.paused ? 'play' : 'pause');
  $('#rp-silencio').innerHTML = ico(v.muted || v.volume === 0 ? 'volumen-x' : 'volumen');
  $('#rp-vol').value = v.muted ? 0 : v.volume;
  $('#rp-velocidad').textContent = `${V.velocidad}×`;
  $('#rp-subs').classList.toggle('activo', V.subActual >= 0);
  $('#rp-subs').classList.toggle('oculto', !(V.datos?.subtitulos || []).length);
  $('#rp-calidad').classList.toggle('oculto', !(nivelesCalidad().length > 1));
  $('#rp-audio').classList.toggle('oculto', !(V.hls?.audioTracks?.length > 1 || (!V.hls && V.datos?.audios?.length > 1)));
  $$('[data-rp="anterior"], [data-rp="siguiente"]').forEach(b => b.classList.toggle('oculto', V.lista.length < 2));
}

function pintarTiempo() {
  const d = duracionVer(), t = tiempoVer();
  $('#rp-tiempo').textContent = `${fmt.dur(t)} / ${d ? fmt.dur(d) : '--:--'}`;
  const pct = d ? Math.min(100, t / d * 100) : 0;
  $('#rp-avance').style.width = `${pct}%`;
  $('#rp-bola').style.left = `${pct}%`;
  const v = video();
  let cargado = 0;
  if (d && v.buffered.length) {
    for (let i = 0; i < v.buffered.length; i++) {
      if (v.buffered.start(i) <= v.currentTime + 1) cargado = Math.max(cargado, v.buffered.end(i));
    }
    cargado = (V.datos?.modo === 'remux' ? V.offset : 0) + cargado;
  }
  $('#rp-cargado').style.width = `${d ? Math.min(100, cargado / d * 100) : 0}%`;
}

function mostrarControles() {
  const rp = $('#reproductor');
  rp.classList.add('controles-visibles');
  clearTimeout(V.ocultarTimer);
  if (!video().paused) V.ocultarTimer = setTimeout(() => { if (!$('#rp-menu').classList.contains('visible')) rp.classList.remove('controles-visibles'); }, 2600);
}

function alternarPlay() {
  const v = video();
  if (!V.datos) return;
  if (v.paused) v.play().catch(() => {}); else v.pause();
}

function destello(icono) {
  const c = $('#rp-centro');
  c.innerHTML = ico(icono, 'lg');
  c.classList.remove('destello'); void c.offsetWidth; c.classList.add('destello');
}

/* ---------- menús del reproductor (velocidad, subtítulos, calidad) ---------- */
function abrirMenuVer(tipo, ancla) {
  const menu = $('#rp-menu');
  if (menu.classList.contains('visible') && menu.dataset.tipo === tipo) return cerrarMenuVer();
  let opciones = [];
  if (tipo === 'velocidad') opciones = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2].map(v => [v, `${v}×`, v === V.velocidad]);
  if (tipo === 'subs') opciones = [[-1, 'Desactivados', V.subActual < 0], ...(V.datos?.subtitulos || []).map((s, i) => [i, nombreSubtitulo(s), V.subActual === i])];
  if (tipo === 'audio') {
    // la original y la del idioma del sistema primero; luego el resto por nombre
    const sistema = (navigator.language || 'es').slice(0, 2).toLowerCase();
    const peso = (p, nombre) => (/original/i.test(nombre) ? 0 : (p.lang || '').toLowerCase().startsWith(sistema) ? 1 : 2);
    if (V.hls) {
      opciones = (V.hls.audioTracks || []).map((p, i) => [i, nombreAudio(p, i), V.hls.audioTrack === i, p])
        .sort((a, b) => peso(a[3], a[1]) - peso(b[3], b[1]) || a[1].localeCompare(b[1]));
    } else {   // archivo local con varias pistas o audio aparte (se une al vuelo)
      opciones = (V.datos?.audios || []).map((p, i) => {
        let nombre = p.nombre;
        try { if (p.idioma && /^[a-z]{2,3}(-|$)/.test(p.idioma)) nombre = `${new Intl.DisplayNames([window.I18N?.idioma || 'es'], { type: 'language' }).of(p.idioma)}${p.nombre && p.nombre !== p.idioma ? ` · ${p.nombre}` : ''}`; } catch { /* idioma raro */ }
        if (p.original && !/original/i.test(nombre)) nombre += ' (original)';
        return [i, nombre, (V.audioRemux || 0) === i];
      });
    }
  }
  if (tipo === 'calidad') {
    opciones = [[-1, 'Automática', !!V.hls?.autoLevelEnabled], ...nivelesCalidad().map(({ i, l }) =>
      [i, `${l.height ? `${l.height}p` : `${Math.round(l.bitrate / 1000)} kbps`}${(l.frameRate || 0) > 31 ? Math.round(l.frameRate) : ''}`,
       !V.hls.autoLevelEnabled && (V.hls.currentLevel === i || V.hls.nextLevel === i)])];
  }
  menu.dataset.tipo = tipo;
  menu.innerHTML = (opciones.length > 12 ? `<input class="entrada chica rp-filtro" type="search" placeholder="${tipo === 'subs' ? 'Buscar idioma' : 'Buscar'}" autocomplete="off">` : '')
    + opciones.map(([v, t, on]) => `<button class="rp-opcion ${on ? 'on' : ''}" data-rp-opcion="${v}" data-texto="${esc(normalizarTexto(t))}">${on ? ico('check', 'sm') : '<span class="ico sm"></span>'}<span class="no-traducir-num">${esc(t)}</span></button>`).join('');
  menu.classList.add('visible');
  menu.classList.remove('oculto');
  const rp = $('#reproductor').getBoundingClientRect(), b = ancla.getBoundingClientRect();
  menu.style.right = `${Math.max(8, rp.right - b.right)}px`;
  ['left', 'top', 'bottom', 'width', 'maxHeight'].forEach(k => { menu.style[k] = ''; });
  if (esAndroid() && S.ajustes?.ver_menu !== 'panel') colocarDesplegable(menu, b);
  menu.querySelector('.rp-opcion.on')?.scrollIntoView({ block: 'nearest' });
}
// Nombre del subtítulo en el idioma de la app («Spanish (traducción automática)» -> «Español (traducción automática)»)
function nombreSubtitulo(s) {
  let extra = (s.nombre.match(/ \((automáticos|traducción automática)\)$/) || [''])[0];
  if (window.I18N?.idioma === 'en') extra = extra.replace('traducción automática', 'auto-translated').replace('automáticos', 'auto-generated');
  try {
    const codigo = (s.idioma || '').replace(/-orig$/, '');
    if (codigo) {
      const n = new Intl.DisplayNames([window.I18N?.idioma || 'es'], { type: 'language' }).of(codigo);
      if (n && n !== codigo) return n.charAt(0).toUpperCase() + n.slice(1) + extra;
    }
  } catch { /* código raro: se deja el nombre que da el sitio */ }
  return s.nombre;
}
document.addEventListener('input', e => {
  if (!e.target.classList?.contains('rp-filtro')) return;
  const q = normalizarTexto(e.target.value.trim());
  $$('#rp-menu .rp-opcion').forEach(b => { b.style.display = !q || b.dataset.texto.includes(q) ? '' : 'none'; });
});

// YouTube da cada resolución varias veces (H.264, VP9, AV1; 30 o 60 fps). Se ofrece una por resolución, solo con
// códecs que este dispositivo reproduce, prefiriendo H.264 (lo decodifica el hardware de casi cualquier teléfono)
function nivelesCalidad() {
  const niveles = V.hls?.levels || [];
  const soporta = l => !l.videoCodec || !window.MediaSource || MediaSource.isTypeSupported(`video/mp4; codecs="${l.videoCodec}"`);
  const mejor = {};
  niveles.forEach((l, i) => {
    if (!soporta(l)) return;
    const clave = l.height || Math.round(l.bitrate / 1000);
    const puntos = (/^avc1/.test(l.videoCodec || '') ? 4 : /^(vp09|vp9)/.test(l.videoCodec || '') ? 2 : 0) + (l.bitrate || 0) / 1e9;
    if (!(clave in mejor) || puntos > mejor[clave].puntos) mejor[clave] = { i, l, puntos };
  });
  return Object.values(mejor).sort((a, b) => (b.l.height || b.l.bitrate) - (a.l.height || a.l.bitrate));
}

// Celular: el menú se despliega junto a su botón (como en PC) pero no queda recortado por el video: va fijo en la
// pantalla, encima del botón si cabe (si no, debajo), con filas grandes para tocar bien
function colocarDesplegable(menu, b) {
  const ancho = Math.min(250, innerWidth - 16);
  menu.style.right = 'auto';
  menu.style.width = `${ancho}px`;
  menu.style.left = `${Math.max(8, Math.min(b.right - ancho, innerWidth - ancho - 8))}px`;
  const arriba = b.top - 12, abajo = innerHeight - b.bottom - 12, alto = menu.scrollHeight;
  if (arriba >= Math.min(alto, 360) || arriba >= abajo) {
    menu.style.top = 'auto';
    menu.style.bottom = `${innerHeight - b.top + 6}px`;
    menu.style.maxHeight = `${Math.max(160, arriba)}px`;
  } else {
    menu.style.bottom = 'auto';
    menu.style.top = `${b.bottom + 6}px`;
    menu.style.maxHeight = `${Math.max(160, abajo)}px`;
  }
}

function cerrarMenuVer() { const m = $('#rp-menu'); m.classList.remove('visible'); m.classList.add('oculto'); }

function elegirOpcionVer(valor) {
  const tipo = $('#rp-menu').dataset.tipo;
  const v = video();
  if (tipo === 'velocidad') { V.velocidad = +valor; v.playbackRate = V.velocidad; }
  if (tipo === 'subs') activarSubtitulo(+valor).then(actualizarBotonesVer);
  if (tipo === 'calidad' && V.hls) { V.hls.currentLevel = +valor < 0 ? -1 : +valor; if (+valor < 0) V.hls.nextLevel = -1; }
  if (tipo === 'audio' && V.hls) V.hls.audioTrack = +valor;
  if (tipo === 'audio' && !V.hls && V.datos?.modo === 'remux' && +valor !== (V.audioRemux || 0)) {
    // se vuelve a unir desde el segundo actual con la otra pista
    const t = tiempoVer(), reproduciendo = !v.paused;
    V.audioRemux = +valor; V.offset = t;
    v.src = srcRemux(t);
    if (reproduciendo) v.play().catch(() => {});
  }
  cerrarMenuVer();
  actualizarBotonesVer();
}

async function activarSubtitulo(n) {
  // <track src="http://127.0.0.1…"> es de otro origen que la página y el WebView lo bloquea (CORS); se descarga
  // con fetch y se le da como blob:, que sí es del mismo origen
  const el = video().querySelectorAll('track')[n];
  const sub = V.datos?.subtitulos?.[n];
  if (el && sub && !el.dataset.cargado) {
    el.dataset.cargado = '1';
    try {
      const r = await fetch(sub.src);
      const texto = r.ok ? await r.text() : '';
      if (!/-->/.test(texto)) throw new Error(String(r.status));
      el.src = URL.createObjectURL(new Blob([texto], { type: 'text/vtt' }));
    } catch {
      delete el.dataset.cargado;
      anotarErrorUi(`Subtítulos «${sub.nombre}» no se pudieron cargar`, 'info');
      toast(/traducción automática/.test(sub.nombre)
        ? 'YouTube no dejó descargar esa traducción automática ahora (limita cuántas se piden). Prueba en un rato u otro idioma.'
        : 'No se pudieron cargar los subtítulos.', 'err');
      return;   // se queda la pista que había
    }
  }
  const pistas = video().textTracks;
  for (let i = 0; i < pistas.length; i++) pistas[i].mode = i === n ? 'showing' : 'disabled';
  V.subActual = n;
}

/* ---------- gestos táctiles (celular): un toque muestra u oculta los controles, doble toque a un lado = ±10 s ---------- */
const esAndroid = () => document.documentElement.classList.contains('android');
function gestosActivos() {
  return (esAndroid() || matchMedia('(hover: none) and (pointer: coarse)').matches) && S.ajustes?.ver_gestos !== false;
}
let toqueTimer = null, ultimoToque = 0, ladoToque = null, saltoTimer = null;
function toqueGesto(e) {
  const r = $('#reproductor').getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width;
  const lado = x < 0.38 ? 'izq' : x > 0.62 ? 'der' : null;
  const ahora = Date.now();
  if (lado && lado === ladoToque && ahora - ultimoToque < 320) {   // doble toque (o más) en el mismo lado
    clearTimeout(toqueTimer); toqueTimer = null;
    ultimoToque = ahora;
    V.saltoAcumulado = (V.saltoAcumulado || 0) + 10;
    saltarA(tiempoVer() + (lado === 'der' ? 10 : -10));
    const aviso = $(`#rp-salto-${lado}`);
    aviso.textContent = `${lado === 'der' ? '+' : '−'}${V.saltoAcumulado} s`;
    $$('.rp-salto').forEach(el => el.classList.toggle('visible', el === aviso));
    clearTimeout(saltoTimer);
    saltoTimer = setTimeout(() => { $$('.rp-salto').forEach(el => el.classList.remove('visible')); V.saltoAcumulado = 0; }, 700);
    return;
  }
  ultimoToque = ahora; ladoToque = lado;
  clearTimeout(toqueTimer);
  toqueTimer = setTimeout(() => {   // un solo toque: controles
    toqueTimer = null;
    const rp = $('#reproductor');
    if (rp.classList.contains('controles-visibles') && !video().paused) { clearTimeout(V.ocultarTimer); rp.classList.remove('controles-visibles'); cerrarMenuVer(); }
    else mostrarControles();
  }, lado ? 300 : 0);
}

/* ---------- pantalla completa (el reproductor llena la ventana y la ventana la pantalla) ---------- */
// En Android: el reproductor ocupa la pantalla con CSS y la app esconde las barras del sistema (y gira a horizontal)
function completaCss(activar, bloquearGiro = true) {
  V.completaCss = activar;
  if (!activar) V.completaPorGiro = false;
  document.body.classList.toggle('ver-completa-css', activar);
  $('[data-rp="completa"]').innerHTML = ico(activar ? 'minimizar' : 'maximizar');
  const v = video();
  const horizontal = !v.videoHeight || v.videoWidth >= v.videoHeight;
  try { window.JabsAndroid?.pantallaCompleta?.(activar, activar && bloquearGiro && horizontal); } catch { /* fuera de Android */ }
  mostrarControles();
}
window.salirCompletaVer = () => { if (V.completaCss) { completaCss(false); return true; } return false; };
if (window.matchMedia) {
  matchMedia('(orientation: landscape)').addEventListener('change', e => {
    if (!esAndroid() || !V.datos || S.vista !== 'ver') return;
    if (e.matches && !V.completaCss) { completaCss(true, false); V.completaPorGiro = true; }   // girar el teléfono
    else if (!e.matches && V.completaCss && V.completaPorGiro) completaCss(false);
  });
}

async function alternarCompletaVer() {
  if (esAndroid()) return completaCss(!V.completaCss);
  const rp = $('#reproductor');
  if (document.fullscreenElement) {
    await document.exitFullscreen().catch(() => {});
  } else {
    await rp.requestFullscreen().catch(() => {});
  }
}
document.addEventListener('fullscreenchange', () => {
  const activa = document.fullscreenElement === $('#reproductor');
  $('[data-rp="completa"]').innerHTML = ico(activa ? 'minimizar' : 'maximizar');
  if (activa !== !!V.ventanaCompleta) { V.ventanaCompleta = activa; API.alternar_pantalla_completa(); }
  document.body.classList.toggle('ver-completa', activa);
});

/* ---------- listas de reproducción (colecciones) ---------- */
async function verColeccion(id, indice = 0) {
  const r = await API.coleccion(id);
  if (!r.ok) return toast(esc(r.error), 'err');
  const c = r.coleccion;
  const items = c.items.filter(i => i.url || i.existe);
  if (!items.length) return toast('Esa colección no tiene nada que se pueda ver.', 'err');
  guardarProgresoVer();
  V.lista = items;
  V.coleccion = c.id;
  V.nombreLista = c.nombre;
  cerrarColecciones();
  irA('ver');
  $('#ver-lista').classList.remove('oculto');
  await abrirItemLista(Math.min(indice, items.length - 1), true);
}

/* El stack de Descargar como lista de reproducción (las playlists del stack se despliegan en sus videos) */
function elementosStack() {
  return (S.stack?.items || []).flatMap(i => {
    const d = i.datos || {};
    if (i.tipo === 'playlist') return (d.entradas || i.entradas || []).map(e => ({ url: e.url, titulo: e.titulo, miniatura: e.miniatura, duracion: e.duracion, uid: i.uid }));
    return [{ url: i.url, titulo: d.titulo || i.titulo, miniatura: d.miniatura || i.miniatura, duracion: d.duracion ?? i.duracion, uid: i.uid }];
  }).filter(e => e.url);
}

function verStack(uid = null) {
  const items = elementosStack();
  if (!items.length) return toast('El stack está vacío.', 'err');
  guardarProgresoVer();
  V.lista = items; V.coleccion = null; V.nombreLista = 'Stack';
  if (S.vista !== 'ver') irA('ver');
  $('#ver-lista').classList.remove('oculto');
  abrirItemLista(Math.max(0, uid ? items.findIndex(e => e.uid === uid) : 0));
}

async function verUnoDeColeccion(id, n) {
  const r = await API.coleccion(id);
  if (!r.ok) return toast(esc(r.error), 'err');
  const item = r.coleccion.items[n];
  if (!item || !(item.url || item.existe)) return toast('Ese elemento no se puede ver (¿se movió o borró el archivo?).', 'err');
  guardarProgresoVer();
  V.lista = [item]; V.coleccion = r.coleccion.id; V.nombreLista = r.coleccion.nombre;
  cerrarColecciones();
  if (S.vista !== 'ver') irA('ver');
  await abrirItemLista(0, true);   // con su progreso: «continúa donde lo dejaste»
}

function verUnoDelStack(uid) {
  const items = elementosStack().filter(e => e.uid === uid);   // una playlist del stack trae sus videos
  if (!items.length) return;
  guardarProgresoVer();
  V.lista = items; V.coleccion = null;
  V.nombreLista = items.length > 1 ? (S.stack.items.find(i => i.uid === uid)?.datos?.titulo || 'Playlist') : '';
  if (S.vista !== 'ver') irA('ver');
  abrirItemLista(0);
}

async function abrirItemLista(n, preguntarContinuar = false) {
  const item = V.lista[n];
  if (!item) return;
  guardarProgresoVer();   // el progreso del que dejas, antes de cambiar de elemento
  V.actual = n;
  pintarListaVer();
  const desde = preguntarContinuar && item.posicion > 10 && !item.visto ? item.posicion : 0;
  const ok = await verOrigen(item.url || item.ruta, { desde });
  if (ok && desde) toast(`Continúa donde lo dejaste (${fmt.dur(desde)}). <a data-accion="ver-desde-cero">Empezar desde el principio</a>`);
}

function siguienteVer(manual = false) {
  if (!V.lista.length) return;
  if (V.repetir === 'uno' && !manual) return saltarA(0), video().play();
  let n = V.aleatorio ? Math.floor(Math.random() * V.lista.length) : V.actual + 1;
  if (V.aleatorio && V.lista.length > 1 && n === V.actual) n = (n + 1) % V.lista.length;
  if (n >= V.lista.length) {
    if (V.repetir !== 'lista' && !manual) return;
    n = 0;
  }
  abrirItemLista(n, true);
}
function anteriorVer() {
  if (tiempoVer() > 5 || !V.lista.length) return saltarA(0);
  abrirItemLista(Math.max(0, V.actual - 1), true);
}

function guardarProgresoVer(final = false) {
  const item = itemActual();
  // solo si lo que suena es ese elemento (mientras carga el siguiente, el anterior aún podría estar sonando)
  if (!V.coleccion || !item || !V.datos || V.cargando || V.datos.origen !== (item.url || item.ruta)) return;
  const t = tiempoVer(), d = duracionVer();
  const visto = final || (d && t / d > 0.95);
  if (visto) { item.visto = true; item.posicion = 0; } else item.posicion = t;
  API.guardar_progreso(V.coleccion, item.url ? { url: item.url } : { ruta: item.ruta }, t, visto);
  V.guardado = Date.now();
}

// Los archivos de la Biblioteca no traen miniatura: se pide (la misma caché que la Biblioteca) solo para lo que se ve
const minisPedidas = new Map();
function miniaturaLocal(item) {
  const ruta = item.ruta;
  if (!ruta || item.miniatura) return;
  if (typeof B !== 'undefined' && B.minis[ruta]) { item.miniatura = B.minis[ruta]; return ponerMiniLocal(item); }
  if (!minisPedidas.has(ruta)) minisPedidas.set(ruta, Promise.resolve(API.biblioteca_miniatura(ruta)).catch(() => null));
  minisPedidas.get(ruta).then(src => {
    if (!src) return;
    if (typeof B !== 'undefined') B.minis[ruta] = src;
    item.miniatura = src;
    ponerMiniLocal(item);
  });
}
function ponerMiniLocal(item) {
  const n = V.lista.indexOf(item);
  const el = n >= 0 && document.querySelector(`#ver-lista [data-ver-item="${n}"] .vl-mini`);
  if (el && !el.querySelector('img')) { el.querySelector('svg')?.remove(); el.insertAdjacentHTML('afterbegin', `<img src="${item.miniatura}" alt="">`); }
  if (n === V.actual && V.datos && !V.datos.miniatura) {
    $('#reproductor').style.setProperty('--fondo-audio', `url("${item.miniatura}")`);
    $('#reproductor').classList.add('con-portada');
  }
}
let observadorMinisVer = null;
function observarMinisVer() {
  observadorMinisVer?.disconnect();
  const items = $$('#ver-lista [data-ver-item]').filter(el => { const i = V.lista[+el.dataset.verItem]; return i?.ruta && !i.miniatura; });
  if (!items.length) return;
  observadorMinisVer = new IntersectionObserver(entradas => {
    for (const en of entradas) {
      if (!en.isIntersecting) continue;
      observadorMinisVer.unobserve(en.target);
      const i = V.lista[+en.target.dataset.verItem];
      if (i) miniaturaLocal(i);
    }
  }, { rootMargin: '300px' });
  items.forEach(el => observadorMinisVer.observe(el));
}

function pintarListaVer() {
  const panel = $('#ver-lista');
  if (panel.classList.contains('oculto')) return;
  const cols = C.lista || [];
  panel.innerHTML = `
    <div class="pc-cabecera"><b>${V.lista.length ? esc(V.nombreLista || 'Lista') : 'Listas'}</b>
      <button class="btn chico icono" data-accion="ver-lista-cerrar" title="Ocultar">${ico('x', 'sm')}</button></div>
    ${V.lista.length ? `<div class="vl-controles">
        <button class="btn chico ${V.aleatorio ? 'primario' : ''}" data-accion="ver-aleatorio" title="Orden aleatorio">${ico('aleatorio', 'sm')}Aleatorio</button>
        <button class="btn chico ${V.repetir !== 'no' ? 'primario' : ''}" data-accion="ver-repetir" title="Repetir">${ico('repetir', 'sm')}${{ no: 'Sin repetir', lista: 'Repetir lista', uno: 'Repetir uno' }[V.repetir]}</button>
      </div>
      <div class="vl-items">${V.lista.map((i, n) => {
        const pct = i.posicion && i.duracion ? Math.min(100, i.posicion / i.duracion * 100) : i.visto ? 100 : 0;
        return `<div class="vl-item ${n === V.actual ? 'activo' : ''} ${i.visto ? 'visto' : ''}" data-ver-item="${n}">
          <span class="vl-mini">${i.miniatura ? `<img src="${esc(i.miniatura)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ico(i.ruta ? 'file' : 'video', 'sm')}
            ${n === V.actual ? `<span class="vl-sonando">${ico('play', 'sm')}</span>` : ''}${pct ? `<span class="vl-progreso" style="width:${pct}%"></span>` : ''}</span>
          <span class="txt"><b class="no-traducir">${esc(i.titulo || i.url || i.ruta)}</b>
            <small>${i.visto ? `${ico('check', 'sm')}Visto` : i.posicion ? `Ibas por ${fmt.dur(i.posicion)}` : i.duracion ? fmt.dur(i.duracion) : ''}</small></span>
        </div>`;
      }).join('')}</div>` : ''}
    <div class="vl-colecciones">
      ${elementosStack().length ? `<div class="etiqueta-grupo">${ico('layers', 'sm')}Stack</div>
        <div class="pc-item ${V.nombreLista === 'Stack' && !V.coleccion ? 'activo' : ''}" data-accion="ver-stack">
          ${collage(elementosStack().map(e => e.miniatura).filter(Boolean).slice(0, 3))}<span class="txt"><b>Stack</b><small>${elementosStack().length} ${elementosStack().length === 1 ? 'elemento' : 'elementos'}</small></span>
          ${ico('play', 'sm')}</div>` : ''}
      <div class="etiqueta-grupo">${ico('bookmark', 'sm')}Tus colecciones</div>
      ${cols.map(c => `<div class="pc-item ${c.id === V.coleccion ? 'activo' : ''}" data-ver-coleccion="${esc(c.id)}">
          ${collage(c.miniaturas || [])}<span class="txt"><b class="no-traducir">${esc(c.nombre)}</b><small>${c.cantidad} ${c.cantidad === 1 ? 'elemento' : 'elementos'}</small></span>
          ${ico('play', 'sm')}</div>`).join('') || '<small class="dim">Aún no tienes colecciones.</small>'}
    </div>`;
  panel.querySelector('.vl-item.activo')?.scrollIntoView({ block: 'nearest' });
  observarMinisVer();
}

async function pintarInicioVer() {
  if (V.datos || V.cargando) return;
  const vistos = await API.vistos();
  if (V.datos || V.cargando) return;   // mientras tanto se empezó a cargar un video
  $('#ver-inicio').innerHTML = `<div class="vacio ver-vacio">
      <div class="circulo">${ico('tv')}</div>
      <b>Mira videos sin descargarlos</b>
      <small>Pega un enlace de YouTube u otro sitio, o abre un archivo de tu equipo. También puedes reproducir una colección entera como lista.</small>
    </div>
    ${vistos.length ? `<div class="etiqueta-grupo" style="margin-top:22px">${ico('clock', 'sm')}Vistos recientemente</div>
    <div class="ver-recientes">${vistos.map(v => `
      <div class="ver-reciente ${v.local && !v.existe ? 'perdido' : ''}" data-ver-origen="${esc(v.origen)}" title="${esc(v.titulo)}">
        <span class="vl-mini">${v.miniatura ? `<img src="${esc(v.miniatura)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ico(v.local ? 'file' : 'video', 'sm')}</span>
        <span class="txt"><b class="no-traducir">${esc(v.titulo || v.origen)}</b><small>${v.local ? 'Archivo de tu equipo' : esc(hostDe(v.origen))}${v.duracion ? ' · ' + fmt.dur(v.duracion) : ''}</small></span>
      </div>`).join('')}</div>` : ''}`;
}

/* ---------- eventos ---------- */
function iniciarVer() {
  const v = video();
  ['play', 'pause', 'volumechange'].forEach(ev => v.addEventListener(ev, () => { actualizarBotonesVer(); mostrarControles(); }));
  v.addEventListener('timeupdate', () => {
    pintarTiempo();
    if (Date.now() - V.guardado > 5000 && !v.paused) guardarProgresoVer();
  });
  v.addEventListener('progress', pintarTiempo);
  v.addEventListener('waiting', () => pintarEstadoVer('Cargando…', true));
  v.addEventListener('playing', () => {
    pintarEstadoVer('');
    if (V.datos && !V.inicioAnotado && V.inicioCarga) {   // al log: cuánto tardó en empezar de verdad
      V.inicioAnotado = true;
      anotarErrorUi(`Ver: empieza a reproducirse en ${((Date.now() - V.inicioCarga) / 1000).toFixed(1)} s (${V.datos.torrent ? 'torrent' : V.datos.modo})`, 'info');
    }
  });
  v.addEventListener('canplay', () => pintarEstadoVer(''));
  v.addEventListener('ended', () => {
    guardarProgresoVer(true);
    if (S.ajustes?.ver_siguiente !== false || V.repetir === 'uno') siguienteVer();
  });
  v.addEventListener('error', () => {
    if (V.datos && v.getAttribute('src') && !V.hls) errorVer('No se pudo reproducir este video aquí. Prueba a descargarlo.',
      `Error del reproductor: ${v.error?.code || '?'} ${v.error?.message || ''}\nModo: ${V.datos.modo}\nOrigen: ${V.datos.origen}`);
  });
  // En pausa: hls.js para de pedir segmentos al rato (no gasta datos de más); al reanudar sigue donde iba
  let pausaTimer = null;
  v.addEventListener('pause', () => { clearTimeout(pausaTimer); pausaTimer = setTimeout(() => { if (v.paused && V.hls) { V.hls.stopLoad(); V.hlsParado = V.hls; } }, 15000); });
  v.addEventListener('play', () => { clearTimeout(pausaTimer); if (V.hls && V.hlsParado === V.hls) { V.hlsParado = null; V.hls.startLoad(v.currentTime); } });
  v.addEventListener('seeking', () => { if (V.hls && V.hlsParado === V.hls) { V.hlsParado = null; V.hls.startLoad(v.currentTime); } });
  v.addEventListener('loadedmetadata', () => { actualizarBotonesVer(); pintarTiempo(); });
  const rp = $('#reproductor');
  rp.addEventListener('mousemove', () => { if (!gestosActivos()) mostrarControles(); });
  rp.addEventListener('pointerdown', e => {
    if (e.target === v || e.target.closest('#rp-centro') || e.target.closest('#rp-estado') || e.target.closest('.rp-salto')) return;
    if (rp.classList.contains('controles-visibles')) mostrarControles();
  });
  rp.addEventListener('click', e => {
    if (!(e.target === v || e.target.closest('#rp-centro') || e.target.closest('#rp-estado') || e.target.closest('.rp-salto'))) return;
    if ($('#rp-estado').classList.contains('error')) return;
    if (gestosActivos()) return toqueGesto(e);
    alternarPlay(); destello(v.paused ? 'pause' : 'play');
  });
  rp.addEventListener('dblclick', e => { if (e.target === v && !gestosActivos()) alternarCompletaVer(); });
  // línea de tiempo: clic y arrastrar
  const linea = $('#rp-linea');
  const posicion = e => { const r = linea.getBoundingClientRect(); return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)); };
  let arrastrando = false;
  linea.addEventListener('pointerdown', e => { arrastrando = true; linea.setPointerCapture(e.pointerId); });
  linea.addEventListener('pointermove', e => {
    const d = duracionVer();
    $('#rp-globo').textContent = fmt.dur(posicion(e) * d);
    $('#rp-globo').style.left = `${posicion(e) * 100}%`;
    if (arrastrando && V.datos?.modo !== 'remux') { $('#rp-avance').style.width = `${posicion(e) * 100}%`; $('#rp-bola').style.left = `${posicion(e) * 100}%`; }
  });
  linea.addEventListener('pointerup', e => { if (arrastrando) { arrastrando = false; saltarA(posicion(e) * duracionVer()); } });
  $('#rp-vol').addEventListener('input', e => {
    v.volume = +e.target.value; v.muted = v.volume === 0;
    try { localStorage.setItem('jabsdlp.volumen', v.volume); } catch { /* sin almacenamiento */ }
  });
  try { const vol = parseFloat(localStorage.getItem('jabsdlp.volumen')); if (vol >= 0 && vol <= 1) v.volume = vol; } catch { /* nada */ }
}

document.addEventListener('click', async e => {
  const t = e.target;
  const rpBtn = t.closest('[data-rp]');
  if (rpBtn) {
    const a = rpBtn.dataset.rp, v = video();
    if (a === 'play') return alternarPlay();
    if (a === 'atras') return saltarA(tiempoVer() - 10);
    if (a === 'adelante') return saltarA(tiempoVer() + 10);
    if (a === 'silencio') { v.muted = !v.muted; if (!v.muted && v.volume === 0) v.volume = 0.6; return; }
    if (a === 'siguiente') return siguienteVer(true);
    if (a === 'anterior') return anteriorVer();
    if (a === 'completa') return alternarCompletaVer();
    if (['velocidad', 'subs', 'calidad', 'audio'].includes(a)) return abrirMenuVer(a, rpBtn);
  }
  const opcion = t.closest('[data-rp-opcion]');
  if (opcion) return elegirOpcionVer(opcion.dataset.rpOpcion);
  if (!t.closest('#rp-menu')) cerrarMenuVer();
  const item = t.closest('[data-ver-item]');
  if (item) return abrirItemLista(+item.dataset.verItem, true);
  const col = t.closest('[data-ver-coleccion]');
  if (col) return verColeccion(col.dataset.verColeccion);
  const rec = t.closest('[data-ver-origen]');
  if (rec) { guardarProgresoVer(); V.lista = []; V.coleccion = null; return verOrigen(rec.dataset.verOrigen); }
  const accion = t.closest('[data-accion]')?.dataset.accion;
  switch (accion) {
    case 'ver-ir': guardarProgresoVer(); V.lista = []; V.coleccion = null; return verOrigen($('#ver-url').value);
    case 'ver-pegar': {
      const texto = ((await API.portapapeles()) || '').trim();
      if (!texto) return toast('El portapapeles está vacío.', 'err');
      $('#ver-url').value = texto; V.lista = []; V.coleccion = null;
      return verOrigen(texto);
    }
    case 'ver-archivo': {
      V.lista = []; V.coleccion = null;
      const r = await API.ver_abrir_archivo();
      if (!r) return;
      if (!r.ok) return pintarEstadoVer(r.error, false, true);
      $('#reproductor').classList.remove('oculto'); $('#ver-inicio').innerHTML = '';
      return cargarFuente(r.datos, 0);
    }
    case 'ver-guardar': {
      const d = V.datos;
      if (!d) return;
      const local = !/^(https?:\/\/|magnet:\?)/i.test(d.origen);
      return abrirColecciones({ agregar: [local ? { ruta: d.origen, titulo: d.titulo } : { url: d.origen, titulo: d.titulo, miniatura: d.miniatura, duracion: d.duracion, canal: d.canal }], nombre: d.titulo });
    }
    case 'ver-descargar':
      if (V.datos) { irA('descargar'); $('#url').value = V.datos.origen; analizar(); }
      return;
    case 'ver-lista-panel': $('#ver-lista').classList.toggle('oculto'); await cargarColecciones(); return pintarListaVer();
    case 'ver-lista-cerrar': $('#ver-lista').classList.add('oculto'); return;
    case 'ver-aleatorio': V.aleatorio = !V.aleatorio; return pintarListaVer();
    case 'ver-repetir': V.repetir = { no: 'lista', lista: 'uno', uno: 'no' }[V.repetir]; return pintarListaVer();
    case 'ver-desde-cero': return saltarA(0);
    case 'ver-cerrar': return cerrarVer();
    case 'ver-copiar-log': {
      const ok = await API.copiar($('#ver-detalle')?.dataset.texto || '');
      return toast(ok ? 'Log copiado.' : 'No se pudo copiar.', ok ? 'ok' : 'err');
    }
    case 'ver-stack': return verStack();
    case 'torrent-ver': if (S.analisis?.url) { V.lista = []; V.coleccion = null; return verOrigen(S.analisis.url); } return;
    case 'col-ver': return verColeccion(C.abierta);
  }
});

document.addEventListener('keydown', e => {
  if (S.vista !== 'ver' || !V.datos || e.target.closest('input, textarea, select') || e.ctrlKey || e.altKey || e.metaKey) return;
  const v = video();
  const teclas = {
    ' ': () => alternarPlay(), k: () => alternarPlay(),
    ArrowLeft: () => saltarA(tiempoVer() - 5), ArrowRight: () => saltarA(tiempoVer() + 5),
    j: () => saltarA(tiempoVer() - 10), l: () => saltarA(tiempoVer() + 10),
    ArrowUp: () => { v.muted = false; v.volume = Math.min(1, v.volume + 0.05); },
    ArrowDown: () => { v.volume = Math.max(0, v.volume - 0.05); },
    m: () => { v.muted = !v.muted; }, f: () => alternarCompletaVer(),
    c: () => { const n = (V.datos.subtitulos || []).length; if (n) { activarSubtitulo(V.subActual + 1 < n ? V.subActual + 1 : -1); actualizarBotonesVer(); } },
    n: () => siguienteVer(true), p: () => anteriorVer(),
  };
  const f = teclas[e.key] || teclas[e.key.toLowerCase()];
  if (f) { e.preventDefault(); f(); mostrarControles(); }
});
document.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.id === 'ver-url') { V.lista = []; V.coleccion = null; verOrigen(e.target.value); } });

// Al salir de la pestaña se pausa (y se guarda el progreso)
const irAOriginal = irA;
irA = function (vista) {   // eslint-disable-line no-global-assign
  if (S.vista === 'ver' && vista !== 'ver' && V.completaCss) completaCss(false);
  if (S.vista === 'ver' && vista !== 'ver' && V.datos) {
    guardarProgresoVer(); video().pause();
    if (V.datos.torrent) { limpiarReproductor(); V.datos = null; API.detener_ver(); clearInterval(temporizadorTorrent); }  // deja de compartir
  }
  irAOriginal(vista);
  if (vista === 'ver') { pintarInicioVer(); pintarListaVer(); }
};
TITULOS.ver = 'Ver';

// Android: «Compartir → Ver en JabsDLP» abre el enlace aquí
window.verCompartido = url => { guardarProgresoVer(); V.lista = []; V.coleccion = null; $('#ver-url').value = url; return verOrigen(url); };

function verLocal(ruta) { guardarProgresoVer(); V.lista = []; V.coleccion = null; return verOrigen(ruta); }

iniciarVer();

/* ---------- lo que suena, fuera de la app: notificación de Android y controles multimedia (Media Session) ---------- */
function infoMusica() {
  const v = video(), d = V.datos, item = V.lista[V.actual];
  if (!d) return null;
  let portada = d.miniatura || item?.miniatura || '';
  if (portada && !/^(data:image\/|https:\/\/)/.test(portada)) portada = '';
  const titulo = d.titulo || item?.titulo || '';
  const artista = d.canal || item?.canal || (V.lista.length > 1 ? V.nombreLista || '' : '');
  return {
    titulo, artista, portada, sonando: !v.paused || !!V.cargando, posicion: tiempoVer() || 0, velocidad: v.playbackRate || 1,
    duracion: (d.duracion || (isFinite(v.duration) ? v.duration : 0)) || 0,
    mantener: !!d.solo_audio || S.ajustes?.ver_video_fondo !== 'pausa',
    anterior: true, siguiente: V.lista.length > 1 && (V.aleatorio || V.repetir === 'lista' || V.actual < V.lista.length - 1),
  };
}
let musicaClave = '', musicaTimer = null;
// Al pasar de una canción a otra hay una pausa de un instante: se espera un poco antes de avisar de una pausa
// para que la notificación no parpadee (y Android no deje de tratar la app como «reproduciendo»)
function avisarMusica() {
  clearTimeout(musicaTimer);
  const info = infoMusica();
  if (info && !info.sonando && musicaClave.includes('"sonando":true')) { musicaTimer = setTimeout(enviarMusica, 1500); return; }
  enviarMusica();
}
function enviarMusica() {
  const activo = S.ajustes?.ver_notificacion !== false;
  const info = activo ? infoMusica() : null;
  const clave = info ? JSON.stringify({ ...info, posicion: Math.round(info.posicion / 5) }) : '';
  if (clave === musicaClave) return;
  musicaClave = clave;
  try { window.JabsAndroid?.musica?.(info ? JSON.stringify(info) : ''); } catch { /* fuera de Android */ }
  const ms = navigator.mediaSession;
  if (!ms) return;
  try {
    if (!info) { ms.metadata = null; ms.playbackState = 'none'; return; }
    ms.metadata = new MediaMetadata({ title: info.titulo, artist: info.artista, artwork: info.portada ? [{ src: info.portada }] : [] });
    ms.playbackState = info.sonando ? 'playing' : 'paused';
  } catch { /* sin Media Session */ }
}
window.controlMusica = (orden, valor) => {
  const v = video();
  if (!V.datos) return;
  if (orden === 'play') v.play().catch(() => {});
  else if (orden === 'pausa') v.pause();
  else if (orden === 'siguiente') siguienteVer(true);
  else if (orden === 'anterior') anteriorVer();
  else if (orden === 'ir' && valor != null) saltarA(+valor);
};
(() => {
  const v = video();
  ['play', 'pause', 'loadedmetadata', 'seeked', 'ratechange', 'emptied'].forEach(ev => v.addEventListener(ev, () => setTimeout(avisarMusica, 0)));
  const ms = navigator.mediaSession;
  if (ms) {
    const acciones = { play: 'play', pause: 'pausa', nexttrack: 'siguiente', previoustrack: 'anterior' };
    for (const [a, o] of Object.entries(acciones)) { try { ms.setActionHandler(a, () => window.controlMusica(o)); } catch { /* no soportada */ } }
    try { ms.setActionHandler('seekto', e => window.controlMusica('ir', e.seekTime)); } catch { /* no soportada */ }
  }
})();
