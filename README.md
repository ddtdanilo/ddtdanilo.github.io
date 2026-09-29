# ddtdanilo.github.io

Personal portfolio of Danilo Díaz Tarascó, CTO and electronics engineer. Live at https://ddtdanilo.github.io.

- Vanilla HTML/CSS/JS, bilingual EN/ES, no build step, no dependencies.
- Hero "signal path" board in inline SVG, a command palette (⌘K / Ctrl K), and scroll reveals that respect `prefers-reduced-motion`.
- Privacy by default: no cookies, no analytics, fonts self-hosted, zero third-party requests. A subtle GDPR note appears only for European time zones (detected locally, no geo-IP). See `privacy.html`.
- Agent-ready: `llms.txt`, `llms-full.txt`, Markdown twins (`index.md`, `consult.md`), JSON Resume (`api/resume.json`) with an OpenAPI spec, RFC 9727 API catalog, Agent Skills index, ARD `ai-catalog.json`, Content Signals in `robots.txt`, and in-page WebMCP tools (`assets/js/agent.js`).
- `worker/`: an optional Cloudflare Worker for header-level features (Link headers, Markdown negotiation, MCP server).

See `AGENTS.md` for conventions.
