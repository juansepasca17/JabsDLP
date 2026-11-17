/* JabsDLP 1.6: modo stack, captura rápida, Colecciones (panel) y Biblioteca.
   Usa las utilidades globales de app.js ($, $$, esc, ico, fmt, toast, S, API, irA, guardarAjuste…). */

/* ================= confirmación genérica (reutiliza el modal de avisos) ================= */
function confirmar(titulo, texto, si = 'Aceptar') {
  const modal = $('#modal');
  const etiqueta = modal.querySelector('.no-mostrar');
  const botonSi = modal.querySelector('[data-modal="si"]');
  const textoSi = botonSi.textContent;
  $('#modal-titulo span').textContent = titulo;
  $('#modal-cuerpo').innerHTML = `<p>${esc(texto)}</p>`;
  etiqueta.classList.add('oculto');
  botonSi.textContent = si;
  modal.classList.remove('oculto');
  botonSi.focus();
  const abierto = performance.now();
  return new Promise(resolver => {
    const cerrar = ok => {
      modal.classList.add('oculto');
      etiqueta.classList.remove('oculto');
      botonSi.textContent = textoSi;
      modal.removeEventListener('click', alClic);
      document.removeEventListener('keydown', alTecla, true);
      resolver(ok);
    };
    const alClic = e => {
      if (performance.now() - abierto < 350) return;
      const b = e.target.closest('[data-modal]');
      if (b) cerrar(b.dataset.modal === 'si');
    };
    const alTecla = e => { if (e.key === 'Escape') { e.stopPropagation(); cerrar(false); } };
    modal.addEventListener('click', alClic);
    document.addEventListener('keydown', alTecla, true);
  });
}

function pedirTexto(titulo, valor = '', si = 'Guardar') {
  const modal = $('#modal');
  const etiqueta = modal.querySelector('.no-mostrar');
  const botonSi = modal.querySelector('[data-modal="si"]');
  const textoSi = botonSi.textContent;
  $('#modal-titulo span').textContent = titulo;
  $('#modal-cuerpo').innerHTML = `<input class="entrada" id="modal-texto" maxlength="80" spellcheck="false" value="${esc(valor)}">`;
  etiqueta.classList.add('oculto');
  botonSi.textContent = si;
  modal.classList.remove('oculto');
  const campo = $('#modal-texto');
  campo.focus(); campo.select();
  const abierto = performance.now();
  return new Promise(resolver => {
    const cerrar = ok => {
      const v = campo.value.trim();
      modal.classList.add('oculto');
      etiqueta.classList.remove('oculto');
      botonSi.textContent = textoSi;
      modal.removeEventListener('click', alClic);
      document.removeEventListener('keydown', alTecla, true);
      resolver(ok && v ? v : null);
    };
    const alClic = e => {
      if (performance.now() - abierto < 350) return;
      const b = e.target.closest('[data-modal]');
      if (b) cerrar(b.dataset.modal === 'si');
    };
    const alTecla = e => {
      if (e.key === 'Escape') { e.stopPropagation(); cerrar(false); }
      if (e.key === 'Enter' && e.target === campo) { e.preventDefault(); cerrar(true); }
    };
    modal.addEventListener('click', alClic);
    document.addEventListener('keydown', alTecla, true);
  });
}

/* ================= MODO STACK ================= */
// El área principal muestra el elemento seleccionado igual que un análisis normal (video con sus opciones o
// playlist con su lista); el stack es un panel lateral fijo a la derecha. Cada elemento guarda su propia
// configuración (preferencias, formato elegido, videos marcados de una playlist…).
S.stack = { nombre: '', items: [], sel: null };
S.stackAbierto = false;   // el panel empieza plegado: se despliega con la pestaña del borde derecho

function nombreStackPorDefecto() {
  const d = new Date(), p = n => String(n).padStart(2, '0');
  return `Stack ${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}-${p(d.getMinutes())}`;
}

function esPlaylistUrl(url) { return /[?&]list=|\/playlist|\/sets\/|\/album\//i.test(url); }
// El stack acepta videos, playlists, magnets, .torrent y enlaces directos (.m3u8/.mpd, archivos)
function apilable(url) { return /^(https?:\/\/|magnet:\?)/i.test(url); }
function esTorrentUrl(url) { return /^magnet:\?/i.test(url) || /\.torrent$/i.test(url.split(/[?#]/)[0]); }
function hostDe(url) { try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; } }

let temporizadorStack = null;
function guardarStackLuego() {
  clearTimeout(temporizadorStack);
  temporizadorStack = setTimeout(() => {
    guardarEstadoActual();
    API.guardar_stack({ nombre: S.stack.nombre, items: S.stack.items.filter(i => i.estado !== 'enviado').map(itemParaGuardar) });
  }, 400);
}

function itemParaGuardar(i) {
  const d = i.datos || {};
  const base = { url: i.url, tipo: i.tipo, titulo: d.titulo || i.titulo, miniatura: d.miniatura || i.miniatura,
                 duracion: d.duracion ?? i.duracion, canal: d.canal || i.canal, incluir: i.incluir,
                 prefs: i.est.prefs || null, spec: specDe(i) };
  if (i.tipo === 'playlist') {
    base.entradas = (d.entradas || i.entradas || []).map(e => ({ url: e.url, titulo: e.titulo, miniatura: e.miniatura, duracion: e.duracion, indice: e.indice }));
    base.marcados = i.est.plSel ? [...i.est.plSel] : i.marcados || null;
  }
  return base;
}

function specDe(i) { return i.est.modoSel === 'manual' && i.est.seleccion ? i.est.seleccion : i.spec || null; }

function nuevoItem(url, tipo) {
  return { uid: Math.random().toString(36).slice(2), url, tipo, estado: 'analizando', datos: null, incluir: true,
           est: { prefs: { ...S.prefs } } };
}

async function agregarAlStack(urls) {
  urls = urls.filter(apilable);
  if (!urls.length) return false;
  if (!S.stack.nombre) S.stack.nombre = nombreStackPorDefecto();
  let nuevos = 0, ultimo = null;
  for (const url of urls) {
    if (S.stack.items.some(i => i.url === url)) continue;
    const item = nuevoItem(url, esTorrentUrl(url) ? 'torrent' : esPlaylistUrl(url) || S.modo === 'playlist' ? 'playlist' : 'video');
    S.stack.items.push(item);
    ultimo = item;
    nuevos++;
    analizarItem(item);
  }
  if (!nuevos) { toast('Ese enlace ya está en el stack.'); return true; }
  if (!S.stack.sel || !itemSel()) seleccionarStack(ultimo.uid);
  else renderDescargar();
  toast(nuevos === 1 ? 'Añadido al stack.' : `${nuevos} enlaces añadidos al stack.`, 'ok');
  const tab = $('#tab-stack');
  if (tab) { tab.classList.remove('aviso-nuevo'); void tab.offsetWidth; tab.classList.add('aviso-nuevo'); }
  guardarStackLuego();
  return true;
}

async function analizarItem(item) {
  item.estado = 'analizando';
  let r;
  try { r = await API.analizar(item.url, item.tipo, item.est.prefs || S.prefs); } catch (e) { r = { ok: false, error: String(e) }; }
  if (!S.stack.items.includes(item)) return;
  if (r.ok && (r.datos.tipo === 'torrent' || r.datos.tipo === 'manifiesto')) {
    item.datos = r.datos;
    item.tipo = r.datos.tipo;
    item.estado = 'listo';
    if (S.ajustes.stack_auto) await enviarItems([item]);
  } else if (r.ok && (r.datos.tipo === 'video' || r.datos.tipo === 'playlist')) {
    item.datos = r.datos;
    item.tipo = r.datos.tipo;
    item.estado = 'listo';
    if (item.tipo === 'video') {
      item.est.calc = { recomendado: r.datos.recomendado, opciones: r.datos.opciones, audios: r.datos.audios,
                        audio_elegido: r.datos.audio_elegido, encoder: r.datos.encoder, aviso_idioma: r.datos.aviso_idioma };
      if (item.spec) { item.est.modoSel = 'manual'; item.est.seleccion = item.spec; }
    } else {
      const marcados = item.marcados ? new Set(item.marcados) : null;
      item.est.plSel = new Set(r.datos.entradas.filter(e => marcados ? marcados.has(e.indice) : !e.ya_descargado).map(e => e.indice));
    }
    if (S.ajustes.stack_auto) await enviarItems([item]);
  } else {
    item.estado = 'error';
    item.error = r.ok ? 'Este enlace no se puede apilar (¿es un lote de varios enlaces?).' : r.error;
  }
  if (S.stack.sel === item.uid) cargarItem(item);
  guardarStackLuego();
  if (S.vista === 'descargar') renderDescargar();
}

function itemSel() { return S.stack.items.find(i => i.uid === S.stack.sel) || null; }

// Guarda en el elemento lo que el usuario cambió en la vista principal
function guardarEstadoActual() {
  const i = itemSel();
  if (!i || i.estado !== 'listo' || S.analisis !== i.datos) return;
  Object.assign(i.est, { prefs: { ...S.prefs }, seleccion: S.seleccion, modoSel: S.modoSel, audioId: S.audioId,
                         verManual: S.verManual, recorte: S.recorte, quitarAnuncios: S.quitarAnuncios, sponsor: S.sponsor,
                         calc: S.calc, plSel: i.tipo === 'playlist' ? new Set(S.plSel) : i.est.plSel });
}

// Pone el elemento en la vista principal (como si se acabara de analizar)
function cargarItem(i) {
  S.cargando = i.estado === 'analizando';
  S.error = i.estado === 'error' ? i.error : null;
  S.analisis = i.estado === 'listo' ? i.datos : null;
  const e = i.est;
  if (e.prefs) S.prefs = { ...e.prefs };
  S.calc = e.calc || null;
  S.seleccion = e.seleccion || null;
  S.modoSel = e.modoSel || (S.ajustes.recomendacion === false ? 'manual' : 'auto');
  S.audioId = e.audioId || null;
  S.verManual = !!e.verManual;
  S.recorte = e.recorte || null;
  S.quitarAnuncios = !!e.quitarAnuncios;
  S.sponsor = e.sponsor || null;
  S.plSel = new Set(e.plSel || []);
}

function seleccionarStack(uid) {
  guardarEstadoActual();
  S.stack.sel = uid;
  const i = itemSel();
  if (!i) return renderDescargar();
  if (i.estado === 'guardado') analizarItem(i);   // venía de stack.json: se analiza al abrirlo
  cargarItem(i);
  renderDescargar();
}

async function enviarItems(items) {
  guardarEstadoActual();
  const lista = [];
  for (const i of items) {
    const d = i.datos || {};
    const prefs = i.est.prefs || null;
    if (i.tipo === 'playlist') {
      const entradas = d.entradas || i.entradas || [];
      const marcados = i.est.plSel || (i.marcados ? new Set(i.marcados) : null);
      entradas.filter(e => !marcados || marcados.has(e.indice))
        .forEach(e => lista.push({ url: e.url, titulo: e.titulo, miniatura: e.miniatura, duracion: e.duracion, canal: e.canal || d.canal, prefs }));
    } else if (i.tipo === 'torrent' || i.tipo === 'manifiesto' || esTorrentUrl(i.url)) {
      // torrents y enlaces directos: van con su propio tipo (aria2 o el modo .m3u8/.mpd con Referer)
      lista.push({ url: i.url, titulo: d.titulo || i.titulo, tipo: esTorrentUrl(i.url) ? 'torrent' : 'manifiesto',
                   referer: d.referer || null, duracion: d.duracion ?? i.duracion });
    } else {
      lista.push({ url: i.url, titulo: d.titulo || i.titulo, miniatura: d.miniatura || i.miniatura, duracion: d.duracion ?? i.duracion,
                   canal: d.canal || i.canal, prefs, spec: specDe(i) });
    }
  }
  if (!lista.length) { toast('No hay videos marcados para descargar.', 'err'); return false; }
  const r = await API.descargar({ tipo: 'stack', nombre: S.stack.nombre || nombreStackPorDefecto(), prefs: S.prefs, items: lista });
  if (!r.ok) { toast(esc(r.error), 'err'); return false; }
  items.forEach(i => { i.estado = 'enviado'; });
  refrescarCola();
  return r.agregados;
}

function marcarActualEnviado() {
  const i = itemSel();
  if (i) { i.estado = 'enviado'; guardarStackLuego(); pintarPanelStack(); }
}

async function descargarStack() {
  const elegidos = S.stack.items.filter(i => i.incluir && (i.estado === 'listo' || i.estado === 'guardado'));
  if (!elegidos.length) return;
  const n = await enviarItems(elegidos);
  if (!n) return;
  toast(`${n} ${n === 1 ? 'descarga añadida' : 'descargas añadidas'} a la cola. <a data-vista="cola">Ver cola</a>`, 'ok');
  S.stack.items = S.stack.items.filter(i => i.estado !== 'enviado');
  S.stack.sel = null;
  if (S.stack.items.length) seleccionarStack(S.stack.items[0].uid);
  else { S.stack.nombre = ''; S.analisis = null; S.error = null; S.cargando = false; renderDescargar(); }
  guardarStackLuego();
}

function quitarDelStack(uid) {
  const pos = S.stack.items.findIndex(i => i.uid === uid);
  if (pos < 0) return;
  S.stack.items.splice(pos, 1);
  if (S.stack.sel === uid) {
    S.stack.sel = null;
    const sig = S.stack.items[pos] || S.stack.items[pos - 1];
    if (sig) return seleccionarStack(sig.uid), guardarStackLuego();
    S.analisis = null; S.error = null; S.cargando = false;
  }
  guardarStackLuego();
  renderDescargar();
}

async function cargarStackGuardado() {
  const s = await API.cargar_stack();
  if (!s?.items?.length) return;
  S.stack = {
    nombre: s.nombre || '', sel: null,
    items: s.items.map(d => ({
      uid: Math.random().toString(36).slice(2), url: d.url, tipo: ['playlist', 'torrent', 'manifiesto'].includes(d.tipo) ? d.tipo : 'video',
      estado: 'guardado', datos: null, incluir: d.incluir !== false, titulo: d.titulo, miniatura: d.miniatura,
      duracion: d.duracion, canal: d.canal, spec: d.spec || null, entradas: d.entradas || null, marcados: d.marcados || null,
      est: { prefs: d.prefs || null },
    })),
  };
}

/* ---------- panel lateral ---------- */
function etiquetaItem(i) {
  const p = i.est.prefs, spec = specDe(i);
  if (spec) return 'Manual';
  if (p?.tipo === 'audio') return 'Audio';
  if (p?.resolucion && p.resolucion !== 'auto') return `${p.resolucion}p`;
  return '';
}

function filaPanelStack(i, n) {
  const d = i.datos || {};
  const titulo = d.titulo || i.titulo || i.url;
  const mini = d.miniatura || i.miniatura;
  const cantidad = i.tipo === 'playlist' ? (d.entradas || i.entradas || []).length : 0;
  const marcados = i.tipo === 'playlist' ? (i.est.plSel ? i.est.plSel.size : (i.marcados || []).length || cantidad) : 0;
  const sub = i.estado === 'analizando' ? 'Analizando…'
    : i.estado === 'error' ? 'Error: ' + (i.error || '')
    : i.estado === 'enviado' ? 'En la cola'
    : i.tipo === 'playlist' ? `Playlist · ${marcados}/${cantidad} videos`
    : i.tipo === 'torrent' ? 'Torrent · sin seed'
    : i.tipo === 'manifiesto' ? `Enlace directo · ${hostDe(i.url)}`
    : `${hostDe(i.url)}${(d.duracion ?? i.duracion) ? ' · ' + fmt.dur(d.duracion ?? i.duracion) : ''}`;
  const etiqueta = etiquetaItem(i);
  return `<div class="ps-item ${S.stack.sel === i.uid ? 'activo' : ''} ${i.estado}" data-stack-ver="${i.uid}">
      <span class="casilla ${i.incluir ? 'on' : ''}" data-stack-incluir="${i.uid}" title="Incluir al descargar todo"></span>
      <span class="ps-mini">${mini ? `<img src="${esc(mini)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ico(i.tipo === 'playlist' ? 'playlist' : 'video', 'sm')}
        ${i.tipo === 'playlist' ? `<span class="ps-pl">${ico('playlist', 'sm')}${cantidad || ''}</span>` : ''}
        ${i.estado === 'analizando' ? `<span class="ps-cargando">${ico('loader', 'sm spin')}</span>` : ''}</span>
      <span class="txt"><b class="no-traducir" title="${esc(titulo)}">${esc(titulo)}</b><small class="${i.estado === 'error' ? 'err-texto' : ''}">${esc(sub)}</small></span>
      ${etiqueta ? `<span class="insignia acento">${esc(etiqueta)}</span>` : ''}
      ${i.tipo !== 'torrent' && i.estado !== 'error' ? `<button class="btn chico icono fantasma" data-stack-tv="${i.uid}" title="Ver en la pestaña Ver">${ico('tv', 'sm')}</button>` : ''}
      <button class="btn chico icono fantasma" data-stack-quitar="${i.uid}" title="Quitar del stack">${ico('x', 'sm')}</button>
    </div>`;
}

function pintarPanelStack() {
  let panel = $('#panel-stack');
  if (!panel) {
    panel = document.createElement('aside');
    panel.id = 'panel-stack';
    panel.className = 'panel-stack';
    document.body.appendChild(panel);
  }
  let pestana = $('#tab-stack');
  if (!pestana) {
    pestana = document.createElement('button');
    pestana.id = 'tab-stack';
    pestana.className = 'tab-stack';
    pestana.dataset.accion = 'stack-abrir';
    document.body.appendChild(pestana);
  }
  // con enlaces en el stack, su pestaña se ve aunque el modo stack esté apagado (más tenue): así no se olvida.
  // Tocarla vuelve a activar el modo stack y abre el panel.
  const hay = S.vista === 'descargar' && S.stack.items.length > 0;
  const activo = !!S.ajustes?.modo_stack;
  const visible = hay && activo && S.stackAbierto;
  document.body.classList.toggle('con-stack', !!visible);
  panel.classList.toggle('abierto', !!visible);
  pestana.classList.toggle('oculto', !hay || visible);
  pestana.classList.toggle('apagado', hay && !activo);
  pestana.title = activo ? 'Abrir el stack (Ctrl + J)' : 'El stack sigue ahí: tócalo para volver a usarlo';
  const analizando = S.stack.items.some(i => i.estado === 'analizando');
  pestana.innerHTML = `${ico('chevron-izq', 'sm')}${ico(analizando ? 'loader' : 'layers', analizando ? 'sm spin' : 'sm')}<span>Stack</span><b>${S.stack.items.length}</b>`;
  pestana.title = 'Mostrar el stack';
  if (!visible) return;
  const incluidos = S.stack.items.filter(i => i.incluir && i.estado !== 'error' && i.estado !== 'enviado');
  const scroll = panel.querySelector('.ps-lista')?.scrollTop;
  panel.innerHTML = `
    <div class="pc-cabecera"><span class="ps-titulo">${ico('layers', 'sm')}<b>Stack</b> <span class="cuenta">(${S.stack.items.length})</span></span>
      <button class="btn chico icono" data-accion="stack-cerrar" title="Plegar el stack">${ico('chevron-der', 'sm')}</button></div>
    <div class="ps-carpeta"><label class="campo" style="margin:0"><span>Carpeta</span>
      <input class="entrada" id="stack-nombre" spellcheck="false" maxlength="120" value="${esc(S.stack.nombre)}"></label></div>
    <div class="ps-lista">${S.stack.items.map((i, n) => filaPanelStack(i, n + 1)).join('')}</div>
    <div class="ps-pie">
      <button class="btn pildora primario ps-descargar" data-accion="stack-descargar" ${incluidos.length ? '' : 'disabled'}>${ico('download')}Descargar todo (${incluidos.length})</button>
      <div class="ps-secundarias">
        <button class="btn chico" data-accion="stack-coleccion">${ico('bookmark', 'sm')}Guardar como colección</button>
        <button class="btn chico peligro" data-accion="stack-vaciar">${ico('trash', 'sm')}Vaciar</button>
      </div>
    </div>`;
  if (scroll) panel.querySelector('.ps-lista').scrollTop = scroll;
}

function renderStack() {
  // Stack vacío: mensaje en el área principal
  let cont = $('#stack-vista');
  if (!cont) {
    cont = document.createElement('div');
    cont.id = 'stack-vista';
    $('#columnas').after(cont);
  }
  $('#inicio').innerHTML = '';
  $('#columnas').classList.add('oculto');
  cont.classList.remove('oculto');
  cont.innerHTML = `<div class="card pad vacio-stack">
      <div class="circulo">${ico('layers', 'lg')}</div>
      <b>El stack está vacío</b>
      <small>Pega enlaces o playlists (o usa el atajo de captura rápida) y se irán sumando a la derecha. Elige uno para verlo y configurarlo como siempre; después descárgalos todos juntos en una carpeta.</small>
    </div>`;
  pintarPanelStack();
}

document.addEventListener('click', async e => {
  const t = e.target;
  if (t.closest('#panel-stack')) {
    const incluir = t.closest('[data-stack-incluir]');
    if (incluir) {
      const i = S.stack.items.find(x => x.uid === incluir.dataset.stackIncluir);
      if (i) { i.incluir = !i.incluir; guardarStackLuego(); pintarPanelStack(); }
      return;
    }
    const quitar = t.closest('[data-stack-quitar]');
    if (quitar) return quitarDelStack(quitar.dataset.stackQuitar);
    const tv = t.closest('[data-stack-tv]');
    if (tv) { guardarEstadoActual(); return verUnoDelStack(tv.dataset.stackTv); }
    const ver = t.closest('[data-stack-ver]');
    if (ver) return seleccionarStack(ver.dataset.stackVer);
  }
  const accion = t.closest('[data-accion]')?.dataset.accion;
  if (accion === 'stack-abrir') {
    S.stackAbierto = true;
    if (!S.ajustes.modo_stack) return guardarAjuste({ modo_stack: true });   // vuelve al modo stack con su panel abierto
    return pintarPanelStack();
  }
  if (accion === 'stack-cerrar') { S.stackAbierto = false; return pintarPanelStack(); }
  if (accion === 'stack-descargar') return descargarStack();
  if (accion === 'stack-quitar-actual') return quitarDelStack(S.stack.sel);
  if (accion === 'stack-vaciar') {
    const n = S.stack.items.length;
    if (!n || await confirmar('Vaciar el stack', `¿Quitar los ${n} enlaces del stack?`, 'Vaciar')) {
      S.stack = { nombre: '', items: [], sel: null };
      S.analisis = null; S.error = null; S.cargando = false;
      guardarStackLuego(); renderDescargar();
    }
    return;
  }
  if (accion === 'stack-coleccion') {
    guardarEstadoActual();
    const items = [];
    for (const i of S.stack.items.filter(x => x.estado !== 'error')) {
      const d = i.datos || {};
      if (i.tipo === 'playlist') (d.entradas || i.entradas || []).forEach(en => items.push({ url: en.url, titulo: en.titulo, miniatura: en.miniatura, duracion: en.duracion }));
      else items.push({ url: i.url, titulo: d.titulo || i.titulo, miniatura: d.miniatura || i.miniatura, duracion: d.duracion ?? i.duracion, canal: d.canal || i.canal });
    }
    if (items.length) abrirColecciones({ agregar: items, nombre: S.stack.nombre });
  }
});
document.addEventListener('input', e => {
  if (e.target.id === 'stack-nombre') { S.stack.nombre = e.target.value; guardarStackLuego(); }
});

/* ================= CAPTURA RÁPIDA (la llama Python) ================= */
function recibirCaptura(urls, accion) {
  urls = (urls || []).filter(u => /^(https?:\/\/|magnet:\?)/i.test(u));
  if (!urls.length) return;
  if (accion === 'descargar') {
    API.descargar({ tipo: 'lote', urls, prefs: S.prefs }).then(r => {
      if (r.ok) { toast('Enviado a la cola. <a data-vista="cola">Ver cola</a>', 'ok'); refrescarCola(); }
      else toast(esc(r.error), 'err');
    });
    return;
  }
  if ((accion === 'stack' || S.ajustes.modo_stack) && agregarAlStack(urls)) {
    if (S.vista !== 'descargar') irA('descargar');
    return;
  }
  recibirEnlaces(urls.join(' '));
}

/* ================= COLECCIONES (panel deslizante) ================= */
const C = { lista: [], abierta: null, agregar: null, nombreSugerido: '', filtro: '' };

function aplicarBotonColecciones() {
  const flotante = S.ajustes.boton_colecciones === 'flotante';
  $('.nav-colecciones')?.classList.toggle('oculto', flotante);
  $('#fab-colecciones')?.classList.toggle('oculto', !flotante || $('#panel-colecciones').classList.contains('abierto'));
  document.body.classList.toggle('con-fab', flotante);
}

function pintarContadorColecciones() {
  const n = C.lista.length;
  $('#contador-colecciones').textContent = n;
  $('#contador-fab').textContent = n;
}

async function cargarColecciones() {
  C.lista = await API.colecciones() || [];
  pintarContadorColecciones();
}

async function abrirColecciones(opciones = {}) {
  C.agregar = opciones.agregar || null;
  C.nombreSugerido = opciones.nombre || '';
  C.abierta = opciones.id || null;
  await cargarColecciones();
  $('#panel-colecciones').classList.add('abierto');
  $('#panel-colecciones').setAttribute('aria-hidden', 'false');
  $('#velo-colecciones').classList.remove('oculto');
  aplicarBotonColecciones();
  await pintarColecciones();
}

function cerrarColecciones() {
  $('#panel-colecciones').classList.remove('abierto');
  $('#panel-colecciones').setAttribute('aria-hidden', 'true');
  $('#velo-colecciones').classList.add('oculto');
  C.agregar = null;
  aplicarBotonColecciones();
}

function collage(minis) {
  return `<span class="collage">${[0, 1, 2].map(i => minis[i]
    ? `<img src="${esc(minis[i])}" alt="" referrerpolicy="no-referrer">` : '<span></span>').join('')}</span>`;
}

async function pintarColecciones() {
  const panel = $('#panel-colecciones');
  if (C.abierta) return pintarColeccion(C.abierta);
  const filtro = C.filtro.toLowerCase();
  const lista = C.lista.filter(c => !filtro || c.nombre.toLowerCase().includes(filtro));
  panel.innerHTML = `
    <div class="pc-cabecera">
      <b>${C.agregar ? `Guardar ${C.agregar.length} ${C.agregar.length === 1 ? 'elemento' : 'elementos'} en…` : 'Colecciones'}</b>
      <button class="btn chico icono" data-accion="cerrar-colecciones" title="Cerrar">${ico('x', 'sm')}</button>
    </div>
    <div class="pc-herramientas">
      <input class="entrada" id="pc-buscar" type="search" placeholder="Buscar colección…" value="${esc(C.filtro)}">
      <button class="btn chico primario" data-accion="col-nueva">${ico('plus', 'sm')}Nueva</button>
      ${C.agregar ? '' : `<button class="btn chico" data-accion="col-importar" title="Importar .jabs o .txt">${ico('file', 'sm')}Importar</button>`}
    </div>
    <div class="pc-lista">${lista.map(c => `
      <div class="pc-item" data-col="${esc(c.id)}">
        ${collage(c.miniaturas || [])}
        <span class="txt"><b class="no-traducir">${esc(c.nombre)}</b><small>${c.cantidad} ${c.cantidad === 1 ? 'elemento' : 'elementos'}</small></span>
        ${C.agregar ? `<span class="insignia acento">${ico('plus', 'sm')}Añadir</span>` : ico('chevron-der', 'sm')}
      </div>`).join('') || '<small class="dim">No hay colecciones con ese nombre.</small>'}
    </div>
    <div class="pc-pie dim">Comparte una colección exportándola como archivo .jabs: quien lo importe tendrá los mismos enlaces.</div>`;
}

async function pintarColeccion(id) {
  const r = await API.coleccion(id);
  const panel = $('#panel-colecciones');
  if (!r.ok) { C.abierta = null; return pintarColecciones(); }
  const c = r.coleccion;
  const enlaces = c.items.filter(i => i.url).length;
  panel.innerHTML = `
    <div class="pc-cabecera">
      <button class="btn chico icono" data-accion="col-volver" title="Volver">${ico('chevron-izq', 'sm')}</button>
      <b class="no-traducir" style="flex:1">${esc(c.nombre)}</b>
      <button class="btn chico icono" data-accion="cerrar-colecciones" title="Cerrar">${ico('x', 'sm')}</button>
    </div>
    <div class="pc-herramientas">
      <button class="btn chico primario" data-accion="col-ver" ${c.items.length ? '' : 'disabled'} title="Reproducir como lista">${ico('play', 'sm')}Ver</button>
      <button class="btn chico" data-accion="col-descargar" ${enlaces ? '' : 'disabled'}>${ico('download', 'sm')}Descargar todo</button>
      <button class="btn chico" data-accion="col-exportar" ${enlaces ? '' : 'disabled'}>${ico('upload', 'sm')}Exportar</button>
      ${c.fija ? '' : `<button class="btn chico icono" data-accion="col-renombrar" title="Renombrar">${ico('pencil', 'sm')}</button>
      <button class="btn chico icono peligro" data-accion="col-borrar" title="Borrar colección">${ico('trash', 'sm')}</button>`}
    </div>
    <div class="pc-pegar">
      <input class="entrada" id="pc-enlace" type="text" spellcheck="false" autocomplete="off" placeholder="Pega un enlace, magnet o .torrent">
      <button class="btn chico icono" data-accion="col-pegar" title="Pegar desde el portapapeles y añadir">${ico('clipboard', 'sm')}</button>
      <button class="btn chico primario" data-accion="col-anadir-enlace">${ico('plus', 'sm')}Añadir</button>
    </div>
    <div class="pc-lista pc-items">${c.items.map((i, n) => `
      <div class="pc-elemento ${i.ruta && !i.existe ? 'perdido' : ''}" draggable="true" data-pos="${n}">
        <span class="asa" title="Arrastra para reordenar">${ico('grip', 'sm')}</span>
        ${i.miniatura ? `<img src="${esc(i.miniatura)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
          : `<span class="sin-img" ${i.ruta && i.existe ? `data-mini-local="${esc(i.ruta)}"` : ''}>${ico(i.ruta ? 'file' : 'link', 'sm')}</span>`}
        <span class="txt"><b class="no-traducir" title="${esc(i.titulo || i.url || i.ruta)}">${esc(i.titulo || i.url || i.ruta.split(/[\\/]/).pop())}</b>
          <small>${tipoElemento(i)}${i.duracion ? ' · ' + fmt.dur(i.duracion) : ''}</small></span>
        ${i.url || i.existe ? `<button class="btn chico icono" data-col-uno="${n}" title="Reproducir desde aquí">${ico('play', 'sm')}</button>` : ''}
        <button class="btn chico icono" data-col-quitar="${n}" title="Quitar de la colección">${ico('x', 'sm')}</button>
      </div>`).join('') || '<small class="dim">Vacía. Añade videos con «Guardar en colección» desde Descargar, el stack o la Biblioteca.</small>'}
    </div>`;
  panel.dataset.items = JSON.stringify(c.items.map(i => i.url ? { url: i.url } : { ruta: i.ruta }));
  if (typeof cargarMinisLocales === 'function') cargarMinisLocales(panel);
  completarColeccion(c);
}

// Texto pequeño de cada elemento: qué es (y de dónde)
function tipoElemento(i) {
  if (i.ruta) {
    if (!i.existe) return 'No encontrado (¿lo moviste o borraste?)';
    return /\.(mp3|m4a|opus|ogg|flac|wav|aac)$/i.test(i.ruta) ? 'Audio descargado' : 'Video descargado';
  }
  const url = i.url || '';
  const host = (() => { try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; } })();
  const pendiente = !i.intentado && !i.titulo ? ' · Obteniendo datos…' : '';
  if (/^magnet:\?/i.test(url) || /\.torrent$/i.test(url.split(/[?#]/)[0])) return 'Torrent' + pendiente;
  const directo = url.split(/[?#]/)[0].match(/\.(m3u8|mpd)$/i);
  if (directo) return `Enlace directo .${directo[1].toLowerCase()}${host ? ' · ' + esc(host) : ''}`;
  return `${i.tipo === 'playlist' ? 'Playlist' : 'Video'}${host ? ' · ' + esc(host) : ''}${pendiente}`;
}

// Los enlaces guardados sin analizar se completan en segundo plano (título, miniatura, duración)
const completando = new Set();
async function completarColeccion(c) {
  const falta = c.items.some(i => i.url && !i.intentado && !(i.titulo && (i.miniatura || /^magnet:/i.test(i.url))));
  if (!falta || completando.has(c.id)) return;
  completando.add(c.id);
  try {
    const r = await API.coleccion_completar(c.id);
    if (r.ok && C.abierta === c.id && $('#panel-colecciones').classList.contains('abierto')) {
      await pintarColeccion(c.id);
      cargarColecciones();
    }
  } finally {
    completando.delete(c.id);
  }
}

// Torrents y enlaces que se guardan sin analizar: un título provisional (el nombre del magnet)
function itemDeEnlace(url) {
  const m = url.match(/[?&]dn=([^&]+)/);
  return m && /^magnet:/i.test(url) ? { url, titulo: decodeURIComponent(m[1].replace(/\+/g, ' ')) } : { url };
}

function enlacesDe(texto) {
  return [...new Set((texto || '').split(/\s+/).map(t => t.trim()).filter(t => /^(https?:\/\/|magnet:\?)/i.test(t)))];
}

async function anadirEnlacesColeccion(texto) {
  const urls = enlacesDe(texto);
  if (!urls.length) return toast('Pega un enlace (http, magnet o .torrent).', 'err');
  const r = await API.agregar_a_coleccion(C.abierta, urls.map(itemDeEnlace));
  if (!r.ok) return toast(esc(r.error), 'err');
  toast(r.resultado ? `${r.resultado} ${r.resultado === 1 ? 'añadido' : 'añadidos'}.` : 'Ya estaba en la colección.', r.resultado ? 'ok' : '');
  C.lista = r.colecciones || C.lista;
  pintarContadorColecciones();
  await pintarColeccion(C.abierta);
}

async function trasCambio(r, mensaje) {
  if (!r?.ok) { if (r) toast(esc(r.error), 'err'); return false; }
  C.lista = r.colecciones || C.lista;
  pintarContadorColecciones();
  if (mensaje) toast(mensaje, 'ok');
  await pintarColecciones();
  return true;
}

document.addEventListener('click', async e => {
  const accionCol = e.target.closest('[data-accion]')?.dataset.accion;
  if (accionCol === 'col-anadir-enlace') { const campo = $('#pc-enlace'); await anadirEnlacesColeccion(campo.value); return; }
  if (accionCol === 'col-pegar') return anadirEnlacesColeccion(((await API.portapapeles()) || '').trim());
  if (accionCol === 'guardar-enlace-col') {
    const urls = enlacesDe($('#url').value);
    if (!urls.length) return toast('Pega primero un enlace en el campo de búsqueda.', 'err');
    return abrirColecciones({ agregar: urls.map(itemDeEnlace), nombre: '' });
  }
  // tocar un elemento (o su ▶) lo reproduce solo; el botón «Ver» de arriba reproduce la colección entera
  const uno = e.target.closest('[data-col-uno]') || (!e.target.closest('button, .asa') && e.target.closest('#panel-colecciones .pc-elemento'));
  if (uno && C.abierta && !e.target.closest('.pc-pegar')) {
    const n = uno.dataset.colUno ?? uno.dataset.pos;
    return verUnoDeColeccion(C.abierta, +n);
  }
  const quitar = e.target.closest('[data-col-quitar]');
  if (quitar) {
    const items = JSON.parse($('#panel-colecciones').dataset.items || '[]');
    return trasCambio(await API.quitar_de_coleccion(C.abierta, items[+quitar.dataset.colQuitar]));
  }
  const col = e.target.closest('[data-col]');
  if (col) {
    if (C.agregar) {
      const r = await API.agregar_a_coleccion(col.dataset.col, C.agregar);
      if (r.ok) { toast(`${r.resultado} ${r.resultado === 1 ? 'añadido' : 'añadidos'} a la colección.`, 'ok'); cerrarColecciones(); cargarColecciones(); }
      else toast(esc(r.error), 'err');
      return;
    }
    C.abierta = col.dataset.col;
    return pintarColecciones();
  }
  const accion = e.target.closest('[data-accion]')?.dataset.accion;
  switch (accion) {
    case 'abrir-colecciones': return abrirColecciones();
    case 'cerrar-colecciones': return cerrarColecciones();
    case 'col-volver': C.abierta = null; return pintarColecciones();
    case 'col-nueva': {
      const nombre = await pedirTexto('Nueva colección', C.nombreSugerido || '', 'Crear');
      if (!nombre) return;
      const r = await API.crear_coleccion(nombre, C.agregar || []);
      if (r.ok && C.agregar) { toast('Colección creada.', 'ok'); cerrarColecciones(); return cargarColecciones(); }
      if (r.ok) C.abierta = r.resultado;
      return trasCambio(r);
    }
    case 'col-importar': {
      const r = await API.importar_coleccion();
      if (!r) return;
      if (r.ok) C.abierta = r.id;
      return trasCambio(r, r.ok ? `Colección importada: ${r.cantidad} ${r.cantidad === 1 ? 'enlace' : 'enlaces'}.` : null);
    }
    case 'col-renombrar': {
      const actual = C.lista.find(c => c.id === C.abierta)?.nombre || '';
      const nombre = await pedirTexto('Renombrar colección', actual);
      if (nombre) return trasCambio(await API.renombrar_coleccion(C.abierta, nombre));
      return;
    }
    case 'col-borrar': {
      const actual = C.lista.find(c => c.id === C.abierta)?.nombre || '';
      if (!(await confirmar('Borrar colección', `¿Borrar «${actual}»? Los videos descargados no se borran.`, 'Borrar'))) return;
      const r = await API.borrar_coleccion(C.abierta);
      C.abierta = null;
      return trasCambio(r, 'Colección borrada.');
    }
    case 'col-descargar': {
      const r = await API.descargar_coleccion(C.abierta, S.prefs);
      if (r.ok) { toast(`${r.agregados} ${r.agregados === 1 ? 'descarga añadida' : 'descargas añadidas'} a la cola. <a data-vista="cola">Ver cola</a>`, 'ok'); refrescarCola(); }
      else toast(esc(r.error), 'err');
      return;
    }
    case 'col-exportar': {
      const r = await API.exportar_coleccion(C.abierta, 'jabs', false);
      if (!r) return;
      if (r.ok) toast(`Exportada: ${esc(r.ruta.split(/[\\/]/).pop())}${r.omitidos ? ` (${r.omitidos} archivos locales no se incluyen)` : ''}.`, 'ok');
      else toast(esc(r.error), 'err');
      return;
    }
    case 'guardar-en-coleccion': {
      const items = itemsParaColeccion();
      if (items.length) abrirColecciones({ agregar: items, nombre: S.analisis?.titulo || '' });
      return;
    }
  }
});
document.addEventListener('input', e => {
  if (e.target.id === 'pc-buscar') { C.filtro = e.target.value; pintarColecciones().then(() => { const b = $('#pc-buscar'); b.focus(); b.setSelectionRange(b.value.length, b.value.length); }); }
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && $('#panel-colecciones').classList.contains('abierto') && $('#modal').classList.contains('oculto')) cerrarColecciones();
});

// Reordenar arrastrando
let arrastrando = null;
document.addEventListener('dragstart', e => {
  const el = e.target.closest?.('.pc-elemento');
  if (!el) return;
  arrastrando = +el.dataset.pos;
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('application/x-jabsdlp', String(arrastrando));
  el.classList.add('arrastrando');
});
document.addEventListener('dragend', e => { e.target.closest?.('.pc-elemento')?.classList.remove('arrastrando'); });
document.addEventListener('dragover', e => { if (arrastrando !== null && e.target.closest('.pc-elemento')) e.preventDefault(); });
document.addEventListener('drop', async e => {
  const destino = e.target.closest('.pc-elemento');
  if (arrastrando === null || !destino) return;
  e.preventDefault();
  e.stopPropagation();
  const desde = arrastrando, hasta = +destino.dataset.pos;
  arrastrando = null;
  if (desde !== hasta) trasCambio(await API.reordenar_coleccion(C.abierta, desde, hasta));
}, true);

// Lo que se guarda con «Guardar en colección» desde Descargar
function itemsParaColeccion() {
  const a = S.analisis;
  if (!a) return [];
  if (a.tipo === 'video') return [{ url: a.url, titulo: a.titulo, miniatura: a.miniatura, duracion: a.duracion, canal: a.canal }];
  if (a.tipo === 'playlist') return a.entradas.filter(e => S.plSel.has(e.indice))
    .map(e => ({ url: e.url, titulo: e.titulo, miniatura: e.miniatura, duracion: e.duracion, canal: e.canal }));
  if (a.tipo === 'lote') return a.urls.filter((_, i) => S.plSel.has(i)).map(url => ({ url }));
  return [];
}

/* ================= BIBLIOTECA ================= */
const B = { carpetas: [], raiz: null, sub: '', datos: null, minis: {}, sel: new Set(), soloFavs: false, ultimo: null,
            recursivo: (() => { try { return localStorage.getItem('jabsdlp.bib.subcarpetas') === '1'; } catch { return false; } })(),
            tamano: (() => { try { return localStorage.getItem('jabsdlp.bib.tamano') || 'mediano'; } catch { return 'mediano'; } })() };
let observadorMinis = null;

async function abrirBiblioteca() {
  B.carpetas = await API.biblioteca_carpetas();
  if (!B.raiz || !B.carpetas.some(c => c.ruta === B.raiz)) { B.raiz = B.carpetas[0]?.ruta || null; B.sub = ''; }
  pintarCarpetasBib();
  await cargarBiblioteca();
}

function pintarCarpetasBib() {
  $('#bib-carpetas').innerHTML = B.carpetas.map(c => `
    <button class="chip-carpeta ${c.ruta === B.raiz ? 'activo' : ''}" data-bib-raiz="${esc(c.ruta)}" title="${esc(c.ruta)}">
      ${ico('folder', 'sm')}<span class="no-traducir">${esc(c.nombre)}</span>
      ${c.principal ? '' : `<span class="quitar" data-bib-quitar="${esc(c.ruta)}" title="Quitar de la Biblioteca">${ico('x', 'sm')}</span>`}
    </button>`).join('') + `<button class="btn chico fantasma" data-accion="bib-agregar">${ico('plus', 'sm')}Añadir carpeta</button>`;
}

async function cargarBiblioteca() {
  if (!B.raiz) { $('#bib-rejilla').innerHTML = ''; return; }
  $('#bib-rejilla').innerHTML = '<div class="esqueleto" style="height:160px;border-radius:12px"></div>';
  const r = await API.biblioteca_listar(B.raiz, B.sub, B.recursivo);
  if (!r.ok) { B.datos = null; $('#bib-rejilla').innerHTML = `<div class="aviso">${ico('alert', 'sm')}<span>${esc(r.error)}</span></div>`; return; }
  B.datos = r;
  B.sel.clear();
  pintarBiblioteca();
}

function filtrarBib() {
  const q = $('#bib-buscar').value.trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const tipo = $('#bib-tipo').value, fecha = $('#bib-fecha').value, orden = $('#bib-orden').value;
  const ahora = Date.now() / 1000;
  const limite = { hoy: 86400, semana: 7 * 86400, mes: 31 * 86400 }[fecha];
  let lista = (B.datos?.archivos || []).filter(a =>
    (!q || a.nombre.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').includes(q))
    && (tipo === 'todo' || a.tipo === tipo) && (!limite || ahora - a.fecha <= limite) && (!B.soloFavs || a.favorito));
  lista = lista.sort(orden === 'nombre' ? (x, y) => x.nombre.localeCompare(y.nombre, undefined, { numeric: true })
    : orden === 'tamano' ? (x, y) => y.tamano - x.tamano : (x, y) => y.fecha - x.fecha);
  return lista;
}

function pintarBiblioteca() {
  const d = B.datos;
  if (!d) return;
  const partes = d.sub ? d.sub.split(/[\\/]/) : [];
  $('#bib-migas').innerHTML = `<a data-bib-sub="">${esc(B.carpetas.find(c => c.ruta === B.raiz)?.nombre || 'Carpeta')}</a>`
    + partes.map((p, i) => ` <span class="dim">›</span> <a data-bib-sub="${esc(partes.slice(0, i + 1).join('/'))}">${esc(p)}</a>`).join('');
  $('#bib-favs').classList.toggle('primario', B.soloFavs);
  $('#bib-subcarpetas')?.classList.toggle('primario', B.recursivo);
  const archivos = filtrarBib();
  const filtrando = $('#bib-buscar').value.trim() || B.soloFavs || $('#bib-tipo').value !== 'todo' || $('#bib-fecha').value !== 'todo';
  const carpetas = filtrando ? [] : d.carpetas;
  if (!carpetas.length && !archivos.length) {
    $('#bib-rejilla').innerHTML = `<div class="vacio"><div class="circulo">${ico('library')}</div>
      <b>${filtrando ? 'Nada coincide con los filtros' : 'Aquí aún no hay videos ni audios'}</b>
      <small>${filtrando ? 'Prueba con otro nombre o quita los filtros.' : 'Lo que descargues aparecerá aquí.'}</small></div>`;
    pintarSeleccionBib();
    return;
  }
  $('#bib-rejilla').innerHTML = (carpetas.length ? `<div class="bib-subcarpetas">${carpetas.map(c => `
      <div class="bib-carpeta" data-bib-sub="${esc(d.sub ? d.sub.replace(/\\/g, '/') + '/' + c.nombre : c.nombre)}">${ico('folder', 'sm')}<span class="no-traducir">${esc(c.nombre)}</span></div>`).join('')}</div>` : '')
    + archivos.map(a => `
      <div class="bib-archivo ${B.sel.has(a.ruta) ? 'sel' : ''}" data-bib-ruta="${esc(a.ruta)}" title="${esc(a.nombre)}">
        <div class="bib-mini" data-mini="${esc(a.ruta)}">${B.minis[a.ruta] ? `<img src="${B.minis[a.ruta]}" alt="">` : ico(a.tipo === 'audio' ? 'music' : 'video', 'lg')}
          <span class="casilla ${B.sel.has(a.ruta) ? 'on' : ''}" data-bib-sel="${esc(a.ruta)}"></span>
          <button class="estrella ${a.favorito ? 'on' : ''}" data-bib-fav="${esc(a.ruta)}" title="${a.favorito ? 'Quitar de favoritos' : 'Añadir a favoritos'}">${ico('star', 'sm')}</button>
        </div>
        <div class="bib-info"><b class="no-traducir">${esc(a.nombre)}</b>
          <small>${a.carpeta ? `<span class="no-traducir">${ico('folder', 'sm')}${esc(a.carpeta)}</span> · ` : ''}${esc(fmt.bytes(a.tamano))} · ${esc(new Date(a.fecha * 1000).toLocaleDateString())}</small></div>
        <div class="bib-acciones">
          <button class="btn chico icono" data-bib-ver="${esc(a.ruta)}" title="Ver aquí">${ico('tv', 'sm')}</button>
          <button class="btn chico icono" data-bib-abrir="${esc(a.ruta)}" title="Abrir con otro programa">${ico('play', 'sm')}</button>
          <button class="btn chico icono" data-bib-carpeta="${esc(a.ruta)}" title="Mostrar en la carpeta">${ico('folder', 'sm')}</button>
          <button class="btn chico icono peligro" data-bib-papelera="${esc(a.ruta)}" title="Enviar a la Papelera">${ico('trash', 'sm')}</button>
        </div>
      </div>`).join('')
    + (d.recortado ? `<div class="aviso" style="grid-column:1/-1">${ico('alert', 'sm')}<span>Hay demasiados archivos: se muestran los primeros 3000.</span></div>` : '');
  pintarSeleccionBib();
  observarMinis();
}

function observarMinis() {
  observadorMinis?.disconnect();
  observadorMinis = new IntersectionObserver(entradas => {
    for (const en of entradas) {
      if (!en.isIntersecting) continue;
      const el = en.target, ruta = el.dataset.mini;
      observadorMinis.unobserve(el);
      if (B.minis[ruta] !== undefined) continue;
      B.minis[ruta] = null;
      API.biblioteca_miniatura(ruta).then(src => {
        B.minis[ruta] = src || null;
        const actual = document.querySelector(`[data-mini="${CSS.escape(ruta)}"]`);
        if (src && actual && !actual.querySelector('img')) {
          actual.querySelector('svg')?.remove();
          actual.insertAdjacentHTML('afterbegin', `<img src="${src}" alt="">`);
        }
      });
    }
  }, { root: $('.contenido'), rootMargin: '200px' });
  $$('#bib-rejilla [data-mini]').forEach(el => { if (B.minis[el.dataset.mini] === undefined) observadorMinis.observe(el); });
}

function pintarSeleccionBib() {
  const barra = $('#bib-seleccion');
  const n = B.sel.size;
  $('#bib-rejilla')?.classList.toggle('modo-sel', n > 0);
  $('#bib-rejilla')?.setAttribute('data-tamano', B.tamano);
  if ($('#bib-tamano')) $('#bib-tamano').value = B.tamano;
  barra.classList.toggle('oculto', !n);
  if (!n) return;
  const todos = filtrarBib().length;
  barra.innerHTML = `<span><b>${n}</b> ${n === 1 ? 'seleccionado' : 'seleccionados'}</span>
    ${n < todos ? `<button class="btn chico" data-accion="bib-sel-todo">${ico('check', 'sm')}Seleccionar todo (${todos})</button>` : ''}
    <button class="btn chico primario" data-accion="bib-reproducir">${ico('play', 'sm')}Reproducir</button>
    <button class="btn chico" data-accion="bib-aleatorio">${ico('aleatorio', 'sm')}Aleatorio</button>
    <button class="btn chico" data-accion="bib-playlist">${ico('playlist', 'sm')}Agrupar en playlist</button>
    <button class="btn chico" data-accion="bib-a-coleccion">${ico('bookmark', 'sm')}Añadir a colección…</button>
    <button class="btn chico" data-accion="bib-fav-sel">${ico('star', 'sm')}Favoritos</button>
    <button class="btn chico peligro" data-accion="bib-papelera-sel">${ico('trash', 'sm')}Papelera</button>
    <button class="btn chico fantasma" data-accion="bib-sel-nada">Quitar selección</button>`;
}

// Lo seleccionado se escucha o se ve como lista en Ver (en el orden de la Biblioteca, o al azar)
function reproducirSeleccion(aleatorio) {
  const orden = filtrarBib().filter(a => B.sel.has(a.ruta));
  if (!orden.length) return;
  guardarProgresoVer();
  V.lista = orden.map(a => ({ ruta: a.ruta, titulo: a.nombre.replace(/\.[^.]+$/, ''), miniatura: B.minis[a.ruta] || undefined, existe: true }));
  V.coleccion = null;
  V.nombreLista = `${orden.length} ${orden.length === 1 ? 'archivo' : 'archivos'} de la Biblioteca`;
  V.aleatorio = aleatorio;
  irA('ver');
  $('#ver-lista').classList.remove('oculto');
  abrirItemLista(aleatorio ? Math.floor(Math.random() * V.lista.length) : 0);
}

// Reproducir un archivo de la Biblioteca (con su lista: los demás del mismo tipo que se ven)
function verDesdeBiblioteca(ruta) {
  // Sigue con los demás archivos del mismo tipo que se ven: canciones con canciones, videos con videos
  const tocado = filtrarBib().find(a => a.ruta === ruta);
  const lista = filtrarBib().filter(a => a.tipo === tocado?.tipo);
  const n = lista.findIndex(a => a.ruta === ruta);
  if (n < 0 || lista.length < 2 || S.ajustes?.ver_seguir_lista === false) return verLocal(ruta);
  guardarProgresoVer();
  V.lista = lista.map(a => ({ ruta: a.ruta, titulo: a.nombre.replace(/\.[^.]+$/, ''), miniatura: B.minis[a.ruta] || undefined, existe: true }));
  V.coleccion = null;
  V.nombreLista = B.sub ? B.sub.split('/').pop() : (B.carpetas.find(c => c.ruta === B.raiz)?.nombre || 'Biblioteca');
  irA('ver');   // aleatorio o en orden: lo que tuvieras elegido en la lista de reproducción
  return abrirItemLista(n);
}

function itemsBib(rutas) {
  const porRuta = Object.fromEntries((B.datos?.archivos || []).map(a => [a.ruta, a]));
  return rutas.map(r => ({ ruta: r, titulo: porRuta[r]?.nombre.replace(/\.[^.]+$/, '') || r.split(/[\\/]/).pop() }));
}

async function papeleraBib(rutas) {
  const n = rutas.length;
  const nombre = n === 1 ? rutas[0].split(/[\\/]/).pop() : null;
  if (!(await confirmar('Enviar a la Papelera', nombre ? `¿Enviar «${nombre}» a la Papelera de reciclaje?`
    : `¿Enviar ${n} archivos a la Papelera de reciclaje?`, 'Enviar a la Papelera'))) return;
  const r = await API.biblioteca_papelera(rutas);
  if (r.movidos) toast(`${r.movidos} ${r.movidos === 1 ? 'archivo enviado' : 'archivos enviados'} a la Papelera.`, 'ok');
  if (r.fallidos) toast(`${r.fallidos} no se pudieron mover (¿están abiertos en otro programa?).`, 'err');
  cargarBiblioteca();
}

document.addEventListener('click', async e => {
  if (!e.target.closest('#vista-biblioteca')) return;
  const t = e.target;
  const sel = t.closest('[data-bib-sel]');
  if (sel) {
    e.stopPropagation();
    const ruta = sel.dataset.bibSel;
    const visibles = filtrarBib().map(a => a.ruta);
    if (e.shiftKey && B.ultimo) {
      const [i, j] = [visibles.indexOf(B.ultimo), visibles.indexOf(ruta)].sort((x, y) => x - y);
      if (i >= 0) visibles.slice(i, j + 1).forEach(r => B.sel.add(r));
    } else if (B.sel.has(ruta)) B.sel.delete(ruta); else B.sel.add(ruta);
    B.ultimo = ruta;
    return pintarBiblioteca();
  }
  if (B.ignorarClic) { B.ignorarClic = false; return; }   // fin de una selección arrastrando
  // Modo selección: con algo marcado, tocar cualquier tarjeta la marca o desmarca
  const tarjeta = t.closest('.bib-archivo');
  if (tarjeta && B.sel.size && !t.closest('button')) {
    const ruta = tarjeta.dataset.bibRuta;
    if (B.sel.has(ruta)) B.sel.delete(ruta); else B.sel.add(ruta);
    B.ultimo = ruta;
    return pintarBiblioteca();
  }
  if (tarjeta && ['pequeno', 'diminuto'].includes(B.tamano) && !t.closest('button, .casilla')) return verDesdeBiblioteca(tarjeta.dataset.bibRuta);
  const fav = t.closest('[data-bib-fav]');
  if (fav) {
    const r = await API.alternar_favorito({ ruta: fav.dataset.bibFav, titulo: fav.dataset.bibFav.split(/[\\/]/).pop() });
    if (r.ok) { const a = B.datos.archivos.find(x => x.ruta === fav.dataset.bibFav); if (a) a.favorito = r.resultado; C.lista = r.colecciones; pintarContadorColecciones(); pintarBiblioteca(); }
    return;
  }
  const abrir = t.closest('[data-bib-abrir]') || t.closest('[data-bib-carpeta]');
  if (abrir) {
    const r = await API.biblioteca_abrir(abrir.dataset.bibAbrir || abrir.dataset.bibCarpeta, !!abrir.dataset.bibCarpeta);
    if (!r.ok) toast(esc(r.error), 'err');
    return;
  }
  const verBib = t.closest('[data-bib-ver]');
  if (verBib) return verDesdeBiblioteca(verBib.dataset.bibVer);
  const pap = t.closest('[data-bib-papelera]');
  if (pap) return papeleraBib([pap.dataset.bibPapelera]);
  const quitar = t.closest('[data-bib-quitar]');
  if (quitar) {
    e.stopPropagation();
    const r = await API.biblioteca_quitar_carpeta(quitar.dataset.bibQuitar);
    B.carpetas = r.carpetas; if (B.raiz === quitar.dataset.bibQuitar) { B.raiz = B.carpetas[0]?.ruta; B.sub = ''; }
    pintarCarpetasBib(); return cargarBiblioteca();
  }
  const raiz = t.closest('[data-bib-raiz]');
  if (raiz) { B.raiz = raiz.dataset.bibRaiz; B.sub = ''; pintarCarpetasBib(); return cargarBiblioteca(); }
  const sub = t.closest('[data-bib-sub]');
  if (sub) { B.sub = sub.dataset.bibSub; return cargarBiblioteca(); }
  const accion = t.closest('[data-accion]')?.dataset.accion;
  switch (accion) {
    case 'bib-agregar': {
      const r = await API.biblioteca_agregar_carpeta();
      if (r?.ok) { B.carpetas = r.carpetas; B.raiz = r.ruta; B.sub = ''; pintarCarpetasBib(); cargarBiblioteca(); }
      return;
    }
    case 'bib-recargar': B.minis = {}; return cargarBiblioteca();
    case 'bib-favs': B.soloFavs = !B.soloFavs; return pintarBiblioteca();
    case 'bib-subcarpetas':
      B.recursivo = !B.recursivo;
      try { localStorage.setItem('jabsdlp.bib.subcarpetas', B.recursivo ? '1' : '0'); } catch { /* sin almacenamiento */ }
      return cargarBiblioteca();
    case 'bib-sel-nada': B.sel.clear(); return pintarBiblioteca();
    case 'bib-sel-todo': filtrarBib().forEach(a => B.sel.add(a.ruta)); return pintarBiblioteca();
    case 'bib-reproducir': case 'bib-aleatorio': return reproducirSeleccion(accion === 'bib-aleatorio');
    case 'bib-playlist': return abrirColecciones({ agregar: itemsBib([...B.sel]), nombre: 'Mi playlist' }).then(() => $('[data-accion="col-nueva"]')?.click());
    case 'bib-a-coleccion': return abrirColecciones({ agregar: itemsBib([...B.sel]) });
    case 'bib-fav-sel': {
      for (const it of itemsBib([...B.sel])) {
        const a = B.datos.archivos.find(x => x.ruta === it.ruta);
        if (a && !a.favorito) { const r = await API.alternar_favorito(it); if (r.ok) a.favorito = true; }
      }
      cargarColecciones(); B.sel.clear(); return pintarBiblioteca();
    }
    case 'bib-papelera-sel': return papeleraBib([...B.sel]);
  }
});
document.addEventListener('dblclick', e => {
  const a = e.target.closest('.bib-archivo');
  if (a && !B.sel.size && !e.target.closest('button, .casilla')) API.biblioteca_abrir(a.dataset.bibRuta, false);
});
['#bib-buscar', '#bib-tipo', '#bib-fecha', '#bib-orden'].forEach(sel => {
  document.addEventListener(sel === '#bib-buscar' ? 'input' : 'change', e => { if (e.target.matches(sel)) pintarBiblioteca(); });
});

/* ================= pantalla completa (F11) ================= */
document.addEventListener('keydown', e => {
  if (e.key === 'F11') { e.preventDefault(); API?.alternar_pantalla_completa(); }
});

/* ================= Ajustes: buscador y secciones plegables (1.7.2) ================= */
const PLEGADAS_CLAVE = 'jabsdlp.ajustes.plegadas';
function seccionesPlegadas() {
  try { return new Set(JSON.parse(localStorage.getItem(PLEGADAS_CLAVE) || '[]')); } catch { return new Set(); }
}
function guardarPlegadas(conjunto) {
  try { localStorage.setItem(PLEGADAS_CLAVE, JSON.stringify([...conjunto])); } catch { /* sin almacenamiento */ }
}

function prepararAjustes() {
  const rejilla = $('#vista-ajustes .rejilla-ajustes');
  if (!rejilla || $('#buscar-ajustes')) return;
  rejilla.insertAdjacentHTML('beforebegin', `<div class="buscar-ajustes">
      <span class="campo-buscar-ajustes"><input id="buscar-ajustes" class="entrada" type="search" spellcheck="false" autocomplete="off" placeholder="Buscar en los ajustes">
        <button class="btn chico icono fantasma oculto" data-accion="ajustes-limpiar-busqueda" title="Borrar la búsqueda">${ico('x', 'sm')}</button></span>
      <button class="btn chico" data-accion="ajustes-plegar" title="Plegar todas las secciones (o toca el título de cada una)">${ico('minimizar', 'sm')}Plegar todo</button>
      <button class="btn chico" data-accion="ajustes-desplegar" title="Desplegar todas las secciones">${ico('maximizar', 'sm')}Desplegar todo</button></div>`);
  crearPestanasAjustes(rejilla);
  const plegadas = seccionesPlegadas();
  [...rejilla.children].forEach((card, n) => {
    card.dataset.seccion = n;
    if (plegadas.has(String(n))) card.classList.add('plegada');
    // botón propio para plegar (grande para el dedo; antes era una flecha dibujada en el borde)
    card.querySelector(':scope > .titulo-seccion')?.insertAdjacentHTML('beforeend',
      `<button class="btn-plegar" data-accion="plegar-seccion" title="Plegar o desplegar" aria-label="Plegar o desplegar">${ico('chevron', 'sm')}</button>`);
  });
}

/* ---------- pestañas de Ajustes ----------
   Las secciones se reparten en pestañas (General, Descargas, Reproductor, Captura, Avanzado). Las opciones del
   reproductor salen de «Ventana, avisos y apariencia» a su propia sección. Con una búsqueda se ve todo. */
const PESTANAS_AJUSTES = [
  ['general', 'General', 'settings'], ['descargas', 'Descargas', 'download'], ['reproductor', 'Reproductor', 'play'],
  ['captura', 'Captura', 'zap'], ['avanzado', 'Avanzado', 'terminal'],
];
const PESTANA_CLAVE = 'jabsdlp.ajustes.pestana';
const AJUSTES_REPRODUCTOR = ['ver_gestos', 'ver_menu', 'ver_subs', 'ver_portada', 'ver_notificacion', 'ver_pip_auto', 'ver_video_fondo', 'ver_seguir_lista', 'ver_siguiente'];

function crearPestanasAjustes(rejilla) {
  const cards = [...rejilla.children];
  const titulo = c => normalizarTexto(c.querySelector(':scope > .titulo-seccion')?.textContent);
  // sección nueva «Reproductor» con las filas del reproductor
  const filas = AJUSTES_REPRODUCTOR.map(k => rejilla.querySelector(`[data-ajuste="${k}"]`)?.closest('.ajuste')).filter(Boolean);
  if (filas.length) {
    const nueva = document.createElement('div');
    nueva.className = 'card pad';
    nueva.innerHTML = `<h2 class="titulo-seccion">${ico('play')}Reproductor (Ver)</h2>`;
    filas.forEach(f => nueva.appendChild(f));
    const ventana = cards.find(c => titulo(c).includes('ventana'));
    rejilla.insertBefore(nueva, ventana ? ventana.nextSibling : null);
  }
  [...rejilla.children].forEach(c => {
    const t = titulo(c);
    c.dataset.pestana = t.startsWith('reproductor') ? 'reproductor'
      : t.startsWith('captura') ? 'captura'
      : (t.startsWith('herramientas') || t.startsWith('avanzado')) ? 'avanzado'
      : (t.startsWith('red') || t.includes('paralelo') || t.includes('aceleracion') || t.startsWith('cookies')) ? 'descargas'
      : 'general';
  });
  const android = document.documentElement.classList.contains('android');
  rejilla.insertAdjacentHTML('beforebegin', `<div class="pestanas-ajustes" role="tablist">${PESTANAS_AJUSTES
    .filter(([id]) => !(android && id === 'captura'))
    .map(([id, nombre, icono]) => `<button class="pestana-aj" role="tab" data-pestana-aj="${id}">${ico(icono, 'sm')}${nombre}</button>`).join('')}</div>`);
  let guardada = 'general';
  try { guardada = localStorage.getItem(PESTANA_CLAVE) || 'general'; } catch { /* sin almacenamiento */ }
  if (android && guardada === 'captura') guardada = 'general';
  mostrarPestanaAjustes(guardada, false);
}

function mostrarPestanaAjustes(id, recordar = true) {
  if (!PESTANAS_AJUSTES.some(([p]) => p === id)) id = 'general';
  document.documentElement.dataset.pestanaAj = id;
  $$('.pestana-aj').forEach(b => { const si = b.dataset.pestanaAj === id; b.classList.toggle('activa', si); b.setAttribute('aria-selected', si); });
  if (recordar) try { localStorage.setItem(PESTANA_CLAVE, id); } catch { /* sin almacenamiento */ }
  filtrarAjustes();
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-pestana-aj]');
  if (b) { mostrarPestanaAjustes(b.dataset.pestanaAj); b.scrollIntoView({ block: 'nearest', inline: 'center' }); }
});

function normalizarTexto(t) { return (t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }

function filtrarAjustes() {
  const q = normalizarTexto($('#buscar-ajustes')?.value.trim());
  $('[data-accion="ajustes-limpiar-busqueda"]')?.classList.toggle('oculto', !q);   // búsqueda activa: X para borrarla
  const pestana = document.documentElement.dataset.pestanaAj || 'general';
  document.documentElement.classList.toggle('buscando-ajustes', !!q);
  $$('#vista-ajustes .rejilla-ajustes > .card').forEach(card => {
    card.classList.toggle('fuera-pestana', !q && !!card.dataset.pestana && card.dataset.pestana !== pestana);
    if (!q) {
      card.classList.remove('sin-coincidencias');
      card.querySelectorAll('.no-coincide').forEach(el => el.classList.remove('no-coincide'));
      card.classList.toggle('plegada', seccionesPlegadas().has(card.dataset.seccion));
      return;
    }
    const enTitulo = normalizarTexto(card.querySelector('.titulo-seccion')?.textContent).includes(q);
    let alguno = false;
    card.querySelectorAll(':scope > .ajuste').forEach(fila => {
      const coincide = enTitulo || normalizarTexto(fila.textContent).includes(q);
      fila.classList.toggle('no-coincide', !coincide);
      alguno = alguno || coincide;
    });
    card.classList.toggle('sin-coincidencias', !alguno && !enTitulo);
    card.classList.remove('plegada');   // al buscar se ve todo lo que coincide
  });
}

document.addEventListener('input', e => { if (e.target.id === 'buscar-ajustes') filtrarAjustes(); });
document.addEventListener('click', e => {
  const titulo = e.target.closest('#vista-ajustes .rejilla-ajustes > .card > .titulo-seccion');
  if (titulo && (e.target.closest('.btn-plegar') || !e.target.closest('button, a, input, label, select'))) {
    const card = titulo.parentNode;
    card.classList.toggle('plegada');
    if ($('#buscar-ajustes')?.value.trim()) return;   // con una búsqueda funciona igual, pero no se recuerda
    const plegadas = seccionesPlegadas();
    if (card.classList.contains('plegada')) plegadas.add(card.dataset.seccion); else plegadas.delete(card.dataset.seccion);
    return guardarPlegadas(plegadas);
  }
  if (e.target.closest('[data-accion="ajustes-limpiar-busqueda"]')) {
    $('#buscar-ajustes').value = '';
    return filtrarAjustes();
  }
  const accion = e.target.closest('[data-accion]')?.dataset.accion;
  if (accion === 'ajustes-plegar' || accion === 'ajustes-desplegar') {
    const plegar = accion === 'ajustes-plegar';
    $('#buscar-ajustes').value = '';
    const todas = $$('#vista-ajustes .rejilla-ajustes > .card');
    todas.forEach(c => c.classList.toggle('plegada', plegar));
    guardarPlegadas(new Set(plegar ? todas.map(c => c.dataset.seccion) : []));
    filtrarAjustes();
  }
});
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', prepararAjustes); else prepararAjustes();

document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.target.id === 'pc-enlace') anadirEnlacesColeccion(e.target.value);
});

/* ================= Biblioteca: tamaño de los iconos y seleccionar arrastrando (1.7.4) ================= */
document.addEventListener('change', e => {
  if (e.target.id !== 'bib-tamano') return;
  B.tamano = e.target.value;
  try { localStorage.setItem('jabsdlp.bib.tamano', B.tamano); } catch { /* sin almacenamiento */ }
  $('#bib-rejilla').setAttribute('data-tamano', B.tamano);
});

// Mantener pulsado (dedo o ratón) sobre un archivo lo marca; sin soltar, al pasar por otros también se marcan
// (o se desmarcan si el primero ya estaba marcado). Cerca del borde la lista se desplaza sola.
const ARRASTRE = { timer: null, activo: false, x: 0, y: 0, marcar: true, scroll: null, ultimaY: 0, tactil: false };

function marcarTarjeta(tarjeta) {
  if (!tarjeta) return;
  const ruta = tarjeta.dataset.bibRuta;
  if (ARRASTRE.marcar) B.sel.add(ruta); else B.sel.delete(ruta);
  tarjeta.classList.toggle('sel', ARRASTRE.marcar);
  tarjeta.querySelector('.casilla')?.classList.toggle('on', ARRASTRE.marcar);
  B.ultimo = ruta;
  pintarSeleccionBib();
}

function finArrastre() {
  clearTimeout(ARRASTRE.timer);
  clearInterval(ARRASTRE.scroll);
  if (ARRASTRE.activo) {
    ARRASTRE.activo = false;
    B.ignorarClic = true;
    setTimeout(() => { B.ignorarClic = false; }, 400);
    document.body.classList.remove('arrastrando-sel');
  }
}

document.addEventListener('pointerdown', e => {
  const tarjeta = e.target.closest('#bib-rejilla .bib-archivo');
  if (!tarjeta || e.target.closest('button, .estrella') || (e.pointerType === 'mouse' && e.button !== 0)) return;
  ARRASTRE.x = e.clientX; ARRASTRE.y = e.clientY; ARRASTRE.tactil = e.pointerType !== 'mouse';
  clearTimeout(ARRASTRE.timer);
  ARRASTRE.timer = setTimeout(() => {
    ARRASTRE.activo = true;
    ARRASTRE.marcar = !B.sel.has(tarjeta.dataset.bibRuta);
    document.body.classList.add('arrastrando-sel');
    marcarTarjeta(tarjeta);
    if (navigator.vibrate) try { navigator.vibrate(12); } catch { /* sin vibración */ }
    const cont = $('.contenido');
    ARRASTRE.ultimaY = ARRASTRE.y;
    ARRASTRE.scroll = setInterval(() => {   // desplazamiento automático cerca de los bordes
      const r = cont.getBoundingClientRect();
      if (ARRASTRE.ultimaY < r.top + 70) cont.scrollTop -= 14;
      else if (ARRASTRE.ultimaY > r.bottom - 90) cont.scrollTop += 14;
    }, 30);
  }, e.pointerType === 'mouse' ? 350 : 450);
});

function moverArrastre(x, y) {
  if (!ARRASTRE.activo) {
    // si se mueve antes de tiempo es un desplazamiento normal (o un clic que se arrastra): no se selecciona
    if (Math.hypot(x - ARRASTRE.x, y - ARRASTRE.y) > 10) clearTimeout(ARRASTRE.timer);
    return false;
  }
  ARRASTRE.ultimaY = y;
  const tarjeta = document.elementFromPoint(x, y)?.closest('#bib-rejilla .bib-archivo');
  if (tarjeta && B.sel.has(tarjeta.dataset.bibRuta) !== ARRASTRE.marcar) marcarTarjeta(tarjeta);
  return true;
}

document.addEventListener('pointermove', e => { if (e.pointerType === 'mouse') moverArrastre(e.clientX, e.clientY); });
// con el dedo, durante la selección se bloquea el desplazamiento de la página (si no, el navegador se lo queda)
document.addEventListener('touchmove', e => {
  const t = e.touches[0];
  if (t && moverArrastre(t.clientX, t.clientY)) e.preventDefault();
}, { passive: false });
['pointerup', 'pointercancel', 'touchend', 'touchcancel'].forEach(ev => document.addEventListener(ev, () => {
  if (ev === 'pointercancel' && ARRASTRE.tactil && ARRASTRE.activo) return;   // el navegador cancela el puntero al mover el dedo
  finArrastre();
}));
document.addEventListener('contextmenu', e => { if (e.target.closest('#bib-rejilla .bib-archivo')) e.preventDefault(); });

/* ================= Atajos dentro de la app (1.7.4) ================= */
document.addEventListener('keydown', e => {
  if (!e.ctrlKey || e.altKey || e.metaKey || e.shiftKey) return;
  const tecla = e.key.toLowerCase();
  if (tecla === 'k') {   // Colecciones
    e.preventDefault();
    if ($('#panel-colecciones')?.classList.contains('abierto')) cerrarColecciones(); else abrirColecciones();
  } else if (tecla === 'j') {   // stack
    e.preventDefault();
    if (!S.stack.items.length) return toast('El stack está vacío (actívalo con el botón «Stack» de Descargar).');
    if (S.vista !== 'descargar') irA('descargar');
    if (!S.ajustes.modo_stack) { S.stackAbierto = true; return guardarAjuste({ modo_stack: true }); }
    S.stackAbierto = !S.stackAbierto;
    pintarPanelStack();
  }
});

// Pellizcar con dos dedos sobre la Biblioteca: juntar = iconos más pequeños, separar = más grandes (como la Galería)
const TAMANOS_BIB = ['diminuto', 'pequeno', 'mediano', 'grande'];
const NOMBRE_TAMANO = { diminuto: 'Iconos muy pequeños', pequeno: 'Iconos pequeños', mediano: 'Iconos medianos', grande: 'Iconos grandes' };
const PELLIZCO = { base: 0 };
const distanciaDedos = t => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);

function cambiarTamanoBib(paso) {
  const i = TAMANOS_BIB.indexOf(B.tamano) + paso;
  if (i < 0 || i >= TAMANOS_BIB.length) return false;
  B.tamano = TAMANOS_BIB[i];
  try { localStorage.setItem('jabsdlp.bib.tamano', B.tamano); } catch { /* sin almacenamiento */ }
  $('#bib-rejilla').setAttribute('data-tamano', B.tamano);
  if ($('#bib-tamano')) $('#bib-tamano').value = B.tamano;
  toast(NOMBRE_TAMANO[B.tamano]);
  return true;
}

document.addEventListener('touchstart', e => {
  if (e.touches.length === 2 && e.target.closest('#bib-rejilla')) {
    clearTimeout(ARRASTRE.timer);   // dos dedos: no es «mantener pulsado para seleccionar»
    PELLIZCO.base = distanciaDedos(e.touches);
  }
}, { passive: true });
document.addEventListener('touchmove', e => {
  if (e.touches.length !== 2 || !PELLIZCO.base) return;
  e.preventDefault();
  const razon = distanciaDedos(e.touches) / PELLIZCO.base;
  if (razon < 0.72 && cambiarTamanoBib(-1)) PELLIZCO.base = distanciaDedos(e.touches);
  else if (razon > 1.38 && cambiarTamanoBib(1)) PELLIZCO.base = distanciaDedos(e.touches);
}, { passive: false });
document.addEventListener('touchend', e => { if (e.touches.length < 2) PELLIZCO.base = 0; });
