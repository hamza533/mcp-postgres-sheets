import { expect, test, type Page } from "@playwright/test";

import toolsData from "../src/data/tools.json";

const PAGES = [
  { path: "/", heading: /query your data/i },
  { path: "/docs/", heading: "Getting started" },
  { path: "/docs/quick-start/", heading: "Quick start" },
  { path: "/docs/configuration/", heading: "Configuration" },
  { path: "/docs/security/", heading: "Security model" },
  { path: "/docs/tools/", heading: "Tools reference" },
  { path: "/docs/remote/", heading: "Remote mode & OAuth" },
  { path: "/changelog/", heading: "Changelog" },
];

function trackErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  return errors;
}

for (const { path, heading } of PAGES) {
  test(`page ${path} loads without errors`, async ({ page }) => {
    const errors = trackErrors(page);
    const response = await page.goto(path);
    expect(response?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    await expect(page.getByRole("link", { name: "PG Sheets MCP home" })).toBeVisible();
    await expect(page.getByTestId("version-badge")).toHaveText(`v${toolsData.version}`);
    expect(errors).toEqual([]);
  });
}

test("install command copy button puts the command on the clipboard", async ({ page }) => {
  await page.goto("/");
  const install = page.getByTestId("install-command");
  await install.getByTestId("copy-button").click();
  await expect(install.getByTestId("copy-button")).toHaveAttribute("data-copied", "true");
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe("uvx mcp-postgres-sheets");
});

test("every quick-start code block copies its own code", async ({ page }) => {
  await page.goto("/docs/quick-start/");
  const blocks = page.getByTestId("code-block").filter({ visible: true });
  const count = await blocks.count();
  expect(count).toBeGreaterThanOrEqual(3);
  for (let i = 0; i < count; i++) {
    const block = blocks.nth(i);
    await block.getByTestId("copy-button").click();
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    const shown = (await block.locator("pre").innerText()).trim();
    expect(copied.trim()).toBe(shown);
  }
});

test("client tabs switch the config block", async ({ page }) => {
  await page.goto("/docs/quick-start/");
  await page.getByRole("tab", { name: "Claude Code" }).click();
  await expect(page.getByText("claude mcp add postgres-sheets")).toBeVisible();
  await page.getByRole("tab", { name: "ChatGPT (remote)" }).click();
  await expect(page.getByText("Server URL:")).toBeVisible();
  await expect(page.getByTestId("success-alert")).toBeVisible();
});

test("tools reference lists every tool from tools/list and filters", async ({ page }) => {
  await page.goto("/docs/tools/");
  const cards = page.getByTestId("tool-card");
  await expect(cards).toHaveCount(toolsData.tools.length);
  for (const tool of toolsData.tools) {
    await expect(page.locator(`#${tool.name}`)).toBeVisible();
  }
  await page.getByRole("button", { name: "write" }).click();
  await expect(cards).toHaveCount(2);
  await expect(page.getByText("Hidden when READ_ONLY=true · requires idempotency_key").first()).toBeVisible();
  await page.getByRole("button", { name: "all" }).click();
  await page.getByTestId("tools-filter").fill("append");
  await expect(cards).toHaveCount(1);
  await expect(cards.first().getByRole("cell", { name: "idempotency_key", exact: true })).toBeVisible();
});

test("configuration table is searchable", async ({ page }) => {
  await page.goto("/docs/configuration/");
  await expect(page.getByTestId("env-row").first()).toBeVisible();
  await page.getByTestId("env-filter").fill("OAUTH_");
  const rows = page.getByTestId("env-row");
  await expect(rows).toHaveCount(3);
  await expect(page.locator("#OAUTH_ISSUER")).toBeVisible();
});

test("search palette navigates to a tool", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("search-button").click();
  await page.getByPlaceholder("Search pages, tools, settings…").fill("postgres_query");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/docs\/tools\/#postgres_query$/);
});

test("theme toggle switches to dark mode", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  await page.getByTestId("theme-toggle").click();
  await expect(page.locator("html")).toHaveClass(/dark/);
});

test("security page reports the safety suite", async ({ page }) => {
  await page.goto("/docs/security/");
  await expect(page.getByTestId("layers").getByRole("listitem")).toHaveCount(5);
  await page.getByTestId("all-cases").locator("summary").click();
  await expect(page.getByTestId("all-cases").getByText("DROP TABLE")).toBeVisible();
});

test("Ctrl+K opens the search palette", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("search-button")).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.keyboard.press("Control+k");
  await expect(page.getByPlaceholder("Search pages, tools, settings…")).toBeVisible();
});

test("quick-start prompts copy on click and the next-step link works", async ({ page }) => {
  await page.goto("/docs/quick-start/");
  const prompt = page.getByTestId("prompt-list").getByRole("button").first();
  await prompt.click();
  await expect(prompt).toContainText("Copied");
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(
    "What tables are in the database",
  );
  await page.getByTestId("next-page").click();
  await expect(page.getByRole("heading", { level: 1, name: "Security model" })).toBeVisible();
});
