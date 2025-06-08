const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// 🔗 Обновлённые ссылки на Downdetector
const apps = {
  telegram: 'https://downdetector.su/telegram',
  youtube: 'https://downdetector.su/youtube',
  vkontakte: 'https://downdetector.su/vkontakte',
  tiktok: 'https://downdetector.su/tiktok',
};

async function generateGraph(appName) {
  const url = apps[appName];
  if (!url) {
    console.error(`Unknown app: ${appName}`);
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 900, height: 500 });

  try {
    await page.goto(url, { waitUntil: 'networkidle2' });

    // Удаление водяных знаков
    await page.evaluate(() => {
      const credits = document.querySelectorAll('.highcharts-credits, .watermark');
      credits.forEach(el => el.remove());
    });

    // Ожидание и выбор canvas-графика
    await page.waitForSelector('canvas');
    const graph = await page.$('canvas');

    if (!graph) {
      throw new Error('График (canvas) не найден на странице');
    }

    const outputDir = path.resolve(__dirname, 'graphs');
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);

    const filePath = path.join(outputDir, `${appName}_graph.png`);
    await graph.screenshot({ path: filePath });

    console.log(`✅ Saved: ${filePath}`);
  } catch (err) {
    console.error('❌ Error generating graph:', err);
    process.exit(1);
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

