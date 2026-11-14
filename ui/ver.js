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
function tiempoVer() { return (V.datos?.modo === 'remux' ? V.offset : 0) + (video().currentTime || 0); }

function saltarA(t) {
  const d = duracionVer();
  t = Math.max(0, d ? Math.min(t, d - 0.5) : t);
  const v = video();
  if (V.datos?.modo === 'remux') {
    const reproduciendo = !v.paused;
    V.offset = t;
    v.src = `${V.datos.src}?t=${t.toFixed(2)}`;
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
  video().pause();
  V.cargando = true;
  pintarEstadoVer(esTorrent ? 'Conectando con el torrent…' : 'Preparando…', true);
  $('#reproductor').classList.remove('oculto');
  $('#ver-inicio').innerHTML = '';
  let r;
  try { r = await API.ver(origen, opciones.referer || null); } catch (e) { r = { ok: false, error: String(e) }; }
  V.cargando = false;
  if (!r.ok) {
    pintarEstadoVer(r.error, false, true);
    $('#ver-info').innerHTML = '';
    return false;
  }
  cargarFuente(r.datos, opciones.desde || 0);
  return true;
}

function limpiarReproductor() {
  const v = video();
  if (V.hls) { V.hls.destroy(); V.hls = null; }
  v.pause();
  v.removeAttribute('src');
  [...v.querySelectorAll('track')].forEach(t => t.remove());
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
  $('#reproductor').style.setProperty('--fondo-audio', datos.miniatura ? `url("${datos.miniatura.replace(/"/g, '')}")` : 'none');
  if (datos.modo === 'hls') {
    if (window.Hls?.isSupported()) {
      V.hls = new Hls({ maxBufferLength: 40, enableWorker: true });
      V.hls.on(Hls.Events.ERROR, (_, e) => { if (e.fatal) pintarEstadoVer('No se pudo cargar el video (error de red o enlace caducado).', false, true); });
      V.hls.on(Hls.Events.MANIFEST_PARSED, () => { if (desde) v.currentTime = desde; v.play().catch(() => {}); });
      V.hls.loadSource(datos.src);
      V.hls.attachMedia(v);
    } else {
      v.src = datos.src;
    }
  } else if (datos.modo === 'remux') {
    V.offset = desde || 0;
    v.src = `${datos.src}?t=${V.offset.toFixed(2)}`;
  } else {
    v.src = datos.src;
    if (desde) v.addEventListener('loadedmetadata', () => { v.currentTime = desde; }, { once: true });
  }
  (datos.subtitulos || []).forEach((s, i) => {
    const t = document.createElement('track');
    Object.assign(t, { kind: 'subtitles', label: s.nombre, srclang: (s.idioma || 'und').slice(0, 8), src: s.src });
    v.appendChild(t);
    t.track.mode = 'disabled';
    t.dataset.n = i;
  });
  if (datos.modo !== 'hls') v.play().catch(() => {});
  pintarEstadoVer('', false);
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
  const enLista = V.lista.length ? `<span>${ico('playlist', 'sm')}${esc(V.nombreLista || 'Lista')} · ${V.actual + 1} de ${V.lista.length}</span>` : '';
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
  $('#rp-calidad').classList.toggle('oculto', !(V.hls?.levels?.length > 1));
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
  if (tipo === 'subs') opciones = [[-1, 'Desactivados', V.subActual < 0], ...(V.datos?.subtitulos || []).map((s, i) => [i, s.nombre, V.subActual === i])];
  if (tipo === 'calidad') {
    const niveles = V.hls?.levels || [];
    opciones = [[-1, 'Automática', V.hls?.autoLevelEnabled], ...niveles.map((l, i) => [i, l.height ? `${l.height}p` : `${Math.round(l.bitrate / 1000)} kbps`, !V.hls.autoLevelEnabled && V.hls.currentLevel === i])]
      .sort((a, b) => (b[0] < 0) - (a[0] < 0) || (niveles[b[0]]?.height || 0) - (niveles[a[0]]?.height || 0));
  }
  menu.dataset.tipo = tipo;
  menu.innerHTML = opciones.map(([v, t, on]) => `<button class="rp-opcion ${on ? 'on' : ''}" data-rp-opcion="${v}">${on ? ico('check', 'sm') : '<span class="ico sm"></span>'}<span class="no-traducir-num">${esc(t)}</span></button>`).join('');
  menu.classList.add('visible');
  menu.classList.remove('oculto');
  const rp = $('#reproductor').getBoundingClientRect(), b = ancla.getBoundingClientRect();
  menu.style.right = `${Math.max(8, rp.right - b.right)}px`;
}
function cerrarMenuVer() { const m = $('#rp-menu'); m.classList.remove('visible'); m.classList.add('oculto'); }

function elegirOpcionVer(valor) {
  const tipo = $('#rp-menu').dataset.tipo;
  const v = video();
  if (tipo === 'velocidad') { V.velocidad = +valor; v.playbackRate = V.velocidad; }
  if (tipo === 'subs') activarSubtitulo(+valor);
  if (tipo === 'calidad') { if (+valor < 0) V.hls.currentLevel = -1; else V.hls.currentLevel = +valor; }
  cerrarMenuVer();
  actualizarBotonesVer();
}

function activarSubtitulo(n) {
  const pistas = video().textTracks;
  for (let i = 0; i < pistas.length; i++) pistas[i].mode = i === n ? 'showing' : 'disabled';
  V.subActual = n;
}

/* ---------- pantalla completa (el reproductor llena la ventana y la ventana la pantalla) ---------- */
async function alternarCompletaVer() {
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
      <div class="etiqueta-grupo">${ico('bookmark', 'sm')}Tus colecciones</div>
      ${cols.map(c => `<div class="pc-item ${c.id === V.coleccion ? 'activo' : ''}" data-ver-coleccion="${esc(c.id)}">
          ${collage(c.miniaturas || [])}<span class="txt"><b class="no-traducir">${esc(c.nombre)}</b><small>${c.cantidad} ${c.cantidad === 1 ? 'elemento' : 'elementos'}</small></span>
          ${ico('play', 'sm')}</div>`).join('') || '<small class="dim">Aún no tienes colecciones.</small>'}
    </div>`;
  panel.querySelector('.vl-item.activo')?.scrollIntoView({ block: 'nearest' });
}

async function pintarInicioVer() {
  if (V.datos || V.cargando) return;
  const vistos = await API.vistos();
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
  v.addEventListener('playing', () => pintarEstadoVer(''));
  v.addEventListener('canplay', () => pintarEstadoVer(''));
  v.addEventListener('ended', () => { guardarProgresoVer(true); siguienteVer(); });
  v.addEventListener('error', () => { if (V.datos && v.getAttribute('src')) pintarEstadoVer('No se pudo reproducir este video aquí. Prueba a descargarlo.', false, true); });
  v.addEventListener('loadedmetadata', () => { actualizarBotonesVer(); pintarTiempo(); });
  const rp = $('#reproductor');
  rp.addEventListener('mousemove', mostrarControles);
  rp.addEventListener('click', e => {
    if (e.target === v || e.target.closest('#rp-centro') || e.target.closest('#rp-estado')) { alternarPlay(); destello(v.paused ? 'pause' : 'play'); }
  });
  rp.addEventListener('dblclick', e => { if (e.target === v) alternarCompletaVer(); });
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
    if (['velocidad', 'subs', 'calidad'].includes(a)) return abrirMenuVer(a, rpBtn);
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
      const local = !/^https?:\/\//i.test(d.origen);
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
  if (S.vista === 'ver' && vista !== 'ver' && V.datos) {
    guardarProgresoVer(); video().pause();
    if (V.datos.torrent) { limpiarReproductor(); V.datos = null; API.detener_ver(); clearInterval(temporizadorTorrent); }  // deja de compartir
  }
  irAOriginal(vista);
  if (vista === 'ver') { pintarInicioVer(); pintarListaVer(); }
};
TITULOS.ver = 'Ver';

function verLocal(ruta) { guardarProgresoVer(); V.lista = []; V.coleccion = null; return verOrigen(ruta); }

iniciarVer();
