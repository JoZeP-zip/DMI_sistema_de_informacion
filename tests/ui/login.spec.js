import { test, expect } from '@playwright/test';

/**
 * Módulo de Pruebas UI: Login / Control de Acceso
 * Credenciales analizadas del sistema:
 * - Usuario: zapatadxd@gmail.com
 * - Contraseña: @Cazta2006 (cumple con mínimo 8 caracteres y al menos 1 símbolo)
 */

test.describe('Login Flow', () => {
  const credentials = {
    email: process.env.TEST_USER_EMAIL || 'zapatadxd@gmail.com',
    password: process.env.TEST_USER_PASSWORD || '@Cazta2006',
  };

  test('Usuario válido inicia sesión exitosamente', async ({ page }) => {
    // 1. Navegar a la pantalla de login
    await page.goto('/login');

    // 2. Localizar inputs del formulario de acceso de DMI
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button[type="submit"]', { hasText: /ingresar|iniciar/i });

    await expect(emailInput).toBeVisible({ timeout: 30000 });
    await expect(passwordInput).toBeVisible();

    // 3. Ingresar las credenciales validadas
    await emailInput.fill(credentials.email);
    await passwordInput.fill(credentials.password);

    // 4. Enviar el formulario
    await submitButton.click();

    // 5. Validar y confirmar el modal de bienvenida (DmiDialog: "Bienvenidos a Disol Motors Injections")
    const welcomeBtn = page.getByRole('button', { name: /entrar al sistema|aceptar|entendido/i });
    try {
      await welcomeBtn.waitFor({ state: 'visible', timeout: 5000 });
      await welcomeBtn.click();
    } catch {
      // Continuar si el modal no se presentó o se cerró automáticamente
    }

    // 6. Verificar que la sesión quedó activa en el sistema
    await page.waitForTimeout(2000);
    const hasToken = await page.evaluate(() => Boolean(localStorage.getItem('token')));

    if (hasToken) {
      expect(hasToken).toBe(true);
    } else {
      // Fallback para interfaz directa
      await expect(
        page.locator('button:has-text("MI CUENTA"), button:has-text("PANEL ADMIN"), .dmi-nav-icon.profile, .dmi-profile-avatar')
      ).toBeVisible({ timeout: 8000 });
    }
  });

  test('Rechaza credenciales inválidas y muestra notificación', async ({ page }) => {
    await page.goto('/login');

    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button[type="submit"]', { hasText: /ingresar|iniciar/i });

    await emailInput.fill('no_existe@disolmotors.com');
    await passwordInput.fill('@ClaveFalsa123');
    await submitButton.click();

    // El sistema levanta un modal de aviso (DmiDialog) con el error
    const errorNotice = page.locator('.dmi-dialog-box, [role="dialog"], .alert, text=/correo|contraseÃ±a|credenciales|incorrect/i');
    await expect(errorNotice).toBeVisible({ timeout: 8000 });
  });
});
