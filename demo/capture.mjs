// Captures the real help desk (frontend + backend + local model) as stills for the Remotion demo.
// Needs the app running on :3000, the API on :8000 and Keycloak on :8080 (docker compose up -d).
// Each customer signs in off camera, in a browser context of their own; the video never shows the login.
import { writeFileSync } from "node:fs";
import { chromium } from "playwright-core";

const OUT = "public/shots";
const QUESTION = "Can I return order 1234?";
const QUESTION_BASIL = "Where is order 1234?";

const WEB = "http://localhost:3000";
const browser = await chromium.launch({ channel: "chrome" });
const boxes = {};
let page;

/** A fresh browser, signed in as `user` (the demo users have their own name as password), on the desk. */
async function signedInPage(user) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  const p = await context.newPage();
  await p.goto(WEB); // no session: the page sends us to Keycloak
  await p.waitForURL("http://localhost:8080/**");
  await p.fill("#username", user);
  await p.fill("#password", user);
  await p.click("#kc-login");
  await p.waitForSelector("#question");
  return p;
}

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

page = await signedInPage("ada");
await page.waitForLoadState("networkidle");
await page.waitForTimeout(1500);
await shot("a-empty");
await scene("a", QUESTION);

page = await signedInPage("basil");
await page.waitForLoadState("networkidle");
await page.waitForTimeout(1500);
await shot("b-empty");
await scene("b", QUESTION_BASIL);

writeFileSync(`${OUT}/boxes.json`, JSON.stringify(boxes, null, 2));
console.log(boxes["a-answer"], "\n---\n", boxes["b-answer"]);
await browser.close();
