import puppeteer from 'puppeteer-core';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = '/Users/luongdh/Mylab/AISDLC Solution/logs/1hr_battle_test/screenshots';

async function main() {
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--window-size=1280,900']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });

  console.log('Navigating to http://localhost:5173...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });

  // 1. Capture catalog
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_catalog.png') });
  console.log('Captured 01_catalog.png');

  // 2. Click "Add to Cart" buttons
  const addToCartButtons = await page.$$('.product-card button, .card button, button');
  let clicked = 0;
  for (const btn of addToCartButtons) {
    const text = await page.evaluate(el => el.textContent, btn);
    if (text && text.includes('Add to Cart')) {
      await btn.click();
      clicked++;
      if (clicked >= 2) break;
    }
  }
  console.log(`Clicked Add to Cart ${clicked} times`);

  // Wait a moment for state update
  await new Promise(r => setTimeout(r, 500));

  // 3. Open Cart
  const buttons = await page.$$('button');
  for (const btn of buttons) {
    const text = await page.evaluate(el => el.textContent, btn);
    if (text && text.includes('Cart')) {
      await btn.click();
      console.log('Clicked Cart button');
      break;
    }
  }

  await new Promise(r => setTimeout(r, 600));
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_cart_drawer.png') });
  console.log('Captured 02_cart_drawer.png');

  // 4. Click Proceed to Checkout
  const checkoutButtons = await page.$$('button');
  for (const btn of checkoutButtons) {
    const text = await page.evaluate(el => el.textContent, btn);
    if (text && (text.includes('Checkout') || text.includes('Proceed'))) {
      await btn.click();
      console.log('Clicked Proceed to Checkout');
      break;
    }
  }

  await new Promise(r => setTimeout(r, 600));

  // Fill in checkout form inputs
  const inputs = await page.$$('input[type="text"], input[type="email"], input');
  if (inputs.length >= 3) {
    await inputs[0].type('Nguyen Van A');
    await inputs[1].type('vana@example.com');
    await inputs[2].type('123 Le Loi, District 1, HCMC');
  }

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_checkout_form.png') });
  console.log('Captured 03_checkout_form.png');

  await browser.close();
  console.log('Done capturing UI flow!');
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
