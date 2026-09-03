import { test, expect } from '@playwright/test';

test.describe('Home Page - Página Principal', () => {
  test('Muestra sección principal y elementos del taller', async ({ page }) => {
    await page.goto('/');

    // Validar encabezado o título de marca de Disol Motors
    const brandElement = page.locator('h1.hero-title, .navbar-brand, text=/DISOL MOTORS|Disol Motors/i');
    await expect(brandElement.first()).toBeVisible({ timeout: 15000 });

    // Validar presencia de opciones de navegación o acciones principales
    const navOrHero = page.locator('.hero-viewport, nav, .dmi-nav-cta, text="EXPLORAR GALERIA"');
    await expect(navOrHero.first()).toBeVisible();
  });
});
