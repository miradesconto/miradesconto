/* PR-only smoke test: render real Jekyll output in Chromium at desktop and mobile widths. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');
const root = path.resolve('_site');
const screenshots = path.resolve('visual-screenshots');
const mime = {'.html':'text/html', '.css':'text/css', '.js':'text/javascript', '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp'};
const server = http.createServer((req,res) => {
  let pathname;
  try { pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); }
  catch { res.writeHead(400); res.end(); return; }
  let filename = path.resolve(root, '.' + pathname);
  if (!filename.startsWith(root + path.sep) && filename !== root) { res.writeHead(403); res.end(); return; }
  try {
    if (fs.statSync(filename).isDirectory()) filename = path.join(filename, 'index.html');
    res.writeHead(200, {'Content-Type':mime[path.extname(filename)] || 'application/octet-stream'});
    fs.createReadStream(filename).pipe(res);
  } catch { res.writeHead(404); res.end('Not found'); }
});
(async () => {
 await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
 fs.mkdirSync(screenshots, {recursive:true});
 const address = 'http://127.0.0.1:' + server.address().port;
 const browser = await chromium.launch({headless:true, args:['--no-sandbox']});
 try {
  for (const device of [{name:'desktop',width:1440,height:900},{name:'mobile',width:390,height:844}]) {
   const page = await browser.newPage({viewport:{width:device.width,height:device.height},deviceScaleFactor:1});
   for (const sitePage of [
    {name:'ofertas-pt',url:'/'},
    {name:'guias-pt',url:'/blog/'},
    {name:'ofertas-en',url:'/en/'},
    {name:'guias-en',url:'/en/blog/'},
   ]) {
    await page.goto(address+sitePage.url,{waitUntil:'domcontentloaded',timeout:25000});
    await page.locator('.mira-global-nav').waitFor({state:'visible',timeout:10000});
    const results = await page.evaluate(() => {
     const nav = document.querySelector('.mira-global-nav');
     const rect=nav.getBoundingClientRect();
     return {h1:document.querySelectorAll('h1').length, navCount:nav.querySelectorAll('a').length,navWidth:Math.round(rect.width),horizontalOverflow:Math.max(0,document.documentElement.scrollWidth-innerWidth),title:document.title};
    });
    assert.equal(results.h1,1,sitePage.name+' needs one H1');
    assert.equal(results.navCount,3,sitePage.name+' must have three menu entries');
    assert.ok(results.horizontalOverflow<=8,sitePage.name+' overflows '+device.name+' by '+results.horizontalOverflow+'px');
    if(sitePage.name==='ofertas-pt'){
      await page.locator('[data-layout-option="gamer"]').click();
      assert.equal(await page.locator('html').getAttribute('data-mira-layout'),'gamer');
      await page.locator('[data-layout-option="classic"]').click();
      assert.equal(await page.locator('html').getAttribute('data-mira-layout'),'classic');
      assert.equal(new URL(page.url()).pathname,'/','switching themes must not navigate');
    }
    if(sitePage.name==='ofertas-en') assert.ok(await page.locator('.en-deal-card').count()>=1,'EN product cards missing');
    if(sitePage.name==='guias-en') assert.equal(await page.locator('.en-guide-card').count(),3,'EN guide hub missing three guides');
    await page.screenshot({path:path.join(screenshots,sitePage.name+'-'+device.name+'.png'),fullPage:true,animations:'disabled'});
    console.log('VISUAL OK',sitePage.name,device.name,JSON.stringify(results));
   }
   await page.close();
  }
 } finally {await browser.close();}
})().catch(err=>{console.error(err.stack||err);process.exitCode=1;}).finally(()=>server.close());
