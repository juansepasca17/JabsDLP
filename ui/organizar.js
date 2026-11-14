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
// Vista en dos columnas, como al analizar un video: a la izquierda el elemento seleccionado en grande con su
// configuración; a la derecha la lista del stack (las playlists salen agrupadas y plegables).
S.stack = { nombre: '', items: [], sel: null, plegados: new Set() };

function nombreStackPorDefecto() {
  const d = new Date(), p = n => String(n).padStart(2, '0');
  return `Stack ${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}-${p(d.getMinutes())}`;
}

function esPlaylistUrl(url) { return /[?&]list=|\/playlist|\/sets\/|\/album\//i.test(url); }

function apilable(url) {
  return /^https?:\/\//i.test(url) && !/\.(m3u8|mpd)$/i.test(url.split(/[?#]/)[0]);
}

let temporizadorStack = null;
function guardarStackLuego() {
  clearTimeout(temporizadorStack);
  temporizadorStack = setTimeout(() => API.guardar_stack({
    nombre: S.stack.nombre,
    items: S.stack.items.filter(i => i.estado === 'listo' || i.estado === 'analizando')
      .map(i => ({ ...i.datos, url: i.url, prefs: i.prefs, grupo: i.grupo })),
  }), 400);
}

function itemDeStack(url, datos = null, grupo = null) {
  return { uid: Math.random().toString(36).slice(2), url, estado: datos ? 'listo' : 'analizando',
           datos: datos || { url }, prefs: null, sel: true, grupo };
}

async function agregarAlStack(urls) {
  urls = urls.filter(apilable);
  if (!urls.length) return false;
  if (!S.stack.nombre) S.stack.nombre = nombreStackPorDefecto();
  let nuevos = 0;
  for (const url of urls) {
    if (esPlaylistUrl(url) || S.modo === 'playlist') { agregarPlaylistAlStack(url); nuevos++; continue; }
    if (S.stack.items.some(i => i.url === url)) continue;
    const item = itemDeStack(url);
    S.stack.items.push(item);
    S.stack.sel = item.uid;
    nuevos++;
    analizarItemStack(item);
  }
  if (!nuevos) { toast('Ese enlace ya está en el stack.'); return true; }
  renderDescargar();
  toast(nuevos === 1 ? 'Añadido al stack.' : `${nuevos} enlaces añadidos al stack.`, 'ok');
  return true;
}

// Una playlist se extrae y sus videos entran agrupados (con su propia cabecera en la lista)
async function agregarPlaylistAlStack(url) {
  const id = 'g' + Math.random().toString(36).slice(2, 8);
  const marcador = itemDeStack(url, null, { id, titulo: 'Playlist…' });
  marcador.esMarcador = true;
  S.stack.items.push(marcador);
  S.stack.sel = 'g:' + id;
  renderDescargar();
  let r;
  try { r = await API.analizar(url, 'playlist', S.prefs); } catch (e) { r = { ok: false, error: String(e) }; }
  const pos = S.stack.items.indexOf(marcador);
  if (pos < 0) return;
  if (!r.ok || r.datos.tipo !== 'playlist') {
    marcador.estado = 'error';
    marcador.error = r.ok ? 'No es una playlist.' : r.error;
    marcador.grupo.titulo = url;
  } else {
    const d = r.datos;
    const grupo = { id, titulo: d.titulo, miniatura: d.miniatura?.startsWith('https://') ? d.miniatura : null };
    const vistos = new Set(S.stack.items.map(i => i.url));
    const entradas = d.entradas.filter(e => !vistos.has(e.url)).map(e => itemDeStack(e.url,
      { url: e.url, titulo: e.titulo, miniatura: e.miniatura, duracion: e.duracion, canal: e.canal || d.canal }, grupo));
    S.stack.items.splice(pos, 1, ...entradas);
    if (S.ajustes.stack_auto && entradas.length) enviarItems(entradas);
  }
  guardarStackLuego();
  if (S.vista === 'descargar') renderDescargar();
}

async function analizarItemStack(item) {
  let r;
  try { r = await API.analizar(item.url, 'video', S.prefs); } catch (e) { r = { ok: false, error: String(e) }; }
  if (!S.stack.items.includes(item)) return;
  if (r.ok && r.datos.tipo === 'video') {
    const d = r.datos;
    item.datos = { url: item.url, titulo: d.titulo, miniatura: d.miniatura, duracion: d.duracion, canal: d.canal,
                   extractor: d.extractor, resolucion: d.resolucion };
    item.estado = 'listo';
    if (S.ajustes.stack_auto) await enviarItems([item]);
  } else {
    item.estado = 'error';
    item.error = r.ok ? 'No es un video suelto.' : r.error;
  }
  guardarStackLuego();
  if (S.vista === 'descargar') renderDescargar();
}

async function enviarItems(items) {
  const r = await API.descargar({ tipo: 'stack', nombre: S.stack.nombre || nombreStackPorDefecto(), prefs: S.prefs,
                                  items: items.map(i => ({ ...i.datos, prefs: i.prefs })) });
  if (!r.ok) { toast(esc(r.error), 'err'); return false; }
  items.forEach(i => { i.estado = 'enviado'; });
  refrescarCola();
  return true;
}

// ---------- grupos y selección ----------
function gruposDelStack() {
  // [{grupo|null, items}] respetando el orden de llegada
  const bloques = [];
  for (const it of S.stack.items) {
    const ultimo = bloques[bloques.length - 1];
    if (it.grupo && ultimo?.grupo?.id === it.grupo.id) ultimo.items.push(it);
    else bloques.push({ grupo: it.grupo || null, items: [it] });
  }
  return bloques;
}

function seleccionado() {
  const sel = S.stack.sel;
  if (sel?.startsWith('g:')) {
    const items = S.stack.items.filter(i => i.grupo?.id === sel.slice(2));
    if (items.length) return { grupo: items[0].grupo, items };
  }
  const item = S.stack.items.find(i => i.uid === sel) || S.stack.items[0];
  if (item?.esMarcador) return { grupo: item.grupo, items: [item] };
  return item ? { item } : null;
}

const OPCION_PREFS = [['resto', 'Como el resto'], ['video', 'Video'], ['audio', 'Solo audio']];
const RESOLUCIONES = [['', 'Máxima'], ['1080', '1080p'], ['720', '720p'], ['480', '480p']];

function prefsHTML(prefs, destino) {
  const modo = !prefs ? 'resto' : prefs.tipo === 'audio' ? 'audio' : 'video';
  return `<div class="stack-config">
      <div class="etiqueta-grupo">${ico('sliders', 'sm')}${destino === 'grupo' ? 'Configuración de toda la playlist' : 'Configuración de este video'}</div>
      <div class="segmentado">${OPCION_PREFS.map(([v, t]) =>
        `<button class="${modo === v ? 'activo' : ''}" data-stack-modo="${v}">${t}</button>`).join('')}</div>
      ${modo === 'video' ? `<div class="fila-res"><span class="dim">Resolución máxima</span><div class="segmentado">${RESOLUCIONES.map(([v, t]) =>
        `<button class="${(prefs.resolucion || '') === v ? 'activo' : ''}" data-stack-res="${v}">${t}</button>`).join('')}</div></div>` : ''}
      <small class="dim">${modo === 'resto' ? 'Usa las preferencias generales del stack (las de arriba).'
        : modo === 'audio' ? 'Se descarga solo el audio, en el formato de tus preferencias de audio.'
        : 'Video con el resto de tus preferencias y, como mucho, la resolución elegida.'}</small>
    </div>`;
}

function detalleStackHTML() {
  const s = seleccionado();
  if (!s) return '';
  if (s.grupo) {
    const g = s.grupo, items = s.items;
    const cargando = items.some(i => i.esMarcador && i.estado === 'analizando');
    const error = items.find(i => i.esMarcador && i.estado === 'error');
    const total = items.filter(i => !i.esMarcador).reduce((a, i) => a + (i.datos.duracion || 0), 0);
    const img = g.miniatura || items.find(i => i.datos.miniatura)?.datos.miniatura;
    return `<div class="miniatura">${img ? `<img src="${esc(img)}" alt="" referrerpolicy="no-referrer">` : ''}
        <div class="tipo-lista">${ico(cargando ? 'loader' : 'playlist', cargando ? 'lg spin' : 'lg')}<span>${cargando ? 'Extrayendo…' : `${items.length} videos`}</span></div></div>
      <div class="meta-titulo no-traducir">${esc(cargando ? 'Extrayendo la playlist…' : g.titulo)}</div>
      ${error ? `<div class="aviso">${ico('alert', 'sm')}<span>${esc(error.error)}</span></div>` : ''}
      ${cargando || error ? '' : `<div class="meta-fila"><span>${ico('playlist', 'sm')}${items.length} videos</span>
        ${total ? `<span>${ico('clock', 'sm')}${fmt.dur(total)} en total</span>` : ''}</div>
      ${prefsHTML(items.every(i => JSON.stringify(i.prefs) === JSON.stringify(items[0].prefs)) ? items[0].prefs : null, 'grupo')}`}
      <div class="stack-acciones-item"><button class="btn chico peligro" data-stack-quitar-grupo="${esc(g.id)}">${ico('trash', 'sm')}Quitar la playlist del stack</button></div>`;
  }
  const i = s.item, d = i.datos;
  const host = (() => { try { return new URL(i.url).hostname.replace(/^www\./, ''); } catch { return ''; } })();
  return `<div class="miniatura">${d.miniatura ? `<img src="${esc(d.miniatura)}" alt="" referrerpolicy="no-referrer">` : ''}
      ${i.estado === 'analizando' ? `<div class="tipo-lista">${ico('loader', 'lg spin')}<span>Analizando…</span></div>` : ''}
      ${d.duracion ? `<span class="duracion">${fmt.dur(d.duracion)}</span>` : ''}</div>
    <div class="meta-titulo no-traducir" title="${esc(d.titulo || i.url)}">${esc(d.titulo || i.url)}</div>
    <div class="meta-canal no-traducir">${esc(d.canal || '')}</div>
    <div class="meta-fila">
      ${d.duracion ? `<span>${ico('clock', 'sm')}${fmt.dur(d.duracion)}</span>` : ''}
      ${d.resolucion ? `<span>${ico('monitor', 'sm')}${esc(d.resolucion)}</span>` : ''}
      <span class="no-traducir">${ico('globe', 'sm')}${esc(d.extractor || host)}</span>
      ${i.grupo ? `<span class="no-traducir">${ico('playlist', 'sm')}${esc(i.grupo.titulo)}</span>` : ''}
    </div>
    ${i.estado === 'error' ? `<div class="aviso">${ico('alert', 'sm')}<span>${esc(i.error || 'No se pudo analizar.')}</span></div>` : ''}
    ${i.estado === 'enviado' ? `<div class="nota">${ico('check', 'sm')} Ya está en la cola de descargas.</div>` : ''}
    ${i.estado === 'listo' ? prefsHTML(i.prefs, 'item') : ''}
    <div class="stack-acciones-item"><button class="btn chico peligro" data-stack-quitar="${i.uid}">${ico('trash', 'sm')}Quitar del stack</button></div>`;
}

function filaStackHTML(i, n, enGrupo) {
  const estado = {
    analizando: `<span class="insignia">${ico('loader', 'sm spin')}</span>`,
    enviado: '<span class="insignia ok">En la cola</span>',
    error: `<span class="insignia err" title="${esc(i.error || '')}">Error</span>`,
  }[i.estado] || (i.prefs ? `<span class="insignia acento">${i.prefs.tipo === 'audio' ? 'Audio' : i.prefs.resolucion ? i.prefs.resolucion + 'p' : 'Video'}</span>` : '');
  return `<div class="item-pl item-stack ${i.estado} ${enGrupo ? 'en-grupo' : ''} ${S.stack.sel === i.uid ? 'activo' : ''}" data-stack-ver="${i.uid}">
      <span class="casilla ${i.sel ? 'on' : ''}" data-stack-sel="${i.uid}"></span>
      <span class="n">${n}</span>
      ${i.datos.miniatura ? `<img src="${esc(i.datos.miniatura)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : '<span class="sin-img"></span>'}
      <span class="t no-traducir" title="${esc(i.datos.titulo || i.url)}">${esc(i.datos.titulo || i.url)}</span>
      <span class="estado-item">${estado}</span>
      <span class="n">${i.datos.duracion ? fmt.dur(i.datos.duracion) : ''}</span>
      <button class="btn chico icono fantasma" data-stack-quitar="${i.uid}" title="Quitar del stack">${ico('x', 'sm')}</button>
    </div>`;
}

function listaStackHTML() {
  let n = 0;
  return gruposDelStack().map(b => {
    if (!b.grupo) return b.items.map(i => filaStackHTML(i, ++n, false)).join('');
    const g = b.grupo, plegado = S.stack.plegados.has(g.id);
    const reales = b.items.filter(i => !i.esMarcador);
    const todos = reales.length && reales.every(i => i.sel);
    const cargando = b.items.some(i => i.esMarcador && i.estado === 'analizando');
    return `<div class="grupo-stack ${S.stack.sel === 'g:' + g.id ? 'activo' : ''}" data-stack-grupo="${esc(g.id)}">
        <span class="casilla ${todos ? 'on' : ''}" data-stack-sel-grupo="${esc(g.id)}"></span>
        <button class="btn chico icono fantasma" data-stack-plegar="${esc(g.id)}" title="${plegado ? 'Desplegar' : 'Plegar'}">${ico(plegado ? 'chevron-der' : 'chevron', 'sm')}</button>
        ${ico(cargando ? 'loader' : 'playlist', cargando ? 'sm spin' : 'sm')}
        <span class="t no-traducir">${esc(cargando ? 'Extrayendo la playlist…' : g.titulo)}</span>
        <span class="cuenta">${reales.length ? `${reales.filter(i => i.sel).length}/${reales.length}` : ''}</span>
      </div>${plegado ? '' : reales.map(i => filaStackHTML(i, ++n, true)).join('')}`;
  }).join('');
}

function renderStack() {
  let cont = $('#stack-vista');
  if (!cont) {
    cont = document.createElement('div');
    cont.id = 'stack-vista';
    $('#columnas').after(cont);
  }
  $('#inicio').innerHTML = '';
  $('#columnas').classList.add('oculto');
  cont.classList.remove('oculto');
  const items = S.stack.items;
  if (!items.length) {
    cont.innerHTML = `<div class="card pad vacio-stack">
      <div class="circulo">${ico('layers', 'lg')}</div>
      <b>El stack está vacío</b>
      <small>Pega enlaces o playlists (o usa el atajo de captura rápida) y se irán sumando aquí. Después los descargas todos juntos en una carpeta, con la configuración general o una por video.</small>
    </div>`;
    return;
  }
  if (!seleccionado() || (S.stack.sel && !S.stack.sel.startsWith('g:') && !items.some(i => i.uid === S.stack.sel))) S.stack.sel = items[0].uid;
  const listos = items.filter(i => i.estado === 'listo' && i.sel && !i.esMarcador);
  const scroll = cont.querySelector('.lista-stack')?.scrollTop;
  cont.innerHTML = `
    <div class="columnas stack-columnas">
      <div class="columna-izq">
        <div class="cabecera-col">${ico('info')}<span>Seleccionado</span></div>
        <div id="stack-detalle">${detalleStackHTML()}</div>
      </div>
      <div class="columna-der">
        <div class="cabecera-col">${ico('layers')}Stack <span class="cuenta">(${items.filter(i => !i.esMarcador).length})</span>
          <label class="campo-linea">Carpeta
            <input class="entrada" id="stack-nombre" spellcheck="false" maxlength="120" value="${esc(S.stack.nombre)}"></label>
        </div>
        <div class="card panel-opciones">
          ${filaPrefsHTML()}
          <div class="lista-playlist lista-stack">${listaStackHTML()}</div>
          <div class="pie-opciones">
            <div class="acciones" style="margin-left:0;margin-right:auto">
              <button class="btn pildora" data-accion="stack-vaciar">${ico('trash', 'sm')}Vaciar</button>
              <button class="btn pildora" data-accion="stack-coleccion">${ico('bookmark', 'sm')}Guardar como colección</button>
            </div>
            <div class="acciones">
              <button class="btn pildora primario" data-accion="stack-descargar" ${listos.length ? '' : 'disabled'}>${ico('check')}Descargar ${listos.length} ${listos.length === 1 ? 'video' : 'videos'}</button>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  if (scroll) cont.querySelector('.lista-stack').scrollTop = scroll;
}

function cambiarPrefsSeleccion(modo, resolucion) {
  const s = seleccionado();
  if (!s) return;
  const objetivo = s.grupo ? s.items.filter(i => !i.esMarcador) : [s.item];
  const actual = objetivo[0]?.prefs;
  let prefs = null;
  if (modo === 'audio') prefs = { tipo: 'audio' };
  else if (modo === 'video') prefs = { tipo: 'video', resolucion: resolucion ?? (actual?.tipo === 'video' ? actual.resolucion || '' : '') };
  if (prefs?.tipo === 'video' && !prefs.resolucion) delete prefs.resolucion;
  objetivo.forEach(i => { i.prefs = prefs ? { ...prefs } : null; });
  guardarStackLuego();
  renderStack();
}

async function descargarStack() {
  const elegidos = S.stack.items.filter(i => i.estado === 'listo' && i.sel && !i.esMarcador);
  if (!elegidos.length) return;
  if (!(await enviarItems(elegidos))) return;
  toast(`${elegidos.length} ${elegidos.length === 1 ? 'descarga añadida' : 'descargas añadidas'} a la cola. <a data-vista="cola">Ver cola</a>`, 'ok');
  S.stack = { nombre: '', items: S.stack.items.filter(i => i.estado !== 'enviado'), sel: null, plegados: S.stack.plegados };
  guardarStackLuego();
  renderDescargar();
}

async function cargarStackGuardado() {
  const s = await API.cargar_stack();
  if (!s?.items?.length) return;
  S.stack = {
    nombre: s.nombre || '', sel: null, plegados: new Set(),
    items: s.items.map(d => {
      const { prefs, grupo, ...datos } = d;
      const item = itemDeStack(d.url, datos, grupo || null);
      item.prefs = prefs || null;
      return item;
    }),
  };
}

document.addEventListener('click', async e => {
  if (!e.target.closest('#stack-vista')) return;
  const t = e.target;
  const sel = t.closest('[data-stack-sel]');
  if (sel) {
    const item = S.stack.items.find(i => i.uid === sel.dataset.stackSel);
    if (item) { item.sel = !item.sel; renderStack(); }
    return;
  }
  const selGrupo = t.closest('[data-stack-sel-grupo]');
  if (selGrupo) {
    const items = S.stack.items.filter(i => i.grupo?.id === selGrupo.dataset.stackSelGrupo && !i.esMarcador);
    const marcar = !items.every(i => i.sel);
    items.forEach(i => { i.sel = marcar; });
    return renderStack();
  }
  const plegar = t.closest('[data-stack-plegar]');
  if (plegar) {
    const id = plegar.dataset.stackPlegar;
    S.stack.plegados.has(id) ? S.stack.plegados.delete(id) : S.stack.plegados.add(id);
    return renderStack();
  }
  const quitar = t.closest('[data-stack-quitar]');
  if (quitar) {
    S.stack.items = S.stack.items.filter(i => i.uid !== quitar.dataset.stackQuitar);
    guardarStackLuego(); return renderDescargar();
  }
  const quitarGrupo = t.closest('[data-stack-quitar-grupo]');
  if (quitarGrupo) {
    S.stack.items = S.stack.items.filter(i => i.grupo?.id !== quitarGrupo.dataset.stackQuitarGrupo);
    S.stack.sel = null;
    guardarStackLuego(); return renderDescargar();
  }
  const modo = t.closest('[data-stack-modo]');
  if (modo) return cambiarPrefsSeleccion(modo.dataset.stackModo);
  const res = t.closest('[data-stack-res]');
  if (res) return cambiarPrefsSeleccion('video', res.dataset.stackRes);
  const ver = t.closest('[data-stack-ver]');
  if (ver) { S.stack.sel = ver.dataset.stackVer; return renderStack(); }
  const grupo = t.closest('[data-stack-grupo]');
  if (grupo) { S.stack.sel = 'g:' + grupo.dataset.stackGrupo; return renderStack(); }
  const accion = t.closest('[data-accion]')?.dataset.accion;
  if (accion === 'stack-descargar') return descargarStack();
  if (accion === 'stack-vaciar') {
    const n = S.stack.items.filter(i => !i.esMarcador).length;
    if (!n || await confirmar('Vaciar el stack', `¿Quitar los ${n} enlaces del stack?`, 'Vaciar')) {
      S.stack = { nombre: '', items: [], sel: null, plegados: new Set() }; guardarStackLuego(); renderDescargar();
    }
    return;
  }
  if (accion === 'stack-coleccion') {
    const items = S.stack.items.filter(i => i.estado !== 'error' && !i.esMarcador).map(i => ({ ...i.datos, url: i.url }));
    if (items.length) abrirColecciones({ agregar: items, nombre: S.stack.nombre });
  }
});
document.addEventListener('input', e => {
  if (e.target.id === 'stack-nombre') { S.stack.nombre = e.target.value; guardarStackLuego(); }
});

/* ================= CAPTURA RÁPIDA (la llama Python) ================= */
function recibirCaptura(urls, accion) {
  urls = (urls || []).filter(u => /^https?:\/\//i.test(u));
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
      <button class="btn chico primario" data-accion="col-descargar" ${enlaces ? '' : 'disabled'}>${ico('download', 'sm')}Descargar todo</button>
      <button class="btn chico" data-accion="col-exportar" ${enlaces ? '' : 'disabled'}>${ico('upload', 'sm')}Exportar</button>
      ${c.fija ? '' : `<button class="btn chico icono" data-accion="col-renombrar" title="Renombrar">${ico('pencil', 'sm')}</button>
      <button class="btn chico icono peligro" data-accion="col-borrar" title="Borrar colección">${ico('trash', 'sm')}</button>`}
    </div>
    <div class="pc-lista pc-items">${c.items.map((i, n) => `
      <div class="pc-elemento ${i.ruta && !i.existe ? 'perdido' : ''}" draggable="true" data-pos="${n}">
        <span class="asa" title="Arrastra para reordenar">${ico('grip', 'sm')}</span>
        ${i.miniatura ? `<img src="${esc(i.miniatura)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
          : `<span class="sin-img">${ico(i.ruta ? 'file' : 'link', 'sm')}</span>`}
        <span class="txt"><b class="no-traducir" title="${esc(i.titulo || i.url || i.ruta)}">${esc(i.titulo || i.url || i.ruta.split(/[\\/]/).pop())}</b>
          <small>${i.ruta ? (i.existe ? 'Archivo descargado' : 'No encontrado (¿lo moviste o borraste?)') : esc(new URL(i.url).hostname.replace(/^www\./, ''))}${i.duracion ? ' · ' + fmt.dur(i.duracion) : ''}</small></span>
        <button class="btn chico icono" data-col-quitar="${n}" title="Quitar de la colección">${ico('x', 'sm')}</button>
      </div>`).join('') || '<small class="dim">Vacía. Añade videos con «Guardar en colección» desde Descargar, el stack o la Biblioteca.</small>'}
    </div>`;
  panel.dataset.items = JSON.stringify(c.items.map(i => i.url ? { url: i.url } : { ruta: i.ruta }));
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
const B = { carpetas: [], raiz: null, sub: '', datos: null, minis: {}, sel: new Set(), soloFavs: false, ultimo: null };
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
  const r = await API.biblioteca_listar(B.raiz, B.sub);
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
    + partes.map((p, i) => ` <span class="dim">›</span> <a data-bib-sub="${esc(partes.slice(0, i + 1).join('\\'))}">${esc(p)}</a>`).join('');
  $('#bib-favs').classList.toggle('primario', B.soloFavs);
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
      <div class="bib-carpeta" data-bib-sub="${esc(d.sub ? d.sub + '\\' + c.nombre : c.nombre)}">${ico('folder', 'sm')}<span class="no-traducir">${esc(c.nombre)}</span></div>`).join('')}</div>` : '')
    + archivos.map(a => `
      <div class="bib-archivo ${B.sel.has(a.ruta) ? 'sel' : ''}" data-bib-ruta="${esc(a.ruta)}" title="${esc(a.nombre)}">
        <div class="bib-mini" data-mini="${esc(a.ruta)}">${B.minis[a.ruta] ? `<img src="${B.minis[a.ruta]}" alt="">` : ico(a.tipo === 'audio' ? 'music' : 'video', 'lg')}
          <span class="casilla ${B.sel.has(a.ruta) ? 'on' : ''}" data-bib-sel="${esc(a.ruta)}"></span>
          <button class="estrella ${a.favorito ? 'on' : ''}" data-bib-fav="${esc(a.ruta)}" title="${a.favorito ? 'Quitar de favoritos' : 'Añadir a favoritos'}">${ico('star', 'sm')}</button>
        </div>
        <div class="bib-info"><b class="no-traducir">${esc(a.nombre)}</b>
          <small>${esc(fmt.bytes(a.tamano))} · ${esc(new Date(a.fecha * 1000).toLocaleDateString())}</small></div>
        <div class="bib-acciones">
          <button class="btn chico icono" data-bib-abrir="${esc(a.ruta)}" title="Abrir">${ico('play', 'sm')}</button>
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
  barra.classList.toggle('oculto', !n);
  if (!n) return;
  barra.innerHTML = `<span><b>${n}</b> ${n === 1 ? 'seleccionado' : 'seleccionados'}</span>
    <button class="btn chico primario" data-accion="bib-playlist">${ico('playlist', 'sm')}Agrupar en playlist</button>
    <button class="btn chico" data-accion="bib-a-coleccion">${ico('bookmark', 'sm')}Añadir a colección…</button>
    <button class="btn chico" data-accion="bib-fav-sel">${ico('star', 'sm')}Favoritos</button>
    <button class="btn chico peligro" data-accion="bib-papelera-sel">${ico('trash', 'sm')}Papelera</button>
    <button class="btn chico fantasma" data-accion="bib-sel-nada">Quitar selección</button>`;
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
    case 'bib-sel-nada': B.sel.clear(); return pintarBiblioteca();
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
  if (a && !e.target.closest('button, .casilla')) API.biblioteca_abrir(a.dataset.bibRuta, false);
});
['#bib-buscar', '#bib-tipo', '#bib-fecha', '#bib-orden'].forEach(sel => {
  document.addEventListener(sel === '#bib-buscar' ? 'input' : 'change', e => { if (e.target.matches(sel)) pintarBiblioteca(); });
});

/* ================= pantalla completa (F11) ================= */
document.addEventListener('keydown', e => {
  if (e.key === 'F11') { e.preventDefault(); API?.alternar_pantalla_completa(); }
});
