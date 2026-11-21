/* Quick view / Full detail switch for the day plan. The choice is remembered on this device only. */
(function () {
  var sw = document.querySelector('.viewswitch');
  if (!sw) return;
  function set(view) {
    document.body.classList.toggle('quick', view === 'quick');
    sw.setAttribute('data-on', view);
    sw.querySelectorAll('button').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-view') === view ? 'true' : 'false');
    });
    try { localStorage.setItem('bdv-view', view); } catch (e) {}
  }
  var saved = 'full';
  try { saved = localStorage.getItem('bdv-view') || 'full'; } catch (e) {}
  set(saved);
  sw.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (b) set(b.getAttribute('data-view'));
    else if (e.target.classList.contains('knob')) set(document.body.classList.contains('quick') ? 'full' : 'quick');
  });
})();
