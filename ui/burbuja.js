// Burbuja que sugiere enviar a JabsDLP un enlace recién copiado (Ajustes → Captura rápida → Sugerir).
const TEXTOS = {
  es: { titulo: '¿Enviar a JabsDLP?', stack: 'Al stack', descargar: 'Descargar', cerrar: 'Descartar' },
  en: { titulo: 'Send to JabsDLP?', stack: 'To stack', descargar: 'Download', cerrar: 'Dismiss' },
};

function mostrar(datos) {
  const t = TEXTOS[datos.idioma] || TEXTOS.es;
  document.documentElement.dataset.tema = datos.claro ? 'claro' : 'oscuro';
  document.getElementById('titulo').textContent = t.titulo;
  document.getElementById('dominio').textContent = datos.dominio ? `${datos.dominio} · ${datos.url}` : datos.url;
  const stack = document.getElementById('btn-stack');
  stack.textContent = t.stack;
  stack.hidden = !datos.stack;
  document.querySelector('[data-accion="descargar"]').textContent = t.descargar;
  document.querySelector('[data-accion="cerrar"]').title = t.cerrar;
  // Barra que se vacía: la burbuja se cierra sola si no haces nada
  const barra = document.getElementById('tiempo');
  barra.classList.remove('corre');
  void barra.offsetWidth;
  barra.classList.add('corre');
}

document.addEventListener('click', e => {
  const b = e.target.closest('[data-accion]');
  if (b && window.pywebview?.api) window.pywebview.api.burbuja_accion(b.dataset.accion);
});
document.addEventListener('mouseenter', () => {
  document.getElementById('tiempo').classList.remove('corre');
  window.pywebview?.api?.burbuja_mantener();
});
document.addEventListener('mouseleave', () => window.pywebview?.api?.burbuja_soltar());
