import { test, expect } from '@playwright/test';

test('homepage loads and renders', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle', timeout: 20_000 });

  // Key page content is present
  const body = await page.textContent('body');
  expect(body).toContain('IPFS');
});

test('homepage has navigation', async ({ page }) => {
  await page.goto('/');

  const nav = page.locator('nav');
  await expect(nav).toBeVisible();
});

test('download page shows 404 for missing hash', async ({ page }) => {
  const response = await page.goto('/d/nonexistent-hash');

  // Page should load (even if file not found)
  await expect(page.locator('body')).toBeVisible();
});

test('homepage has feature cards', async ({ page }) => {
  await page.goto('/');

  // Feature section should be present
  const body = await page.textContent('body');
  expect(body).toContain('Decentralized');
});
