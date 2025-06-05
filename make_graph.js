const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const apps = {
  telegram: 'https://downdetector.su/status/telegram/',
  youtube: 'https://downdetector.su/status/youtube/',
  vkontakte: 'https://downdetector.su/status/vkontakte/',
  tiktok: 'https://downdetector.su/status/tiktok/',
};

async function generateGraph(appName) {
  const url = apps[appName];
  if (!url) {
    console.error(`Unknown app: ${appName}`);
    process.exit(1);
  }

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: 900, height: 500 });

  try {
    await page.goto(url, { waitUntil: 'networkidle2' });

    // Удаляем водяные знаки и кредиты Highcharts
    await page.evaluate(() => {
      const credits = document.querySelectorAll('.highcharts-credits, .watermark');
      credits.forEach(el => el.remove());
    });

    // Ждём появления графика
    await page.waitForSelector('#container');
    const graph = await page.$('#container');

    const outputDir = path.resolve(__dirname, 'graphs');
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);

    const filePath = path.join(outputDir, `${appName}_graph.png`);
    await graph.screenshot({ path: filePath });
    console.log(`✅ Saved: ${filePath}`);
  } catch (err) {
    console.error('❌ Error generating graph:', err);
  } finally {
    await browser.close();
  }
}

const appName = process.argv[2];
if (!appName) {
  console.error('Usage: node make_graph.js <appName>');
  process.exit(1);
}

generateGraph(appName);
