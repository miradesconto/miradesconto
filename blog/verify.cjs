const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const entries = JSON.parse(fs.readFileSync(path.join(__dirname, 'pautas.json'), 'utf8'));
assert(!/Kingston|NV3|aggregateRating|"@type":"Review"|"@type":"Article"/.test(html));
assert.equal((html.match(/class="card"/g) || []).length, entries.length);
const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map(m=>m[1]);
assert.equal(new Set(ids).size, ids.length, 'IDs duplicados');
for (const [,url] of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
 if (/^https:/.test(url)) continue;
 const [file,fragment] = url.split('#');
 const target = path.resolve(__dirname, file.split('?')[0] || 'index.html');
 assert(fs.existsSync(target), `Destino ausente: ${url}`);
 if (!file && fragment) assert(ids.includes(fragment), `Âncora ausente: ${url}`);
}
const schema = JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1]);
assert(schema['@graph'].some(item=>item['@type'] === 'CollectionPage'));
assert(html.includes('../favicon.svg'));
console.log('OK: links locais, âncoras, favicon, estrutura e ausência de reviews fictícios.');
