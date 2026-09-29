# Agent edge Worker

GitHub Pages can't set headers or negotiate content, so it caps the Cloudflare Agent Readiness scan at level 2. Put this Worker in front of the site on a domain you control to reach level 5.

What it adds on top of the Pages origin:
- `Link` headers on HTML pages (api-catalog, service-desc, service-doc, describedby).
- `Accept: text/markdown` on `/` and `/consult.html` returns `index.md` / `consult.md` with `x-markdown-tokens`.
- A stateless, read-only MCP server at `/mcp` (tools: `get_profile`, `list_experience`, `search_portfolio`, `get_consulting_options`) and `/.well-known/mcp/server-card.json`.
- `application/linkset+json` on `/.well-known/api-catalog`.

## Deploy
1. Add the domain to Cloudflare and enable DNSSEC.
2. Set the route in `wrangler.toml`, then run `npx wrangler deploy` from this folder.
3. Point canonical URLs, `sitemap.xml`, `robots.txt`, and `llms.txt` at the new domain, and set it as the GitHub Pages custom domain (or keep github.io as a hidden origin).
4. Optional for full marks: DNS-AID records (`_mcp._agents.<domain>` SVCB) and `_catalog._agents.<domain>` TXT `url=https://<domain>/.well-known/ai-catalog.json`.

Local test: `node test.mjs`.
