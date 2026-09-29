/**
 * Agent-readiness edge for ddtdanilo.github.io (Cloudflare Worker).
 *
 * GitHub Pages can't set response headers, so this Worker sits in front of it
 * on a custom domain and adds what the Cloudflare Agent Readiness scan expects
 * from a server:
 *   - Link headers (RFC 8288) on HTML pages
 *   - Markdown content negotiation (Accept: text/markdown -> *.md twin)
 *   - A read-only MCP server (Streamable HTTP, stateless) at /mcp
 *   - /.well-known/mcp/server-card.json describing it
 * Everything else is proxied unchanged from GitHub Pages.
 */

const PROTOCOL_VERSION = '2025-06-18';
const SERVER_INFO = { name: 'ddtdanilo-portfolio', title: 'Danilo Díaz Tarascó portfolio', version: '2026.09.29' };

const MARKDOWN_TWINS = { '/': '/index.md', '/index.html': '/index.md', '/consult.html': '/consult.md' };

const LINK_HEADER = [
  '</.well-known/api-catalog>; rel="api-catalog"',
  '</api/openapi.json>; rel="service-desc"; type="application/openapi+json"',
  '</llms.txt>; rel="service-doc"; type="text/plain"',
  '</api/resume.json>; rel="describedby"; type="application/json"',
  '</.well-known/mcp/server-card.json>; rel="mcp-server-card"; type="application/json"',
].join(', ');

const TOOLS = [
  {
    name: 'get_profile',
    title: 'Get profile',
    description: 'Short professional profile of Danilo Díaz Tarascó: headline, summary, location, languages, public links.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'list_experience',
    title: 'List experience',
    description: 'Professional roles with company, dates (YYYY-MM), and highlights, most recent first.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'integer', minimum: 1, maximum: 10 } },
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'search_portfolio',
    title: 'Search portfolio',
    description: 'Full-text search across roles, projects, skills, and awards.',
    inputSchema: {
      type: 'object',
      properties: { query: { type: 'string', minLength: 2 } },
      required: ['query'],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'get_consulting_options',
    title: 'Get consulting options',
    description: 'Paid 1:1 consulting sessions (duration, USD price, scope) and Stripe booking links. Never pay without explicit user confirmation.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
];

function originUrl(env, path) {
  return new URL(path, env.ORIGIN || 'https://ddtdanilo.github.io').toString();
}

async function fetchJson(env, path) {
  const res = await fetch(originUrl(env, path), { cf: { cacheTtl: 300 } });
  if (!res.ok) throw new Error(`${path} returned ${res.status}`);
  return res.json();
}

function wantsMarkdown(request) {
  const accept = request.headers.get('Accept') || '';
  return /(^|,)\s*text\/markdown/i.test(accept);
}

function serverCard(baseUrl) {
  return {
    $schema: 'https://static.modelcontextprotocol.io/schemas/mcp-server-card/v1.json',
    version: '1.0',
    protocolVersion: PROTOCOL_VERSION,
    serverInfo: SERVER_INFO,
    description: 'Read-only facts about Danilo Díaz Tarascó (CTO, electronics engineer) and his consulting offer.',
    documentationUrl: `${baseUrl}/llms.txt`,
    transport: { type: 'streamable-http', endpoint: '/mcp' },
    capabilities: { tools: { listChanged: false } },
    authentication: { required: false, schemes: [] },
    tools: TOOLS.map(({ name, title, description }) => ({ name, title, description })),
  };
}

// ---- MCP tool implementations -------------------------------------------

async function callTool(env, name, args) {
  const resume = name === 'get_consulting_options' ? null : await fetchJson(env, '/api/resume.json');
  switch (name) {
    case 'get_profile':
      return {
        name: resume.basics.name,
        headline: resume.basics.label,
        summary: resume.basics.summary,
        location: `${resume.basics.location.city}, ${resume.basics.location.countryCode}`,
        languages: resume.languages.map((l) => `${l.language} (${l.fluency})`),
        profiles: resume.basics.profiles.map((p) => p.url),
      };
    case 'list_experience': {
      const limit = Math.min(Math.max(Number(args.limit) || 10, 1), 10);
      return resume.work.slice(0, limit).map((w) => ({
        position: w.position, company: w.name, start: w.startDate, end: w.endDate || 'present', highlights: w.highlights,
      }));
    }
    case 'search_portfolio': {
      const q = String(args.query || '').toLowerCase().trim();
      if (q.length < 2) throw new RpcError(-32602, 'query must be at least 2 characters');
      const hits = [];
      const scan = (kind, title, body, url) => {
        if (`${title} ${body}`.toLowerCase().includes(q)) hits.push({ kind, title, detail: body, url });
      };
      resume.work.forEach((w) => scan('role', `${w.position} @ ${w.name}`, w.highlights.join(' ')));
      resume.projects.forEach((p) => scan('project', p.name, p.description, p.url));
      resume.skills.forEach((s) => scan('skill', s.name, s.keywords.join(', ')));
      resume.awards.forEach((a) => scan('award', a.title, a.summary || ''));
      return hits;
    }
    case 'get_consulting_options':
      return fetchJson(env, '/api/consulting.json');
    default:
      throw new RpcError(-32602, `Unknown tool: ${name}`);
  }
}

class RpcError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

async function handleRpc(env, msg) {
  const { id, method, params = {} } = msg;
  const isNotification = id === undefined || id === null;
  try {
    let result;
    switch (method) {
      case 'initialize':
        result = {
          protocolVersion: PROTOCOL_VERSION,
          capabilities: { tools: { listChanged: false } },
          serverInfo: SERVER_INFO,
          instructions: 'Read-only portfolio data. Contact is LinkedIn only; no email or phone is published.',
        };
        break;
      case 'ping':
        result = {};
        break;
      case 'tools/list':
        result = { tools: TOOLS };
        break;
      case 'tools/call': {
        const data = await callTool(env, params.name, params.arguments || {});
        result = { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }], structuredContent: Array.isArray(data) ? { items: data } : data, isError: false };
        break;
      }
      default:
        if (isNotification) return null;
        throw new RpcError(-32601, `Method not found: ${method}`);
    }
    return isNotification ? null : { jsonrpc: '2.0', id, result };
  } catch (err) {
    if (isNotification) return null;
    const code = err instanceof RpcError ? err.code : -32603;
    return { jsonrpc: '2.0', id, error: { code, message: err.message } };
  }
}

async function handleMcp(request, env) {
  const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type, Mcp-Protocol-Version, Mcp-Session-Id', 'Access-Control-Allow-Methods': 'POST, OPTIONS' };
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
  if (request.method !== 'POST') {
    return new Response('This MCP endpoint is stateless: POST JSON-RPC only.', { status: 405, headers: { Allow: 'POST, OPTIONS', ...cors } });
  }
  let body;
  try { body = await request.json(); } catch {
    return Response.json({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }, { status: 400, headers: cors });
  }
  const batch = Array.isArray(body);
  const replies = (await Promise.all((batch ? body : [body]).map((m) => handleRpc(env, m)))).filter(Boolean);
  if (!replies.length) return new Response(null, { status: 202, headers: cors });
  return Response.json(batch ? replies : replies[0], { headers: cors });
}

function approxTokens(text) {
  return String(Math.ceil(text.length / 4));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const base = `${url.protocol}//${url.host}`;

    if (url.pathname === '/mcp') return handleMcp(request, env);
    if (url.pathname === '/.well-known/mcp/server-card.json') {
      return Response.json(serverCard(base), { headers: { 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'public, max-age=3600' } });
    }

    const twin = MARKDOWN_TWINS[url.pathname];
    if (twin && request.method === 'GET' && wantsMarkdown(request)) {
      const res = await fetch(originUrl(env, twin));
      const text = await res.text();
      return new Response(text, {
        status: res.status,
        headers: {
          'Content-Type': 'text/markdown; charset=utf-8',
          'Vary': 'Accept',
          'x-markdown-tokens': approxTokens(text),
          'Link': LINK_HEADER,
          'Cache-Control': 'public, max-age=300',
        },
      });
    }

    const upstream = await fetch(originUrl(env, url.pathname + url.search), request);
    const headers = new Headers(upstream.headers);
    if (url.pathname === '/.well-known/api-catalog') headers.set('Content-Type', 'application/linkset+json');
    if ((headers.get('Content-Type') || '').includes('text/html')) {
      headers.append('Link', LINK_HEADER);
      if (twin) headers.set('Vary', 'Accept');
    }
    return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers });
  },
};
