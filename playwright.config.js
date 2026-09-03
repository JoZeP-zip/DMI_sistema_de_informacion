import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/ui',
  // Carpeta dedicada para almacenar las capturas de pantalla y evidencias del navegador
  outputDir: './screenshots',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  // Ejecución en una sola ventana / secuencial
  fullyParallel: false,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    // Vistas en puerto 3000 (React)
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    browserName: 'chromium',
    headless: false,
    viewport: { width: 1280, height: 720 },
    video: 'on-first-retry',
    // 'on': Captura evidencia gráfica en todas las pruebas (tanto exitosas como fallidas)
    screenshot: 'on',
    trace: 'on-first-retry',
  },
  // Un solo navegador Desktop Chrome
  projects: [
    {
      name: 'Desktop Chrome',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
