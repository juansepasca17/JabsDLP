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
          notif: 'Notificaciones', compartir: 'En Android, comparte un enlace desde YouTube o el navegador: Compartir → JabsDLP.' },
    en: { seguir: 'Keep downloading when the app is closed',
          seguirTxt: 'If you swipe JabsDLP away from recent apps, downloads continue. Off: they stop and the queue is saved to resume later.',
          notif: 'Notifications', compartir: 'On Android, share a link from YouTube or your browser: Share → JabsDLP.' }
  };

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
    var propia = document.querySelector('.ajuste-android');
    if (propia) {   // los textos siguen el idioma elegido
      propia.querySelector('b').textContent = t.seguir;
      propia.querySelector('small').textContent = t.seguirTxt;
    }
    var nc = document.getElementById('jabs-nota-compartir');
    if (nc) nc.textContent = t.compartir;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', retocar);
  else retocar();
  // Al cambiar de idioma la interfaz reescribe sus textos: se vuelven a aplicar los retoques
  window.addEventListener('load', function () { setTimeout(retocar, 600); });
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('[data-vista="ajustes"]')) setTimeout(retocar, 50);
  });
})();
