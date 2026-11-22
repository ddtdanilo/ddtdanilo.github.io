/* ============================================
   WebMCP tools (https://webmachinelearning.github.io/webmcp/)
   Read-only tools that in-browser AI agents can call. Nothing is shown
   in the UI; data comes from same-origin static JSON.
   ============================================ */

(function () {
    'use strict';

    var SECTIONS = ['top', 'about', 'work', 'experience', 'expertise', 'lab', 'contact'];
    var cache = {};

    function getJSON(path) {
        if (!cache[path]) {
            cache[path] = fetch(path, { headers: { Accept: 'application/json' } }).then(function (r) {
                if (!r.ok) throw new Error(path + ' returned ' + r.status);
                return r.json();
            });
        }
        return cache[path];
    }

    function text(value) {
        return { content: [{ type: 'text', text: typeof value === 'string' ? value : JSON.stringify(value, null, 2) }] };
    }

    function lang() { return (window.DDT && window.DDT.lang) || 'en'; }

    var tools = [
        {
            name: 'get_profile',
            description: 'Get a short professional profile of Danilo Díaz Tarascó (CTO, electronics engineer): headline, summary, location, languages, and public links.',
            inputSchema: { type: 'object', properties: {}, additionalProperties: false },
            annotations: { readOnlyHint: true },
            execute: function () {
                return getJSON('/api/resume.json').then(function (r) {
                    return text({
                        name: r.basics.name,
                        headline: r.basics.label,
                        summary: r.basics.summary,
                        location: r.basics.location.city + ', ' + r.basics.location.countryCode,
                        languages: r.languages.map(function (l) { return l.language + ' (' + l.fluency + ')'; }),
                        profiles: r.basics.profiles.map(function (p) { return p.url; }),
                        contact: 'LinkedIn: https://linkedin.com/in/ddtdanilo'
                    });
                });
            }
        },
        {
            name: 'list_experience',
            description: 'List professional roles with company, dates (YYYY-MM), and highlights, most recent first.',
            inputSchema: {
                type: 'object',
                properties: { limit: { type: 'integer', minimum: 1, maximum: 10, description: 'Maximum number of roles to return.' } },
                additionalProperties: false
            },
            annotations: { readOnlyHint: true },
            execute: function (args) {
                var limit = (args && args.limit) || 10;
                return getJSON('/api/resume.json').then(function (r) {
                    return text(r.work.slice(0, limit).map(function (w) {
                        return { position: w.position, company: w.name, start: w.startDate, end: w.endDate || 'present', highlights: w.highlights };
                    }));
                });
            }
        },
        {
            name: 'search_portfolio',
            description: 'Full-text search across roles, projects, skills, and awards on this portfolio. Returns matching items with their source section.',
            inputSchema: {
                type: 'object',
                properties: { query: { type: 'string', minLength: 2, description: 'Keywords, e.g. "LoRa", "AWS", "FCC".' } },
                required: ['query'],
                additionalProperties: false
            },
            annotations: { readOnlyHint: true },
            execute: function (args) {
                var q = String((args && args.query) || '').toLowerCase().trim();
                if (q.length < 2) return Promise.resolve(text('Query must be at least 2 characters.'));
                return getJSON('/api/resume.json').then(function (r) {
                    var hits = [];
                    function scan(kind, title, body, url) {
                        if ((title + ' ' + body).toLowerCase().indexOf(q) !== -1) hits.push({ kind: kind, title: title, detail: body, url: url || undefined });
                    }
                    r.work.forEach(function (w) { scan('role', w.position + ' @ ' + w.name, w.highlights.join(' ')); });
                    r.projects.forEach(function (p) { scan('project', p.name, p.description + ' ' + (p.keywords || []).join(' '), p.url); });
                    r.skills.forEach(function (s) { scan('skill', s.name, s.keywords.join(', ')); });
                    r.awards.forEach(function (a) { scan('award', a.title, a.summary || ''); });
                    return text(hits.length ? hits : 'No matches for "' + q + '".');
                });
            }
        },
        {
            name: 'get_consulting_options',
            description: 'Get paid consulting session options (duration, price in USD, what it covers) and their booking links.',
            inputSchema: { type: 'object', properties: {}, additionalProperties: false },
            annotations: { readOnlyHint: true },
            execute: function () {
                return getJSON('/api/consulting.json').then(text);
            }
        },
        {
            name: 'navigate_to_section',
            description: 'Scroll the portfolio page to a section so the user can see it.',
            inputSchema: {
                type: 'object',
                properties: { section: { type: 'string', enum: SECTIONS, description: 'Section id.' } },
                required: ['section'],
                additionalProperties: false
            },
            annotations: { readOnlyHint: true },
            execute: function (args) {
                var id = args && args.section;
                if (SECTIONS.indexOf(id) === -1) return Promise.resolve(text('Unknown section. Use one of: ' + SECTIONS.join(', ')));
                if (!document.getElementById(id)) { location.href = '/#' + id; return Promise.resolve(text('Opening /#' + id)); }
                window.DDT.go('#' + id);
                return Promise.resolve(text('Scrolled to #' + id));
            }
        },
        {
            name: 'set_language',
            description: 'Switch the page language between English ("en") and Spanish ("es").',
            inputSchema: {
                type: 'object',
                properties: { lang: { type: 'string', enum: ['en', 'es'] } },
                required: ['lang'],
                additionalProperties: false
            },
            annotations: { readOnlyHint: true },
            execute: function (args) {
                var ok = window.DDT && window.DDT.setLanguage(args && args.lang);
                return Promise.resolve(text(ok ? 'Language set to ' + args.lang : 'Use "en" or "es".'));
            }
        }
    ];

    // ---- Register with the browser's model context (feature-detected) ----
    var modelContext = document.modelContext || navigator.modelContext;
    if (modelContext && typeof modelContext.registerTool === 'function') {
        var controller = typeof AbortController === 'function' ? new AbortController() : null;
        tools.forEach(function (tool) {
            try {
                var res = modelContext.registerTool(tool, controller ? { signal: controller.signal } : undefined);
                if (res && typeof res.catch === 'function') res.catch(function () {});
            } catch (e) { /* older builds may reject options; keep going */ }
        });
        window.addEventListener('pagehide', function () { if (controller) controller.abort(); });
    }

})();
