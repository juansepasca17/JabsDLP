/* JabsDLP para Android: retoques de la interfaz del PC que no se pueden hacer solo con CSS. */
(function () {
  if (window.__jabsAndroidUi) return;
  window.__jabsAndroidUi = true;
  if (document.documentElement) document.documentElement.classList.add('android');

  function idioma() {
    var l = (window.I18N && I18N.idioma) || document.documentElement.lang || navigator.language || 'es';
    return String(l).toLowerCase().indexOf('es') === 0 ? 'es' : 'en';
  }
  var T = {
    es: { seguir: 'Seguir descargando al cerrar la app',
          seguirTxt: 'Si quitas JabsDLP de las apps recientes, las descargas continúan. Apagado: se detienen y la cola se guarda para retomarla al abrir.',
          notif: 'Notificaciones', compartir: 'En Android, comparte un enlace desde YouTube o el navegador: Compartir → «Descargar con JabsDLP» o «Ver en JabsDLP».',
          log: 'Log de la app', logTxt: 'El registro de JabsDLP (Python y la interfaz) en un archivo de texto, para enviarlo si algo falla: guárdalo en Descargas (por ejemplo para mandarlo por WhatsApp) o compártelo directamente. Las URLs con tokens se ocultan.',
          logBtn: 'Compartir', logGuardar: 'Guardar en Descargas', logGuardado: 'Log guardado en ', logError: 'No se pudo exportar el log.',
          sd: 'Usar la tarjeta SD', sdOk: 'Las descargas irán a la tarjeta SD: ',
          sdFalta: 'La tarjeta SD no está disponible', sdFaltaTxt: 'La carpeta de descargas está en una tarjeta SD que no se encuentra (¿la sacaste?). Hasta que la vuelvas a poner, las descargas fallarán. ¿Quieres guardar en la memoria interna (Descargas/JabsDLP)?',
          sdInterna: 'Usar la memoria interna' },
    en: { seguir: 'Keep downloading when the app is closed',
          seguirTxt: 'If you swipe JabsDLP away from recent apps, downloads continue. Off: they stop and the queue is saved to resume later.',
          notif: 'Notifications', compartir: 'On Android, share a link from YouTube or your browser: Share → «Descargar con JabsDLP» or «Ver en JabsDLP».',
          log: 'App log', logTxt: 'The JabsDLP log (Python and the interface) as a text file, to send if something fails: save it to Downloads (e.g. to send it on WhatsApp) or share it directly. URLs with tokens are hidden.',
          logBtn: 'Share', logGuardar: 'Save to Downloads', logGuardado: 'Log saved to ', logError: 'Could not export the log.',
          sd: 'Use the SD card', sdOk: 'Downloads will go to the SD card: ',
          sdFalta: 'The SD card is not available', sdFaltaTxt: 'The download folder is on an SD card that cannot be found (did you remove it?). Until you put it back, downloads will fail. Do you want to save to internal storage (Download/JabsDLP)?',
          sdInterna: 'Use internal storage' }
  };

  function usarSd() {
    var sd = window.JabsAndroid.carpetaSd();
    if (!sd) return;
    window.pywebview.api.guardar_ajustes({ carpeta: sd }).then(function (r) {
      if (typeof S !== 'undefined') { S.ajustes = r; if (window.pintarAjustes) pintarAjustes(); }
      if (window.toast) toast(T[idioma()].sdOk + sd, 'ok');
    });
  }

  // Si la carpeta de descargas está en una SD que ya no está, se avisa y se ofrece la memoria interna
  function revisarSd(intentos) {
    if (typeof S === 'undefined' || !S.ajustes || S.ajustes.tema === undefined) { if (intentos < 60) setTimeout(function () { revisarSd(intentos + 1); }, 500); return; }
    var carpeta = S.ajustes.carpeta_efectiva || S.ajustes.carpeta || '';
    if (!carpeta || window.JabsAndroid.carpetaDisponible(carpeta)) return;
    var t = T[idioma()];
    if (!window.confirmar) return;
    confirmar(t.sdFalta, t.sdFaltaTxt, t.sdInterna).then(function (ok) {
      if (!ok) return;
      window.pywebview.api.guardar_ajustes({ carpeta: '' }).then(function (r) { S.ajustes = r; if (window.pintarAjustes) pintarAjustes(); });
    });
  }

  function retocar() {
    var t = T[idioma()];
    document.documentElement.classList.add('android');
    // El estilo inyectado al inicio va al final de <head> para que gane a estilos.css
    var css = document.getElementById('jabs-android-css');
    if (css && document.head && css.parentNode !== document.head) document.head.appendChild(css);
    else if (css && document.head && document.head.lastElementChild !== css) document.head.appendChild(css);

    // "Notificaciones de Windows" -> "Notificaciones"
    var notif = document.querySelector('.ajuste:has([data-ajuste="notificaciones"]) .txt b');
    if (notif) notif.textContent = t.notif;

    // Captura rápida: en Android los enlaces llegan con Compartir
    var stackAuto = document.querySelector('.ajuste:has([data-ajuste="stack_auto"])');
    if (stackAuto && !document.getElementById('jabs-nota-compartir')) {
      var nota = document.createElement('div');
      nota.className = 'nota';
      nota.id = 'jabs-nota-compartir';
      nota.textContent = t.compartir;
      stackAuto.parentNode.appendChild(nota);
    }

    // Ajuste propio de Android: seguir descargando al quitar la app de recientes
    var retomar = document.querySelector('.ajuste:has([data-ajuste="retomar_cola"])');
    if (retomar && !document.getElementById('jabs-seguir')) {
      var fila = document.createElement('div');
      fila.className = 'ajuste ajuste-android';
      fila.innerHTML = '<div class="txt"><b></b><small></small></div>' +
        '<label class="switch"><input type="checkbox" id="jabs-seguir"><span></span></label>';
      var caja = fila.querySelector('input');
      caja.checked = !!window.JabsAndroid.seguirAlCerrar();
      caja.addEventListener('change', function () { window.JabsAndroid.cambiarSeguirAlCerrar(caja.checked); });
      retomar.parentNode.insertBefore(fila, retomar.nextSibling);
    }
    var propia = document.getElementById('jabs-seguir');
    propia = propia && propia.closest('.ajuste');
    if (propia) {   // los textos siguen el idioma elegido
      propia.querySelector('b').textContent = t.seguir;
      propia.querySelector('small').textContent = t.seguirTxt;
    }

    // Log de la app: «Guardar en Descargas» y «Compartir» junto al interruptor «Guardar log de la app»
    var accionesLog = document.getElementById('aj-acciones-log');
    if (accionesLog && !document.getElementById('jabs-exportar-log')) {
      var guardar = document.createElement('button');
      guardar.className = 'btn chico'; guardar.id = 'jabs-guardar-log';
      guardar.addEventListener('click', function () {
        var ruta = window.JabsAndroid.guardarLog();
        if (window.toast) toast(ruta ? T[idioma()].logGuardado + ruta : T[idioma()].logError, ruta ? 'ok' : 'err');
      });
      var compartir = document.createElement('button');
      compartir.className = 'btn chico'; compartir.id = 'jabs-exportar-log';
      compartir.addEventListener('click', function () {
        if (!window.JabsAndroid.compartirLog() && window.toast) toast(T[idioma()].logError, 'err');
      });
      accionesLog.insertBefore(compartir, accionesLog.firstChild);
      accionesLog.insertBefore(guardar, accionesLog.firstChild);
    }
    var bl = document.getElementById('jabs-exportar-log');
    if (bl) {
      bl.textContent = t.logBtn;
      document.getElementById('jabs-guardar-log').textContent = t.logGuardar;
    }

    // Tarjeta SD: botón junto a «Carpeta de destino» si hay una SD puesta
    var filaCarpeta = document.querySelector('.ajuste:has(#aj-carpeta)');
    var botonSd = document.getElementById('jabs-usar-sd');
    if (filaCarpeta && !botonSd && window.JabsAndroid.carpetaSd()) {
      botonSd = document.createElement('button');
      botonSd.className = 'btn chico';
      botonSd.id = 'jabs-usar-sd';
      botonSd.addEventListener('click', usarSd);
      filaCarpeta.appendChild(botonSd);
    }
    if (botonSd) botonSd.textContent = t.sd;
    var nc = document.getElementById('jabs-nota-compartir');
    if (nc) nc.textContent = t.compartir;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', retocar);
  else retocar();
  // Al cambiar de idioma la interfaz reescribe sus textos: se vuelven a aplicar los retoques
  window.addEventListener('load', function () { setTimeout(retocar, 600); setTimeout(function () { revisarSd(0); }, 1500); });
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('[data-vista="ajustes"]')) setTimeout(retocar, 50);
  });
})();
