// Local smoke test: node worker/test.mjs (serves origin files from the repo).
import { readFile } from 'node:fs/promises';
import worker from './src/index.js';

const root = new URL('../', import.meta.url);
globalThis.fetch = async (input) => {
  const path = new URL(typeof input === 'string' ? input : input.url).pathname;
  const file = path.endsWith('/') ? path + 'index.html' : path;
  try {
    const body = await readFile(new URL('.' + file, root));
    const type = file.endsWith('.html') ? 'text/html; charset=utf-8' : file.endsWith('.json') ? 'application/json' : 'text/plain';
    return new Response(body, { headers: { 'Content-Type': type } });
  } catch { return new Response('not found', { status: 404 }); }
};

const env = { ORIGIN: 'https://ddtdanilo.github.io' };
const call = (path, init) => worker.fetch(new Request('https://edge.test' + path, init), env);
const rpc = (msg) => call('/mcp', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(msg) });
const assert = (cond, label) => { if (!cond) { console.error('FAIL', label); process.exitCode = 1; } else console.log('ok  ', label); };

let r = await call('/');
assert(r.headers.get('Link')?.includes('rel="api-catalog"'), 'HTML has Link header');
r = await call('/', { headers: { Accept: 'text/markdown' } });
assert(r.headers.get('Content-Type').startsWith('text/markdown') && Number(r.headers.get('x-markdown-tokens')) > 100, 'markdown negotiation');
r = await call('/.well-known/api-catalog');
assert(r.headers.get('Content-Type') === 'application/linkset+json', 'api-catalog content type');
r = await call('/.well-known/mcp/server-card.json');
const card = await r.json();
assert(card.serverInfo.name && card.transport.endpoint === '/mcp', 'server card');
r = await rpc({ jsonrpc: '2.0', id: 1, method: 'initialize', params: {} });
assert((await r.json()).result.protocolVersion, 'initialize');
r = await rpc({ jsonrpc: '2.0', method: 'notifications/initialized' });
assert(r.status === 202, 'notification -> 202');
r = await rpc({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
assert((await r.json()).result.tools.length === 4, 'tools/list');
r = await rpc({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'search_portfolio', arguments: { query: 'LoRa' } } });
assert((await r.json()).result.structuredContent.items.length > 0, 'search_portfolio');
r = await rpc({ jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'get_consulting_options', arguments: {} } });
assert((await r.json()).result.structuredContent.sessions.length === 3, 'get_consulting_options');
r = await rpc({ jsonrpc: '2.0', id: 5, method: 'nope' });
assert((await r.json()).error.code === -32601, 'unknown method');
