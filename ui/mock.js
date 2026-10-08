/* Datos de ejemplo para previsualizar la interfaz en un navegador normal: abre index.html?mock=1.
   Dentro de la app (pywebview) no se activa nunca. */
(function () {
  if (!/[?&]mock\b/.test(location.search)) return;

  const miniatura = (h1, h2, texto) => 'data:image/svg+xml;utf8,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="hsl(${h1},70%,32%)"/><stop offset="1" stop-color="hsl(${h2},75%,14%)"/></linearGradient></defs>
    <rect width="640" height="360" fill="url(#g)"/><path d="M0 290 L140 170 L230 240 L360 110 L470 210 L560 150 L640 220 L640 360 L0 360Z" fill="rgba(0,0,0,.35)"/>
    <path d="M0 320 L120 250 L260 300 L400 230 L520 290 L640 260 L640 360 L0 360Z" fill="rgba(0,0,0,.45)"/>
    <circle cx="500" cy="90" r="34" fill="rgba(255,255,255,.75)"/><text x="32" y="64" font-family="Segoe UI,Arial" font-size="38" font-weight="700" fill="#fff">${texto}</text></svg>`);

  const dormir = ms => new Promise(r => setTimeout(r, ms));
  const DUR = 1837;
  const KBPS = { 2160: 9800, 1440: 5200, 1080: 2600, 720: 1500, 480: 800, 360: 520 };
  const FACTOR = { av1: 0.82, vp9: 1, h264: 1.45 };
  const ID = { av1: { 2160: 401, 1440: 400, 1080: 399, 720: 398, 480: 397, 360: 396 }, vp9: { 2160: 313, 1440: 271, 1080: 248, 720: 247, 480: 244, 360: 243 }, h264: { 1080: 137, 720: 136, 480: 135, 360: 134 } };
  const PUNTAJE = { av1: 4, vp9: 3, h265: 2, h264: 1 };
  const NOMBRE = { av1: 'AV1', vp9: 'VP9', h264: 'H.264', h265: 'H.265' };

  let ajustes = {
    carpeta: '', carpeta_efectiva: 'C:\\Users\\usuario\\Videos\\JabsDLP', subcarpeta_playlist: true, plantilla: '%(title)s.%(ext)s',
    cookies_modo: 'ninguna', cookies_archivo: '', cookies_navegador: 'firefox', paralelo: true, max_paralelo: 0,
    fragmentos: 4, max_conversiones: 2, gpu: 'auto', decodificar_gpu: true, calidad: 26, ffmpeg_ruta: '', idiomas_subtitulos: 'es.*,en.*',
    prefs: { tipo: 'video', codec: 'auto', resolucion: 'auto', contenedor: 'auto', audio: 'auto', audio_calidad: 'alta', criterio: 'equilibrado', formato_audio: 'auto', metadatos: true, miniatura: true, subtitulos: false },
    recomendacion: true,
  };
  const herramientas = {
    ffmpeg: 'C:\\ffmpeg\\bin\\ffmpeg.exe', ffprobe: 'C:\\ffmpeg\\bin\\ffprobe.exe',
    gpu: { nvenc: false, amf: true, qsv: false }, encoder: { tipo: 'amf', nombre: 'AMD AMF', encoder: 'hevc_amf', gpu: true },
    descarga: { estado: 'inactivo', progreso: 0 }, js: ['node'],
  };

  const PISTAS = [
    { spec: '251', titulo: 'Opus · 130 kbps', idioma: 'es-US (original)', acodec: 'opus', abr: 130 },
    { spec: '140', titulo: 'AAC · 129 kbps', idioma: 'es-US (original)', acodec: 'aac', abr: 129 },
    { spec: '250', titulo: 'Opus · 70 kbps', idioma: 'es-US (original)', acodec: 'opus', abr: 70 },
    { spec: '249', titulo: 'Opus · 50 kbps', idioma: 'es-US (original)', acodec: 'opus', abr: 50 },
    { spec: '139', titulo: 'AAC · 49 kbps', idioma: 'es-US (original)', acodec: 'aac', abr: 49 },
  ].map(o => ({ ...o, tamano: o.abr * 125 * DUR, contenedor: o.acodec === 'opus' ? 'opus' : 'm4a', video: false, audio: true, ids: o.spec }));
  const CRIT = { equilibrado: 'Equilibrado', ahorro: 'Ahorro', calidad: 'Máxima calidad' };

  function elegirAudio(prefs, audioId) {
    if (prefs.audio === 'no') return null;
    if (audioId) return PISTAS.find(p => p.spec === audioId) || PISTAS[0];
    const aac = ['h264', 'h265'].includes(prefs.codec);
    const nivel = prefs.audio === 'custom' ? prefs.audio_calidad : (prefs.criterio === 'ahorro' ? 'media' : 'alta');
    const tope = { alta: 999, media: 100, baja: 64 }[nivel];
    const lista = PISTAS.filter(p => p.abr <= tope).sort((x, y) => ((y.acodec === 'aac') === aac) - ((x.acodec === 'aac') === aac) || y.abr - x.abr);
    return lista[0];
  }

  function calcular(prefs, audioId) {
    const criterio = prefs.criterio || 'equilibrado';
    if (prefs.tipo === 'audio') {
      const fa = prefs.formato_audio;
      const lista = PISTAS.map(o => {
        const fam = { m4a: 'aac', opus: 'opus', mp3: 'mp3', flac: 'flac' }[fa];
        return { ...o, contenedor: fa === 'auto' ? o.contenedor : fa, recodificar: fa === 'auto' || fam === o.acodec ? null : fa };
      });
      const elegida = criterio === 'ahorro' ? lista[2] : lista[0];
      const rec = { ...elegida, etiquetas: [CRIT[criterio], 'Idioma original'].concat(elegida.recodificar ? [] : ['Sin recodificar']), aviso: null };
      return { recomendado: rec, opciones: lista, audios: [], audio_elegido: null, encoder: herramientas.encoder };
    }
    const audio = elegirAudio(prefs, audioId);
    const opciones = [];
    for (const h of Object.keys(KBPS).map(Number).sort((a, b) => b - a)) {
      for (const c of ['av1', 'vp9', 'h264']) {
        if (!ID[c][h]) continue;
        const v = Math.round(KBPS[h] * FACTOR[c]);
        const recod = ['h264', 'h265'].includes(prefs.codec) && c !== prefs.codec ? prefs.codec : null;
        const afam = audio ? audio.acodec : null;
        opciones.push({
          spec: audio ? `${ID[c][h]}+${audio.spec}` : String(ID[c][h]),
          titulo: `${h}p · ${NOMBRE[c]}${audio ? ' + ' + (afam === 'aac' ? 'AAC' : 'Opus') : ''}`,
          altura: h, fps: 25, hdr: false, vcodec: c, acodec: afam, puntaje: PUNTAJE[c],
          tamano: (v + (audio ? audio.abr : 0)) * 125 * DUR, tbr: v + (audio ? audio.abr : 0),
          contenedor: prefs.contenedor === 'auto' ? 'mp4' : prefs.contenedor, video: true, audio: !!audio, recodificar: recod,
          ids: audio ? `${ID[c][h]} + ${audio.spec}` : String(ID[c][h]),
        });
      }
    }
    const alturas = [...new Set(opciones.map(o => o.altura))].sort((a, b) => a - b);
    const maxima = alturas[alturas.length - 1];
    const objetivo = prefs.resolucion === 'auto' ? (criterio === 'ahorro' ? Math.min(720, maxima) : maxima) : +prefs.resolucion;
    const altura = alturas.filter(a => a <= objetivo).pop() || alturas[0];
    const base = opciones.filter(o => o.altura === altura);
    let cand = base;
    let aviso = null;
    if (prefs.codec !== 'auto') {
      const exactas = base.filter(o => o.vcodec === prefs.codec);
      if (exactas.length) cand = exactas;
      else if (!['h264', 'h265'].includes(prefs.codec)) aviso = `${NOMBRE[prefs.codec]} no está disponible en ${altura}p; se usa el mejor códec disponible.`;
    }
    const orden = criterio === 'calidad' ? (a, b) => b.tbr - a.tbr : criterio === 'ahorro' ? (a, b) => a.tamano - b.tamano : (a, b) => b.puntaje - a.puntaje || a.tamano - b.tamano;
    const elegida = { ...cand.slice().sort(orden)[0] };
    elegida.etiquetas = [CRIT[criterio]];
    if (elegida.puntaje === Math.max(...base.map(o => o.puntaje))) elegida.etiquetas.push('Mejor códec');
    if (elegida.tamano <= Math.min(...base.map(o => o.tamano))) elegida.etiquetas.push('Menor tamaño');
    if (criterio === 'calidad') elegida.etiquetas.push('Mayor bitrate');
    elegida.aviso = aviso;
    return { recomendado: elegida, opciones, audios: prefs.audio === 'no' ? [] : PISTAS, audio_elegido: audio ? audio.spec : null, encoder: herramientas.encoder };
  }

  const ahora = Date.now() / 1000;
  let cola = [
    { id: 'a1', titulo: 'Atardecer en la Patagonia · Timelapse 4K', miniatura: miniatura(22, 280, 'Patagonia'), canal: 'Viajes Lumen', tipo: 'video', titulo_formato: '2160p · AV1 + Opus', estado: 'completado', fase: 'Completado', progreso: 1, total: 1288490188, encoder: null, creado: ahora - 900 },
    { id: 'a2', titulo: 'Curso de C++ desde cero · Variables y tipos de datos', miniatura: miniatura(200, 250, 'C++ 01'), canal: 'Aprende Código', tipo: 'video', titulo_formato: '1080p · VP9 + AAC', estado: 'convirtiendo', fase: 'Convirtiendo a H.265', progreso: 1, progreso_conversion: 0.62, velocidad_conversion: '4.8x', encoder: 'AMD AMF (hevc_amf)', creado: ahora - 300 },
    { id: 'a3', titulo: 'Curso de C++ desde cero · Punteros y referencias', miniatura: miniatura(205, 255, 'C++ 02'), canal: 'Aprende Código', tipo: 'video', titulo_formato: 'Auto', estado: 'descargando', fase: 'Descargando video (1/2)', progreso: 0.45, descargado: 104857600, total: 233016320, velocidad: 12582912, eta: 11, creado: ahora - 200 },
    { id: 'a4', titulo: 'Layla Unplugged · Lección de guitarra', miniatura: miniatura(35, 10, 'Guitarra'), canal: 'Lecciones Eric', tipo: 'audio', titulo_formato: 'Opus · 130 kbps', estado: 'descargando', fase: 'Descargando', progreso: 0.78, descargado: 3355443, total: 4299161, velocidad: 2097152, eta: 1, creado: ahora - 150 },
    { id: 'a5', titulo: 'Curso de C++ desde cero · Clases y objetos', miniatura: miniatura(210, 260, 'C++ 03'), canal: 'Aprende Código', tipo: 'video', titulo_formato: 'Auto', estado: 'en_cola', fase: '', progreso: 0, creado: ahora - 100 },
    { id: 'a6', titulo: 'Video privado de ejemplo', miniatura: null, canal: null, tipo: 'video', titulo_formato: 'Auto', estado: 'error', fase: 'Error', progreso: 0, error: 'YouTube pide iniciar sesión para confirmar que no eres un bot. Configura cookies en Ajustes.', creado: ahora - 60 },
  ];

  function avanzar() {
    for (const t of cola) {
      if (t.estado === 'descargando') {
        t.progreso = Math.min(1, t.progreso + 0.02);
        t.descargado = Math.round((t.total || 0) * t.progreso);
        t.eta = Math.max(0, Math.round((1 - t.progreso) * 40));
        if (t.progreso >= 1) { t.estado = 'convirtiendo'; t.fase = 'Convirtiendo a H.265'; t.progreso_conversion = 0; t.encoder = 'AMD AMF (hevc_amf)'; t.velocidad_conversion = '5.1x'; }
      } else if (t.estado === 'convirtiendo') {
        t.progreso_conversion = Math.min(1, (t.progreso_conversion || 0) + 0.03);
        if (t.progreso_conversion >= 1) { t.estado = 'completado'; t.fase = 'Completado'; }
      } else if (t.estado === 'en_cola' && cola.filter(x => ['descargando', 'convirtiendo'].includes(x.estado)).length < (ajustes.paralelo ? 99 : 1)) {
        t.estado = 'descargando'; t.fase = 'Descargando'; t.total = 180000000; t.velocidad = 9000000;
      }
    }
  }

  const resumen = () => ({
    activos: cola.filter(t => ['iniciando', 'descargando', 'procesando', 'convirtiendo', 'esperando_gpu'].includes(t.estado)).length,
    en_cola: cola.filter(t => t.estado === 'en_cola').length,
    completados: cola.filter(t => t.estado === 'completado').length,
    errores: cola.filter(t => t.estado === 'error').length,
    total: cola.length,
  });

  const analisisVideo = () => ({
    tipo: 'video', id: 'v1', url: 'https://www.youtube.com/watch?v=demo', titulo: 'Paisajes de Islandia en 4K · Vuelo con dron sobre glaciares y volcanes',
    canal: 'Viajes Lumen', duracion: DUR, vistas: 411800, likes: 7600, fecha: '20260904', miniatura: miniatura(190, 260, 'Islandia 4K'),
    extractor: 'Youtube', resolucion: '3840x2160', fps: 25, tbr: 2100,
  });
  const analisisPlaylist = () => ({
    tipo: 'playlist', id: 'p1', url: 'https://www.youtube.com/playlist?list=demo', titulo: 'Curso de C++ desde cero', canal: 'Aprende Código', cantidad: 8,
    miniatura: miniatura(205, 255, 'Curso C++'), extractor: 'YoutubeTab', duracion: 8 * 1420,
    entradas: ['Introducción e instalación', 'Variables y tipos de datos', 'Condicionales', 'Bucles for y while', 'Funciones', 'Punteros y referencias', 'Clases y objetos', 'Proyecto final']
      .map((t, i) => ({ indice: i + 1, url: `https://www.youtube.com/watch?v=c${i}`, titulo: `C++ ${String(i + 1).padStart(2, '0')} · ${t}`, duracion: 900 + i * 137, miniatura: miniatura(200 + i * 6, 250, `C++ ${i + 1}`) })),
  });

  window.__MOCK_API__ = {
    async iniciar() { return { ok: true, app: 'JabsDLP', version: '1.0.0', ytdlp: '2026.08.19', ajustes, herramientas }; },
    async herramientas() { return herramientas; },
    async detectar_gpu() { return herramientas; },
    async descargar_ffmpeg() { return herramientas.descarga; },
    async analizar(texto, modo, prefs) {
      await dormir(900);
      const urls = texto.match(/https?:\/\/\S+/g) || [];
      if (urls.length > 1) return { ok: true, datos: { tipo: 'lote', urls, cantidad: urls.length } };
      if (!urls.length) return { ok: false, error: 'Pega una URL válida (debe empezar por http).' };
      if (modo === 'playlist') return { ok: true, datos: analisisPlaylist() };
      return { ok: true, datos: { ...analisisVideo(), ...calcular(prefs) } };
    },
    async opciones(id, prefs, audioId) { return calcular(prefs, audioId); },
    async descargar(sol) {
      const n = sol.tipo === 'playlist' ? sol.indices.length : sol.tipo === 'lote' ? sol.urls.length : 1;
      for (let i = 0; i < n; i++) {
        cola.push({ id: 'n' + Math.random(), titulo: sol.tipo === 'video' ? analisisVideo().titulo : analisisPlaylist().entradas[i % 8].titulo,
          miniatura: miniatura(190 + i * 7, 260, 'Nuevo'), canal: 'Viajes Lumen', tipo: sol.prefs.tipo, titulo_formato: 'Auto', estado: 'en_cola', progreso: 0, creado: Date.now() / 1000 });
      }
      return { ok: true, agregados: n };
    },
    async cola() { avanzar(); return { trabajos: cola, resumen: resumen(), paralelo: ajustes.paralelo, max_paralelo: ajustes.max_paralelo }; },
    async cancelar(id) { const t = cola.find(x => x.id === id); if (t) { t.estado = 'cancelado'; t.fase = 'Cancelado'; } return true; },
    async cancelar_todo() { cola.forEach(t => { if (!['completado', 'error'].includes(t.estado)) t.estado = 'cancelado'; }); return true; },
    async reintentar(id) { const t = cola.find(x => x.id === id); if (t) { t.estado = 'en_cola'; t.error = null; t.progreso = 0; } return true; },
    async quitar(id) { cola = cola.filter(x => x.id !== id); return true; },
    async limpiar() { cola = cola.filter(t => !['completado', 'error', 'cancelado'].includes(t.estado)); return true; },
    async abrir_archivo() { return true; },
    async abrir_carpeta() { return true; },
    async ajustes() { return ajustes; },
    async guardar_ajustes(c) { ajustes = { ...ajustes, ...c, prefs: { ...ajustes.prefs, ...(c.prefs || {}) } }; return ajustes; },
    async elegir_carpeta() { return null; },
    async elegir_cookies() { return null; },
    async elegir_ffmpeg() { return null; },
    async importar_txt() { return { ok: true, urls: ['https://www.youtube.com/watch?v=a1', 'https://www.youtube.com/watch?v=a2', 'https://vimeo.com/123456'] }; },
    async portapapeles() { return 'https://www.youtube.com/watch?v=demo'; },
  };
})();

/* Demostraciones automáticas para capturas: index.html?mock=1&demo=video|menu|manual|audio|playlist|cola */
(function () {
  const demo = (location.search.match(/[?&]demo=(\w+)/) || [])[1];
  if (!demo || !window.__MOCK_API__) return;
  const esperar = ms => new Promise(r => setTimeout(r, ms));
  const clic = sel => document.querySelector(sel)?.click();
  window.addEventListener('load', async () => {
    await esperar(300);
    if (demo === 'cola') { clic('[data-vista="cola"]'); return; }
    if (demo === 'ajustes') { clic('[data-vista="ajustes"]'); return; }
    document.querySelector('#url').value = demo === 'playlist' ? 'https://www.youtube.com/playlist?list=demo' : 'https://www.youtube.com/watch?v=demo';
    document.querySelector('#url').dispatchEvent(new Event('input'));
    clic('[data-accion="analizar"]');
    await esperar(1200);
    if (demo === 'menu') clic('[data-abrir="criterio"]');
    if (demo === 'extras') clic('[data-abrir="extras"]');
    if (demo === 'manual') clic('[data-accion="modo-manual"]');
    if (demo === 'audio') {
      clic('[data-abrir="audio"]'); await esperar(150);
      clic('.menu-item[data-menu-valor="custom"]'); await esperar(300);
      clic('[data-abrir="codec"]'); await esperar(150);
      clic('.menu-item[data-menu-valor="h265"]');
    }
  });
})();
