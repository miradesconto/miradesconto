#!/usr/bin/env node
/* Auditoria offline: apenas lê produtos.js; não consulta lojas nem altera preços. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, 'produtos.js'), 'utf8'), context, { timeout: 3000 });
const products = context.window.MIRA_DATA?.products;
if (!Array.isArray(products)) throw new Error('produtos.js não contém catálogo válido');
const now = Date.now();
const maxAge = 2 * 60 * 60 * 1000;
const counts = { total: products.length, recentes: 0, vencidos: 0, semEvidencia: 0, divergentes: 0, dataFutura: 0 };
const examples = [];
for (const p of products) {
  const e = p.priceCheck;
  let reason = '';
  if (!e || !e.checkedAt || e.status !== 'verified') reason = 'semEvidencia';
  else if (e.itemId !== (e.method === 'ml-sale-price-v1' ? (p.itemId || p.id) : p.id)
    || e.currency !== 'BRL' || e.price !== p.price || e.oldPrice !== p.oldPrice
    || !Number.isFinite(p.price) || p.price <= 0 || p.available === false) reason = 'divergentes';
  else {
    const ts = Date.parse(e.checkedAt);
    if (!Number.isFinite(ts)) reason = 'semEvidencia';
    else if (ts > now) reason = 'dataFutura';
    else if (now - ts > maxAge) reason = 'vencidos';
    else reason = 'recentes';
  }
  counts[reason]++;
  if (reason !== 'recentes' && examples.length < 30) examples.push({ id: p.id, problema: reason, checkedAt: e?.checkedAt || null });
}
const report = {
  geradoEm: new Date(now).toISOString(),
  limiteHoras: 2,
  aviso: 'Esta auditoria verifica evidências gravadas no catálogo, não consulta preços atuais no Mercado Livre.',
  contagens: counts,
  percentualRecente: counts.total ? Number((100 * counts.recentes / counts.total).toFixed(1)) : 0,
  exemplos: examples
};
console.log(JSON.stringify(report, null, 2));
if (process.argv.includes('--strict') && (counts.total === 0 || counts.recentes === 0)) process.exitCode = 1;
