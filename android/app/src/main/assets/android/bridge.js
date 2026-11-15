/* JabsDLP para Android: crea window.pywebview.api igual que en el PC, así ui/app.js no cambia.
   Cada llamada va a Kotlin (JabsAndroid.llamar) y de ahí a la Api de Python; la respuesta vuelve
   con window.__jabsResolver(id, json). Se inyecta al cargar la página (puede ejecutarse dos veces). */
(function () {
  if (window.pywebview && window.pywebview.__android) return;
  if (!window.JabsAndroid) return;

  var pendientes = {};
  var siguiente = 0;

  window.__jabsResolver = function (id, texto) {
    var p = pendientes[id];
    if (!p) return;
    delete pendientes[id];
    var r;
    try { r = JSON.parse(texto); } catch (e) { p.reject(e); return; }
    if (r && Object.prototype.hasOwnProperty.call(r, 'e')) p.reject(new Error(r.e));
    else p.resolve(r ? r.v : null);
  };

  function llamar(nombre, args) {
    return new Promise(function (resolve, reject) {
      var id = ++siguiente;
      pendientes[id] = { resolve: resolve, reject: reject };
      try { window.JabsAndroid.llamar(id, nombre, JSON.stringify(args)); }
      catch (e) { delete pendientes[id]; reject(e); }
    });
  }

  function lineas(texto) {
    return String(texto || '').split('\n').map(function (l) { return l.trim(); })
      .filter(function (l) { return l && l.charAt(0) !== '#'; });
  }

  var api = {};
  lineas(window.JabsAndroid.funciones()).forEach(function (nombre) {
    api[nombre] = function () { return llamar(nombre, Array.prototype.slice.call(arguments)); };
  });
  // Funciones solo de PC: responden sin llamar a Python (la interfaz esconde sus botones)
  lineas(window.JabsAndroid.soloPc()).forEach(function (linea) {
    var i = linea.indexOf('=');
    var nombre = (i < 0 ? linea : linea.slice(0, i)).trim();
    var valor = { ok: false, error: 'Solo disponible en la versión de PC.' };
    if (i >= 0 && linea.slice(i + 1).trim()) {
      try { valor = JSON.parse(linea.slice(i + 1)); } catch (e) { /* se deja el error por defecto */ }
    }
    api[nombre] = function () { return Promise.resolve(JSON.parse(JSON.stringify(valor))); };
  });
  api.plataforma = function () { return Promise.resolve('android'); };

  window.pywebview = { api: api, __android: true };
  if (document.documentElement) document.documentElement.classList.add('android');
  window.dispatchEvent(new Event('pywebviewready'));
})();
