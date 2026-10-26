// Captures the real help desk (frontend + backend + local model) as stills for the Remotion demo.
// Needs the app running on :3000 and the API on :8000.
import { writeFileSync } from "node:fs";
import { chromium } from "playwright-core";

const OUT = "public/shots";
const QUESTION = "Can I return order 1234?";
const QUESTION_BASIL = "Where is order 1234?";

const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const boxes = {};

async function box(name, selector) {
  const b = await page.locator(selector).first().boundingBox({ timeout: 2000 }).catch(() => null);
  if (b) boxes[name] = b;
}

async function shot(name) {
  await page.screenshot({ path: `${OUT}/${name}.png` });
}

async function scene(prefix, question) {
  await box(`${prefix}-textarea`, "#question");
  await box(`${prefix}-ask`, ".ask-button");
  const steps = [];
  for (let i = 0; i <= question.length; i += 2) steps.push(i);
  if (steps.at(-1) !== question.length) steps.push(question.length);
  for (const [n, i] of steps.entries()) {
    await page.fill("#question", question.slice(0, i));
    await shot(`${prefix}-type-${String(n).padStart(2, "0")}`);
  }
  boxes[`${prefix}-typeFrames`] = steps.length;
  await page.click(".ask-button");
  await page.waitForSelector(".loading");
  await page.waitForTimeout(1200);
  await shot(`${prefix}-loading`);
  await page.waitForSelector(".answer, .error", { timeout: 120000 });
  await page.waitForTimeout(2500);
  await shot(`${prefix}-answer`);
  await box(`${prefix}-answerText`, ".answer-text");
  await box(`${prefix}-cite`, ".call-number");
  await box(`${prefix}-openSpine`, ".spine.is-open");
  await box(`${prefix}-passage`, ".passage");
  await box(`${prefix}-shelf`, ".shelf-section");
  boxes[`${prefix}-answer`] = await page.locator(".answer-text").innerText();
}

await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
await shot("a-empty");
await scene("a", QUESTION);

await box("basilCard", '.library-card:has-text("Basil")');
await page.click('.library-card:has-text("Basil")');
await page.waitForTimeout(800);
await shot("b-empty");
await scene("b", QUESTION_BASIL);

writeFileSync(`${OUT}/boxes.json`, JSON.stringify(boxes, null, 2));
console.log(boxes["a-answer"], "\n---\n", boxes["b-answer"]);
await browser.close();
