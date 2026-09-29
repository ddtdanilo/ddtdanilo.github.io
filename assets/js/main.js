/* ============================================
   DANILO DÍAZ TARASCÓ — Portfolio JS
   i18n (EN/ES), navigation, reveals, command palette,
   EU privacy notice. No dependencies, no cookies, no network calls.
   Exposes window.DDT for assets/js/agent.js (WebMCP tools).
   ============================================ */

(function () {
    'use strict';

    var LANG_KEY = 'ddt-lang';
    var PRIVACY_KEY = 'ddt-privacy-ack';
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var currentLang = 'en';
    var closeMobileMenu = function () {};

    // localStorage can throw (private mode, blocked site data).
    function store(key, value) {
        try {
            if (value === undefined) return localStorage.getItem(key);
            localStorage.setItem(key, value);
        } catch (e) { return null; }
        return value;
    }

    function t(en, es) { return currentLang === 'es' ? es : en; }

    // ---- i18n ----
    function detectLanguage() {
        var saved = store(LANG_KEY);
        if (saved === 'en' || saved === 'es') return saved;
        var nav = (navigator.language || 'en').toLowerCase();
        return nav.indexOf('es') === 0 ? 'es' : 'en';
    }

    function setLanguage(lang) {
        if (lang !== 'en' && lang !== 'es') return false;
        currentLang = lang;
        store(LANG_KEY, lang);
        document.documentElement.lang = lang;
        document.querySelectorAll('[data-' + lang + ']').forEach(function (el) {
            var text = el.getAttribute('data-' + lang);
            if (text !== null) el.innerHTML = text;
        });
        document.querySelectorAll('[data-aria-' + lang + ']').forEach(function (el) {
            el.setAttribute('aria-label', el.getAttribute('data-aria-' + lang));
        });
        document.querySelectorAll('.lang-option').forEach(function (opt) {
            opt.classList.toggle('active', opt.getAttribute('data-lang') === lang);
        });
        document.dispatchEvent(new CustomEvent('ddt:lang', { detail: lang }));
        return true;
    }

    function initLanguage() {
        setLanguage(detectLanguage());
        var toggle = document.getElementById('lang-toggle');
        if (toggle) toggle.addEventListener('click', function () {
            setLanguage(currentLang === 'en' ? 'es' : 'en');
        });
    }

    // ---- Navigation ----
    function go(hash) {
        var target = hash && document.querySelector(hash);
        if (!target) return false;
        target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
        history.replaceState(null, '', hash);
        // Move keyboard focus too, so skip links and in-page nav work for AT users.
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
        return true;
    }

    function initNavbar() {
        var nav = document.getElementById('navbar');
        if (!nav) return;
        var onScroll = function () { nav.classList.toggle('scrolled', window.scrollY > 24); };
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });

        // Highlight the section in view
        var links = document.querySelectorAll('.nav-link[href^="#"]');
        if (!links.length || !('IntersectionObserver' in window)) return;
        var map = {};
        links.forEach(function (l) { map[l.getAttribute('href').slice(1)] = l; });
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (!e.isIntersecting) return;
                links.forEach(function (l) { l.removeAttribute('aria-current'); });
                var link = map[e.target.id];
                if (link) link.setAttribute('aria-current', 'true');
            });
        }, { rootMargin: '-45% 0px -50% 0px' });
        document.querySelectorAll('main > section[id]').forEach(function (s) { io.observe(s); });
    }

    function initMobileMenu() {
        var toggle = document.querySelector('.nav-toggle');
        var menu = document.getElementById('mobile-menu');
        if (!toggle || !menu) return;

        // Everything outside the header and the menu becomes inert while open,
        // so keyboard focus can't wander into the obscured page.
        var behind = document.querySelectorAll('body > main, body > footer, .skip-link');
        function setOpen(open) {
            toggle.setAttribute('aria-expanded', String(open));
            menu.hidden = !open;
            document.body.style.overflow = open ? 'hidden' : '';
            behind.forEach(function (el) { el.inert = open; });
            document.querySelectorAll('#navbar a, #navbar .chip-btn').forEach(function (el) { el.inert = open; });
            if (open) {
                var first = menu.querySelector('a');
                if (first) first.focus();
            }
        }
        closeMobileMenu = function () { if (!menu.hidden) setOpen(false); };
        toggle.addEventListener('click', function () {
            setOpen(toggle.getAttribute('aria-expanded') !== 'true');
        });
        menu.addEventListener('click', function (e) {
            if (e.target.closest('a')) setOpen(false);
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !menu.hidden) { setOpen(false); toggle.focus(); }
        });
    }

    // ---- Reveal on scroll + counters ----
    function initReveals() {
        var items = document.querySelectorAll('.reveal');
        if (reduceMotion || !('IntersectionObserver' in window)) {
            items.forEach(function (el) { el.classList.add('in'); });
            return;
        }
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
            });
        }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
        items.forEach(function (el) { io.observe(el); });
    }

    function initCounters() {
        var nums = document.querySelectorAll('[data-count]');
        if (reduceMotion || !('IntersectionObserver' in window)) return;
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (!e.isIntersecting) return;
                io.unobserve(e.target);
                var el = e.target;
                var end = parseFloat(el.getAttribute('data-count'));
                var dec = parseInt(el.getAttribute('data-decimals') || '0', 10);
                var start = performance.now();
                var dur = 1400;
                (function tick(now) {
                    var p = Math.min(1, (now - start) / dur);
                    var eased = 1 - Math.pow(1 - p, 3);
                    el.textContent = (end * eased).toFixed(dec);
                    if (p < 1) requestAnimationFrame(tick);
                })(start);
            });
        }, { threshold: 0.6 });
        nums.forEach(function (n) { io.observe(n); });
    }

    // ---- Hero board readouts ----
    function initBoard() {
        var clock = document.getElementById('clock');
        var packets = document.getElementById('packets');
        var board = document.querySelector('.board svg');
        if (board) {
            // Set trace lengths so the draw-in animation is exact.
            board.querySelectorAll('.trace').forEach(function (p) {
                if (p.getTotalLength) p.style.setProperty('--len', Math.ceil(p.getTotalLength()));
            });
            if (reduceMotion && board.pauseAnimations) board.pauseAnimations();
        }
        if (clock) {
            var fmt;
            try {
                fmt = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'America/Bogota' });
            } catch (e) { fmt = null; }
            var paint = function () { if (fmt) clock.textContent = fmt.format(new Date()) + ' COT'; };
            paint();
            setInterval(paint, 1000);
        }
        if (packets) {
            // Illustrative counter, labelled as such via aria; not real telemetry.
            packets.setAttribute('title', 'Illustrative animation, not live data');
            var n = 18240 + Math.floor((Date.now() / 1000) % 5000);
            var paintN = function () { packets.textContent = n.toLocaleString('en-US'); };
            paintN();
            if (!reduceMotion) setInterval(function () { n += 1 + Math.floor(Math.random() * 3); paintN(); }, 900);
        }
    }

    // ---- Card spotlight (pointer-follow gradient) ----
    function initSpotlight() {
        if (reduceMotion || !window.matchMedia('(hover: hover)').matches) return;
        document.addEventListener('pointermove', function (e) {
            var card = e.target.closest && e.target.closest('.card');
            if (!card) return;
            var r = card.getBoundingClientRect();
            card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
            card.style.setProperty('--my', (e.clientY - r.top) + 'px');
        }, { passive: true });
    }

    // ---- Toast ----
    var toastTimer;
    function toast(msg) {
        var el = document.querySelector('.toast');
        if (!el) {
            el = document.createElement('div');
            el.className = 'toast';
            el.setAttribute('role', 'status');
            document.body.appendChild(el);
        }
        el.textContent = msg;
        el.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () { el.classList.remove('show'); }, 2200);
    }

    function copy(text) {
        var done = function () { toast(t('Copied: ', 'Copiado: ') + text); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(done, function () { toast(text); });
        } else { toast(text); }
    }

    // ---- Command palette ----
    var ORIGIN = 'https://ddtdanilo.github.io';
    function onHome() { return !!document.getElementById('hero'); }
    function section(hash) {
        return function () { if (onHome()) go(hash); else location.href = '/' + hash; };
    }
    var actions = [
        { id: 'work', en: 'Go to selected work', es: 'Ir a trabajo seleccionado', group: 'nav', run: section('#work') },
        { id: 'experience', en: 'Go to experience', es: 'Ir a experiencia', group: 'nav', run: section('#experience') },
        { id: 'expertise', en: 'Go to expertise', es: 'Ir a especialidades', group: 'nav', run: section('#expertise') },
        { id: 'lab', en: 'Go to lab archive', es: 'Ir al archivo del lab', group: 'nav', run: section('#lab') },
        { id: 'agents', en: 'Go to the agent tools', es: 'Ir a herramientas para agentes', group: 'nav', run: section('#agents') },
        { id: 'contact', en: 'Go to contact', es: 'Ir a contacto', group: 'nav', run: section('#contact') },
        { id: 'consult', en: 'Book a consulting session', es: 'Agendar una sesión de consultoría', group: 'page', run: function () { location.href = '/consult.html'; } },
        { id: 'lang', en: 'Cambiar a español', es: 'Switch to English', group: 'lang', run: function () { setLanguage(currentLang === 'en' ? 'es' : 'en'); } },
        { id: 'md', en: 'Open this site as Markdown', es: 'Abrir este sitio en Markdown', group: 'agents', run: function () { location.href = '/index.md'; } },
        { id: 'llms', en: 'Copy llms.txt URL', es: 'Copiar URL de llms.txt', group: 'agents', run: function () { copy(ORIGIN + '/llms.txt'); } },
        { id: 'json', en: 'Open JSON Resume', es: 'Abrir JSON Resume', group: 'agents', run: function () { location.href = '/api/resume.json'; } },
        { id: 'linkedin', en: 'Open LinkedIn', es: 'Abrir LinkedIn', group: 'link', run: function () { window.open('https://linkedin.com/in/ddtdanilo', '_blank', 'noopener'); } },
        { id: 'github', en: 'Open GitHub', es: 'Abrir GitHub', group: 'link', run: function () { window.open('https://github.com/ddtdanilo', '_blank', 'noopener'); } },
        { id: 'privacy', en: 'Privacy notice', es: 'Aviso de privacidad', group: 'page', run: function () { location.href = '/privacy.html'; } }
    ];

    function initPalette() {
        if (typeof HTMLDialogElement !== 'function') return;
        var dlg = document.createElement('dialog');
        dlg.className = 'palette';
        dlg.setAttribute('aria-label', 'Command palette');
        dlg.innerHTML =
            '<input class="palette-input" type="text" role="combobox" aria-expanded="true" aria-controls="palette-list" aria-autocomplete="list" autocomplete="off" spellcheck="false">' +
            '<ul class="palette-list" id="palette-list" role="listbox"></ul>' +
            '<div class="palette-foot" aria-hidden="true"><span>↑↓ navigate</span><span>↵ run</span><span>esc close</span></div>';
        document.body.appendChild(dlg);
        var input = dlg.querySelector('input');
        var list = dlg.querySelector('ul');
        var shown = [];
        var sel = 0;
        var opener = null;

        function render() {
            var q = input.value.trim().toLowerCase();
            shown = actions.filter(function (a) {
                return !q || (a.en + ' ' + a.es + ' ' + a.id).toLowerCase().indexOf(q) !== -1;
            });
            sel = Math.min(sel, Math.max(0, shown.length - 1));
            if (!shown.length) {
                list.innerHTML = '<li class="palette-empty" role="option" aria-disabled="true">' + t('No matches', 'Sin resultados') + '</li>';
                input.removeAttribute('aria-activedescendant');
                return;
            }
            list.innerHTML = shown.map(function (a, i) {
                return '<li role="option" id="pal-' + a.id + '" data-i="' + i + '" aria-selected="' + (i === sel) + '"><span>' + t(a.en, a.es) + '</span><small>' + a.group + '</small></li>';
            }).join('');
            input.setAttribute('aria-activedescendant', 'pal-' + shown[sel].id);
            var active = list.children[sel];
            if (active && active.scrollIntoView) active.scrollIntoView({ block: 'nearest' });
        }
        function run(i) {
            var a = shown[i];
            if (!a) return;
            close();
            a.run();
        }
        function open() {
            closeMobileMenu(); // un-inert the page so palette commands can focus targets
            opener = document.activeElement;
            input.value = '';
            input.placeholder = t('Type a command or search…', 'Escribe un comando o busca…');
            sel = 0;
            render();
            dlg.showModal();
            input.focus();
        }
        function close() {
            if (dlg.open) dlg.close();
        }
        dlg.addEventListener('close', function () { if (opener && opener.focus) opener.focus(); });
        dlg.addEventListener('click', function (e) {
            if (e.target === dlg) { close(); return; }
            var li = e.target.closest('li[data-i]');
            if (li) run(parseInt(li.getAttribute('data-i'), 10));
        });
        input.addEventListener('input', function () { sel = 0; render(); });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); sel = (sel + 1) % Math.max(1, shown.length); render(); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); sel = (sel - 1 + shown.length) % Math.max(1, shown.length); render(); }
            else if (e.key === 'Enter') { e.preventDefault(); run(sel); }
        });
        document.addEventListener('keydown', function (e) {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                if (dlg.open) close(); else open();
            } else if (e.key === '/' && !dlg.open && !/input|textarea|select/i.test(document.activeElement.tagName)) {
                e.preventDefault();
                open();
            }
        });
        document.querySelectorAll('[data-open-palette]').forEach(function (b) { b.addEventListener('click', open); });
        var hint = document.querySelector('.nav-cmd kbd');
        if (hint && !/Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)) hint.textContent = 'Ctrl K';
    }

    // ---- EU/EEA privacy notice ----
    // Shown only when the browser's time zone is in Europe. Detection is local
    // (Intl API): no geo-IP lookup, so nothing about the visitor leaves the page.
    function inEuropeanTimeZone() {
        try {
            var tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
            return /^(?:Europe\/|Atlantic\/(?:Canary|Madeira|Azores|Reykjavik)$)/.test(tz);
        } catch (e) { return false; }
    }

    function initPrivacyNote() {
        if (store(PRIVACY_KEY) === '1') return;
        var force = /[?&]privacy-note=1\b/.test(location.search);
        if (!force && !inEuropeanTimeZone()) return;
        var note = document.createElement('aside');
        note.className = 'privacy-note';
        note.setAttribute('aria-label', 'Privacy');
        document.body.appendChild(note);
        function paint() {
            note.innerHTML =
                '<b><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' + t('GDPR · privacy', 'RGPD · privacidad') + '</b>' +
                t('No cookies, no analytics, no trackers. Fonts are self-hosted; this browser only stores your language choice and that you closed this note. ',
                  'Sin cookies, sin analítica, sin rastreadores. Las fuentes se sirven desde este sitio; este navegador solo guarda tu idioma y que cerraste este aviso. ') +
                '<a href="/privacy.html">' + t('Details', 'Detalles') + '</a>' +
                '<div class="privacy-note-actions"><button type="button">' + t('Got it', 'Entendido') + '</button></div>';
            note.querySelector('button').addEventListener('click', function () {
                store(PRIVACY_KEY, '1');
                note.classList.remove('show');
                setTimeout(function () { note.remove(); }, 600);
            });
        }
        paint();
        document.addEventListener('ddt:lang', function () { if (note.isConnected) paint(); });
        setTimeout(function () { note.classList.add('show'); }, reduceMotion ? 0 : 1800);
    }

    // ---- In-page anchors honour reduced motion and update the URL ----
    function initAnchors() {
        document.addEventListener('click', function (e) {
            var a = e.target.closest && e.target.closest('a[href^="#"]');
            if (!a) return;
            var hash = a.getAttribute('href');
            if (hash.length < 2) return;
            if (go(hash)) e.preventDefault();
        });
    }

    // ---- 3D mesh-field background (lazy, self-hosted Three.js) ----
    function initField() {
        var el = document.getElementById('field');
        if (!el) return;
        var conn = navigator.connection;
        if (conn && (conn.saveData || /(^|-)2g$/.test(conn.effectiveType || ''))) return;
        var load = function () {
            import('/assets/js/field.js?v=20260929b')
                .then(function (m) { m.startField(el, { reduceMotion: reduceMotion }); })
                .catch(function () { /* background is decorative; ignore */ });
        };
        if ('requestIdleCallback' in window) requestIdleCallback(load, { timeout: 2000 });
        else setTimeout(load, 1200);
    }

    function init() {
        initLanguage();
        initNavbar();
        initMobileMenu();
        initAnchors();
        initReveals();
        initCounters();
        initBoard();
        initSpotlight();
        initPalette();
        initPrivacyNote();
        initField();
    }

    window.DDT = {
        get lang() { return currentLang; },
        setLanguage: setLanguage,
        go: go,
        toast: toast,
        actions: actions
    };

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
