# Playwright SDK

TypeScript client for the Vi-Sdet-Selector API.

- **`predict.ts`** — calls `POST /predict` and turns the recommendation into
  a locator string you can hand straight to `page.locator(...)`.
- **`tests/saucedemo.spec.ts`** — a real, runnable example against
  [saucedemo.com](https://www.saucedemo.com), a purpose-built QA practice
  site. Demonstrates the AI-recommended `data-test` strategy driving an
  actual login flow.

## Setup

```bash
npm install
npx playwright install   # downloads browser binaries, first time only
```

## Run the demo

The API needs to be running first (from the repo root):

```bash
uvicorn server.app:app --reload
```

Then, from this folder:

```bash
npm test
```

## Using it in your own tests

```ts
import { getLocator } from "./predict";

const locator = await getLocator(
  { tag: "input", data_testid: "username" },
  "data-test" // the actual DOM attribute your app uses
);
await page.locator(locator).fill("standard_user");
```
