(function () {
  function closeOverlay(overlay) {
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
  }
  window.dmiShowMessage = function (options) {
    options = options || {};
    var overlay = document.createElement('div');
    overlay.className = 'dmi-message-overlay';
    overlay.innerHTML = [
      '<section class="dmi-message-card" role="dialog" aria-modal="true">',
      '<p class="dmi-message-kicker">' + escapeHtml(options.kicker || 'Mensaje del sistema') + '</p>',
      '<h2 class="dmi-message-title">' + escapeHtml(options.title || 'Aviso') + '</h2>',
      '<p class="dmi-message-text">' + escapeHtml(options.message || '') + '</p>',
      '<div class="dmi-message-actions">',
      '<button type="button" class="dmi-message-btn" data-confirm>' + escapeHtml(options.confirmText || 'Aceptar') + '</button>',
      options.cancelText ? '<button type="button" class="dmi-message-btn ghost" data-cancel>' + escapeHtml(options.cancelText) + '</button>' : '',
      '</div>',
      '</section>'
    ].join('');
    document.body.appendChild(overlay);
    overlay.querySelector('[data-confirm]').addEventListener('click', function () {
      closeOverlay(overlay);
      if (typeof options.onConfirm === 'function') options.onConfirm();
    });
    var cancel = overlay.querySelector('[data-cancel]');
    if (cancel) cancel.addEventListener('click', function () { closeOverlay(overlay); });
    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) closeOverlay(overlay);
    });
  };
  window.dmiShowServerMessage = function (successMessage, errorMessage) {
    var message = successMessage || errorMessage;
    if (!message) return;
    document.querySelectorAll('.ot-alert, .inv-alert, .alert.alert-danger, .alert.alert-success').forEach(function (element) {
      element.classList.add('dmi-message-hide-source');
    });
    window.dmiShowMessage({
      kicker: successMessage ? 'Proceso completado' : 'Atencion requerida',
      title: successMessage ? 'Operacion exitosa' : 'No se pudo completar',
      message: message,
      confirmText: 'Aceptar'
    });
  };
  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }
})();