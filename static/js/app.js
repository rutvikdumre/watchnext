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
    var base = box.getAttribute('data-autocomplete'); // "/detail/", "/suggestions/" or "add"
    var addForm = box.querySelector('[data-add-form]');
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
          var href = addForm ? '#' : base + esc(m.id);
          return '<li><a href="' + href + '" data-id="' + esc(m.id) + '"' + (addForm ? '' : ' data-loading') + '>' +
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

    function choose(a) {
      if (!a) return;
      showLoading();
      if (addForm) {
        addForm.querySelector('[name="imdb_id"]').value = a.getAttribute('data-id');
        addForm.submit();
      } else {
        window.location = a.href;
      }
    }
    list.addEventListener('click', function (e) {
      var a = e.target.closest('a');
      if (a && addForm) { e.preventDefault(); choose(a); }
    });
    if (addForm) {
      box.querySelector('form[role="search"]').addEventListener('submit', function (e) {
        e.preventDefault();
        var first = list.querySelector('a');
        if (first && !list.hidden) choose(first); else fetchResults();
      });
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
      else if (e.key === 'Enter' && (active >= 0 || addForm)) { e.preventDefault(); choose(all[Math.max(active, 0)]); }
      else if (e.key === 'Escape') { close(); }
    });
    document.addEventListener('click', function (e) { if (!box.contains(e.target)) close(); });
  });
})();

// ---------------------------------------------------------------- watchlists
(function () {
  'use strict';

  // Ask before destructive actions.
  document.addEventListener('submit', function (e) {
    var msg = e.target.getAttribute && e.target.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) { e.preventDefault(); e.stopImmediatePropagation(); }
  }, true);

  // Vote / watched / remove without a full page reload.
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.hasAttribute || !form.hasAttribute('data-ajax') || e.defaultPrevented) return;
    e.preventDefault();
    var card = form.closest('.wl-item');
    if (card) card.classList.add('busy');
    fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'X-Requested-With': 'fetch' } })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        var type = r.headers.get('Content-Type') || '';
        return type.indexOf('json') >= 0 ? r.json() : r.text();
      })
      .then(function (data) {
        if (!card) { window.location.reload(); return; }
        if (typeof data === 'string') {
          var tmp = document.createElement('div');
          tmp.innerHTML = data.trim();
          card.replaceWith(tmp.firstChild);
        } else if (data.removed) {
          card.style.opacity = '0';
          setTimeout(function () { card.remove(); }, 200);
        }
        markSeen();
      })
      .catch(function () { form.submit(); });
  });

  // Pick which list the "Add to watchlist" button targets.
  document.querySelectorAll('[data-list-select]').forEach(function (select) {
    var form = select.closest('form');
    form.action = select.value;
    select.addEventListener('change', function () { form.action = select.value; });
  });

  // Share invite links (native share sheet on phones, copy elsewhere).
  document.querySelectorAll('[data-share]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var url = btn.getAttribute('data-share');
      var title = btn.getAttribute('data-share-title') || 'watchNext';
      if (navigator.share) {
        navigator.share({ title: title, text: title, url: url }).catch(function () {});
        return;
      }
      var done = function () {
        var old = btn.textContent;
        btn.textContent = 'Link copied!';
        setTimeout(function () { btn.textContent = old; }, 1800);
      };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { window.prompt('Copy this link', url); });
      else window.prompt('Copy this link', url);
    });
  });

  // Live updates: refresh when a friend changes the list.
  var itemsEl = document.getElementById('wl-items');
  var cfg = itemsEl && itemsEl.getAttribute('data-state-url') ?
    { state: itemsEl.getAttribute('data-state-url'), version: itemsEl.getAttribute('data-version') } : null;
  var seen = cfg && cfg.version;
  function markSeen() {
    if (!cfg) return;
    fetch(cfg.state).then(function (r) { return r.json(); }).then(function (d) { seen = d.version; }).catch(function () {});
  }
  if (cfg) {
    setInterval(function () {
      if (document.hidden) return;
      var typing = document.activeElement && document.activeElement.tagName === 'INPUT' && document.activeElement.value;
      fetch(cfg.state).then(function (r) { return r.json(); }).then(function (d) {
        if (d.version !== seen && !typing && !window.WN_PAUSE_REFRESH) window.location.reload();
      }).catch(function () {});
    }, 8000);
  }
})();

// ---------------------------------------------------------------- movie draw reveal
(function () {
  'use strict';
  var box = document.querySelector('[data-reveal]');
  if (!box) return;
  var data;
  try { data = JSON.parse(box.getAttribute('data-reveal')); } catch (e) { return; }
  var key = 'wn-reveal-' + data.round;
  var seen = false;
  try { seen = !!window.localStorage.getItem(key); } catch (e) { /* private mode */ }
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (seen || reduce || data.posters.length < 2) { box.classList.add('done', 'static'); return; }

  // Build a long strip of random tickets that ends on the winner.
  var reel = box.querySelector('.reel');
  var win = data.posters[data.winner];
  var strip = [];
  var stop = 34;
  for (var i = 0; i < stop; i++) strip.push(data.posters[Math.floor(Math.random() * data.posters.length)]);
  strip.push(win);
  for (var j = 0; j < 4; j++) strip.push(data.posters[Math.floor(Math.random() * data.posters.length)]);
  reel.innerHTML = strip.map(function (p, k) {
    var div = document.createElement('div');
    div.textContent = p.title;
    return '<div class="cell' + (k === stop ? ' is-winner' : '') + '"><img src="' + p.poster.replace(/"/g, '&quot;') +
      '" alt=""><span>' + div.innerHTML + '</span></div>';
  }).join('');

  window.WN_PAUSE_REFRESH = true;
  box.classList.add('spinning');
  box.scrollIntoView({ block: 'start', behavior: 'smooth' });
  var cell = reel.querySelector('.cell');
  var step = cell.getBoundingClientRect().width + 12;
  var windowWidth = box.querySelector('.reel-window').clientWidth;
  var target = -(stop * step) + (windowWidth / 2 - (step - 12) / 2);
  setTimeout(function () {
    reel.style.transition = 'transform 4.6s cubic-bezier(0.12, 0.7, 0.12, 1)';
    reel.style.transform = 'translateX(' + target + 'px)';
  }, 350);
  reel.addEventListener('transitionend', function () {
    box.classList.remove('spinning');
    box.classList.add('done');
    window.WN_PAUSE_REFRESH = false;
    try { window.localStorage.setItem(key, '1'); } catch (e) { /* ignore */ }
    setTimeout(function () { box.classList.add('collapsed'); }, 1600);
  }, { once: true });
})();
