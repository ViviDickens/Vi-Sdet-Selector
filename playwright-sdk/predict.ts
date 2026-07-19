/**
 * Vi-Sdet-Selector TypeScript SDK
 *
 * Talks to the FastAPI /predict endpoint (server/app.py) and turns the
 * response into a locator string ready to hand to Playwright's
 * page.locator().
 *
 * Only calls /predict (deterministic, no API key needed) — never
 * /predict/explain, which needs ANTHROPIC_API_KEY and is meant for
 * human-readable explanations, not for driving test automation.
 */

export interface ElementDescriptor {
  tag: string;
  id?: string;
  classes?: string[];
  data_testid?: string;
  aria_label?: string;
  xpath?: string;
  text?: string;
}

export type LocatorStrategy = "data-testid" | "aria-label" | "css" | "xpath";

export interface Prediction {
  recommended_strategy: LocatorStrategy;
  confidence: number;
  reasoning: string[];
  alternative?: string;
}

const API_URL = process.env.VI_SDET_SELECTOR_URL ?? "http://localhost:8000";

/**
 * Calls POST /predict with the element's attributes and returns the
 * raw recommendation (strategy, confidence, reasoning, alternative).
 */
export async function predict(element: ElementDescriptor): Promise<Prediction> {
  const res = await fetch(`${API_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(element),
  });

  if (!res.ok) {
    throw new Error(`vi-sdet-selector /predict failed: ${res.status} ${await res.text()}`);
  }

  return res.json() as Promise<Prediction>;
}

/**
 * Turns a prediction + the original element descriptor into a locator
 * string Playwright can use directly: page.locator(await getLocator(el))
 *
 * @param element        the same attributes you'd send to /predict
 * @param testIdAttribute the actual DOM attribute your app uses for test
 *                        ids. Defaults to "data-testid", but real sites
 *                        vary — e.g. saucedemo.com uses "data-test".
 */
export async function getLocator(
  element: ElementDescriptor,
  testIdAttribute: string = "data-testid"
): Promise<string> {
  const prediction = await predict(element);

  switch (prediction.recommended_strategy) {
    case "data-testid":
      return `[${testIdAttribute}="${element.data_testid}"]`;
    case "aria-label":
      return `[aria-label="${element.aria_label}"]`;
    case "css":
      return element.id ? `#${element.id}` : element.tag;
    case "xpath":
      return element.xpath ? `xpath=${element.xpath}` : element.tag;
    default:
      return element.tag;
  }
}
