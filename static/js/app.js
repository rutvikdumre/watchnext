// watchNext: menu behaviour, loading overlay and live movie search.
(function () {
  'use strict';

  // ----- Close the mobile menu after picking a link or tapping outside it.
  var collapse = document.getElementById('wnMenu');
  var toggler = document.querySelector('.wn-toggler');
  if (collapse && window.jQuery) {
    var $c = window.jQuery(collapse);
    $c.on('click', 'a', function () { if ($c.hasClass('show')) $c.collapse('hide'); });
    document.addEventListener('click', function (e) {
      if ($c.hasClass('show') && !collapse.contains(e.target) && !toggler.contains(e.target)) {
        $c.collapse('hide');
      }
    });
  }

  // ----- Keep the selected genre chip visible on small screens.
  var chip = document.querySelector('.chips .chip.active');
  if (chip) chip.parentNode.scrollLeft = chip.offsetLeft - (chip.parentNode.clientWidth - chip.clientWidth) / 2;

  // ----- Loading overlay for slow pages (IMDb lookups).
  var overlay = document.getElementById('loading');
  function showLoading() { if (overlay) overlay.classList.add('show'); }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-loading]');
    if (a && !e.metaKey && !e.ctrlKey && !e.shiftKey) showLoading();
  });
  document.querySelectorAll('form[data-loading]').forEach(function (f) {
    f.addEventListener('submit', showLoading);
  });
  // Hide the overlay when coming back with the browser's back button.
  window.addEventListener('pageshow', function () { if (overlay) overlay.classList.remove('show'); });

  // ----- Live search suggestions.
  document.querySelectorAll('[data-autocomplete]').forEach(function (box) {
    var input = box.querySelector('input[type="search"]');
    var list = box.querySelector('.ac-list');
    var base = box.getAttribute('data-autocomplete'); // "/detail/" or "/suggestions/"
    var timer = null;
    var lastQuery = '';
    var active = -1;
    var controller = null;

    function esc(s) {
      return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
      });
    }
    function close() { list.hidden = true; active = -1; input.setAttribute('aria-expanded', 'false'); }
    function items() { return list.querySelectorAll('a'); }
    function highlight(i) {
      var all = items();
      all.forEach(function (a) { a.classList.remove('active'); });
      if (i >= 0 && i < all.length) { all[i].classList.add('active'); all[i].scrollIntoView({ block: 'nearest' }); }
      active = i;
    }
    function render(results, q) {
      if (q !== input.value.trim()) return;
      if (!results.length) {
        list.innerHTML = '<li class="empty">No matches yet. Press Search to look harder.</li>';
      } else {
        list.innerHTML = results.map(function (m) {
          var sub = [m.year, m.cast].filter(Boolean).join(' · ');
          return '<li><a href="' + base + esc(m.id) + '" data-loading>' +
            '<img src="' + esc(m.poster) + '" alt="" loading="lazy">' +
            '<div><div class="t">' + esc(m.title) + '</div><div class="s">' + esc(sub) + '</div></div></a></li>';
        }).join('');
      }
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      active = -1;
    }
    function fetchResults() {
      var q = input.value.trim();
      if (q.length < 2) { close(); return; }
      if (q === lastQuery && !list.hidden) return;
      lastQuery = q;
      if (controller) controller.abort();
      controller = window.AbortController ? new AbortController() : null;
      fetch('/api/suggest?q=' + encodeURIComponent(q), controller ? { signal: controller.signal } : {})
        .then(function (r) { return r.json(); })
        .then(function (data) { render(data.results || [], q); })
        .catch(function () { /* ignore aborted or failed lookups */ });
    }

    input.setAttribute('autocomplete', 'off');
    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(fetchResults, 220);
    });
    input.addEventListener('focus', function () { if (list.innerHTML && input.value.trim().length >= 2) list.hidden = false; });
    input.addEventListener('keydown', function (e) {
      var all = items();
      if (list.hidden || !all.length) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); highlight(Math.min(active + 1, all.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); highlight(Math.max(active - 1, -1)); }
      else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); showLoading(); window.location = all[active].href; }
      else if (e.key === 'Escape') { close(); }
    });
    document.addEventListener('click', function (e) { if (!box.contains(e.target)) close(); });
  });
})();
