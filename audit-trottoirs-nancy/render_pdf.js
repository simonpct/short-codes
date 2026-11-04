// Imprime le HTML en PDF balisé (structure, alt, langue) avec Chromium.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [html, pdf] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(html), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: pdf, format: 'A4', printBackground: true, preferCSSPageSize: true, tagged: true, outline: true });
  await browser.close();
})();
