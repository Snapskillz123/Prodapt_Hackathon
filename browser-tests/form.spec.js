import { test, expect } from "@playwright/test";
import { plan } from "./fixtures.js";

test("trip form validates, retains failures, submits preferences and displays a plan on mobile", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("Your name").fill("Form Explorer");
  await page.getByLabel("Email address").fill(`form-${Date.now()}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("test-password-for-roam");
  await page.getByRole("button", { name: "Let’s explore" }).click();
  await page.getByRole("button", { name: "Start with trip details" }).click();
  await page.getByLabel("Where are you headed?").fill("Jaipur, India");
  const start = new Date();
  start.setDate(start.getDate() + 7);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  const iso = (value) =>
    `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  await page.getByLabel("Departure date").fill(iso(start));
  await page.getByLabel("Last day of your trip").fill(iso(start));
  await page.getByRole("button", { name: "Create my itinerary" }).click();
  await expect(page.getByRole("alert")).toContainText("2–7 days");
  await page.getByLabel("Last day of your trip").fill(iso(end));
  await page.getByLabel("Total group budget (INR)").fill("10000");
  await page.getByRole("radio", { name: /Relaxed/ }).check();
  await page.getByLabel(/Anything else/).fill("Keep afternoons quiet.");
  await page.locator(".conversation-scroll").evaluate((element) => {
    element.scrollTop = 0;
  });
  await page.screenshot({ path: "artifacts/form-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator(".conversation-scroll").evaluate((element) => {
    element.scrollTop = 0;
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "artifacts/form-mobile.png", fullPage: true });
  let attempts = 0;
  await page.route("**/api/chats/*/preferences", async (route) => {
    const body = route.request().postDataJSON();
    expect(body.style).toBe("Relaxed");
    expect(body.requirements).toBe("Keep afternoons quiet.");
    expect(body.travellers).toBe(2);
    if (!attempts++)
      return route.fulfill({
        status: 502,
        json: { error: "Test provider unavailable" },
      });
    const id = route.request().url().split("/").at(-2);
    return route.fulfill({
      json: {
        id,
        title: "Trip to Jaipur",
        profile: plan.profile,
        plan,
        version: 1,
        messages: [
          { role: "user", content: "Plan from my preferences" },
          { role: "assistant", content: plan.summary },
        ],
      },
    });
  });
  await page.getByRole("button", { name: "Create my itinerary" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Test provider unavailable",
  );
  await expect(page.getByLabel("Where are you headed?")).toHaveValue(
    "Jaipur, India",
  );
  await page.getByRole("button", { name: "Create my itinerary" }).click();
  await expect(page.locator(".plan-panel")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Make it cheaper", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "itinerary", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: "budget", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.getByRole("button", { name: "Open navigation" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete my account & data" }).click();
  await expect(
    page.getByRole("heading", { name: "A world of possibilities." }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
