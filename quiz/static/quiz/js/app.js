/* Progressive enhancement only: with JavaScript disabled every screen still works.
   1) a submit button that says what is happening and cannot be pressed twice;
   2) the focus moves to the summary of errors of a form that came back invalid.
   It lives in a file, and not inline in the template, so that the Content-Security-
   Policy can stay without 'unsafe-inline' (SUI-05). */
(function () {
  document.querySelectorAll("form[data-loading-text]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var button = form.querySelector("button[type=submit]");
      if (!button) { return; }
      button.disabled = true;
      button.textContent = form.getAttribute("data-loading-text") || "Guardando...";
      var status = form.querySelector("[data-loading-status]");
      if (status) { status.textContent = "Enviando el formulario, espera un momento."; }
    });
  });
  var summary = document.querySelector("[data-error-summary]");
  if (summary) { summary.focus(); }
})();