# AGENTS.md

GitHub Pages portfolio for Danilo Díaz Tarascó, served from `master` at https://ddtdanilo.github.io. The repo must stay public.

## Rules
- Vanilla HTML/CSS/JS. No build step, no frameworks, no third-party requests at runtime (fonts are self-hosted, for GDPR).
- Every visible string supports EN/ES through `data-en` / `data-es` (and `data-aria-en` / `data-aria-es` for labels). Long prose uses `data-lang-block`.
- Privacy: never publish an email, phone number, birth date, address, nationality/residency details, or client/proprietary internals. Contact goes through LinkedIn. Strip metadata from images (use `cwebp`).
- Facts come from the private `cv-danilo` repo (`content/resume.yaml`). Keep `index.html`, `index.md`, `api/resume.json`, and `llms.txt` in sync.
- Commits: concise, English, conventional style. No `Co-Authored-By` or any AI attribution.

## Agent-readiness files
- After editing `index.md`, `consult.md`, a `SKILL.md`, or any JSON: run `python3 tools/build_agent_files.py`. It regenerates `llms-full.txt` and the skill digests, then validates JSON, local links, and email-like strings.
- `worker/` holds the Cloudflare Worker (Link headers, Markdown negotiation, MCP server). It needs a custom domain; see `worker/README.md`. Test it with `node worker/test.mjs`.
- Scan: `curl -s -X POST https://isitagentready.com/api/scan -H 'content-type: application/json' -d '{"url":"https://ddtdanilo.github.io"}'`.
