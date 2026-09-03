import { test, expect } from '@playwright/test';

/**
 * Módulo de Pruebas UI: Creación de Recurso / Agendamiento de Citas
 * 
 * Flujo completo verificado en el sistema:
 * 1. Login con el usuario real: zapatadxd@gmail.com / @Cazta2006
 * 2. Cierre del modal de bienvenida ("Entrar al sistema")
 * 3. Acceso al módulo de citas: ruta '/citas' o botón 'Agendar cita' de Mi Cuenta
 * 4. Verificación de garaje:
 *    - Si no posee vehículos aún: maneja la pantalla "Primero registra tu vehiculo"
 *      y completa el registro básico.
 * 5. Diligenciamiento de los 6 parámetros del formulario de cita:
 *    - vehiculos_idvehiculo (select de vehículos de Mi Garaje)
 *    - descripcion_vehiculo (textarea de estado o falla)
 *    - fecha_cita (input tipo date, regla: hoy hasta 2 meses adelante)
 *    - hora_cita (select de horarios de taller disponibles)
 *    - motivo (select de servicios automotrices activos)
 *    - observaciones (textarea de notas adicionales)
 * 6. Envío mediante botón "Confirmar cita"
 * 7. Validación de la confirmación: "Cita agendada" y "Hemos registrado tu cita exitosamente."
 */

test.describe('Agendar Cita Flow', () => {
  const userCredentials = {
    email: process.env.TEST_USER_EMAIL || 'zapatadxd@gmail.com',
    password: process.env.TEST_USER_PASSWORD || '@Cazta2006',
  };

  test('Proceso completo: Inicio de sesión, parametrización y agendamiento exitoso de cita', async ({ page }) => {
    // ==========================================
    // PASO 1: AUTENTICACIÓN
    // ==========================================
    await page.goto('/login');

    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button[type="submit"]:has-text("INGRESAR")');

    await expect(emailInput).toBeVisible({ timeout: 25000 });
    await emailInput.fill(userCredentials.email);
    await passwordInput.fill(userCredentials.password);
    await submitButton.click();

    // Confirmar modal de bienvenida
    const welcomeModalBtn = page.locator('button:has-text("Entrar al sistema")');
    try {
      await welcomeModalBtn.waitFor({ state: 'visible', timeout: 8000 });
      await welcomeModalBtn.click();
    } catch {
      // Si el modal no se presentó, continuar
    }

    // ==========================================
    // PASO 2: NAVEGAR A AGENDAR CITA
    // ==========================================
    await page.goto('/citas');
    await page.waitForLoadState('domcontentloaded');

    // ==========================================
    // PASO 3: VALIDAR GARAJE (VEHÍCULO PREVIO)
    // ==========================================
    // En caso de que la cuenta aún no tenga vehículos registrados
    const noVehicleNotice = page.locator('h2:has-text("Primero registra tu vehiculo")');
    if (await noVehicleNotice.isVisible({ timeout: 4000 }).catch(() => false)) {
      const btnRegistrar = page.locator('button:has-text("Registrar vehiculo")');
      await btnRegistrar.click();

      // Completar vehículo rápido para habilitar la cita
      const placaInput = page.locator('input[name="placa"]');
      if (await placaInput.isVisible({ timeout: 5000 }).catch(() => false)) {
        await page.fill('input[name="codigo"]', 'VEH-' + Math.floor(Math.random() * 9000 + 1000));
        await placaInput.fill('XYZ' + Math.floor(Math.random() * 900 + 100));
        await page.fill('input[name="marca"]', 'Mazda');
        await page.fill('input[name="modelos"]', '3 Skyactiv');
        await page.selectOption('select[name="tipoVehiculo"]', { index: 1 }).catch(() => {});
        await page.click('button[type="submit"]');
        await page.waitForTimeout(2000);
        await page.goto('/citas');
      }
    }

    // ==========================================
    // PASO 4: COMPLETAR PARÁMETROS DEL FORMULARIO
    // ==========================================
    // 4.1 Selección del vehículo
    const vehiculoSelect = page.locator('select[name="vehiculos_idvehiculo"]');
    if (await vehiculoSelect.isVisible().catch(() => false)) {
      const optionsCount = await vehiculoSelect.locator('option').count();
      if (optionsCount > 0) {
        await vehiculoSelect.selectOption({ index: 0 });
      }
    }

    // 4.2 Descripción de la falla o motivo de ingreso
    const descTextarea = page.locator('textarea[name="descripcion_vehiculo"]');
    if (await descTextarea.isVisible().catch(() => false)) {
      await descTextarea.fill('Mantenimiento preventivo general, revisión de inyección electrónica y cambio de filtros.');
    }

    // 4.3 Fecha de la cita (dentro de los 2 meses calendario permitidos)
    const citaDate = new Date();
    citaDate.setDate(citaDate.getDate() + 3); // 3 días en el futuro
    const yyyy = citaDate.getFullYear();
    const mm = String(citaDate.getMonth() + 1).padStart(2, '0');
    const dd = String(citaDate.getDate()).padStart(2, '0');
    const fechaISO = `${yyyy}-${mm}-${dd}`;

    const fechaInput = page.locator('input[name="fecha_cita"]');
    await expect(fechaInput).toBeVisible({ timeout: 10000 });
    await fechaInput.fill(fechaISO);
    await fechaInput.dispatchEvent('change');

    // 4.4 Hora disponible en el taller (se habilita tras fijar la fecha)
    const horaSelect = page.locator('select[name="hora_cita"]');
    await expect(horaSelect).toBeEnabled({ timeout: 10000 });
    const availableOption = await horaSelect
      .locator('option:not([disabled]):not([value=""])')
      .first()
      .getAttribute('value');
    await horaSelect.selectOption(availableOption || '10:00');

    // 4.5 Servicio automotriz requerido
    const motivoSelect = page.locator('select[name="motivo"]');
    await expect(motivoSelect).toBeVisible();
    const serviceOption = await motivoSelect
      .locator('option:not([disabled]):not([value=""])')
      .first()
      .getAttribute('value');
    await motivoSelect.selectOption(serviceOption || { index: 1 });

    // 4.6 Observaciones adicionales
    const obsTextarea = page.locator('textarea[name="observaciones"]');
    if (await obsTextarea.isVisible().catch(() => false)) {
      await obsTextarea.fill('Prueba automatizada de agendamiento Playwright con credenciales reales.');
    }

    // Captura de evidencia 4: Formulario de cita completamente diligenciado
    await page.screenshot({ path: 'screenshots/04_cita_formulario_diligenciado.png', fullPage: true });

    // ==========================================
    // PASO 5: ENVIAR FORMULARIO
    // ==========================================
    const confirmButton = page.locator('button[type="submit"]:has-text("Confirmar cita")');
    await expect(confirmButton).toBeEnabled();
    await confirmButton.click();

    // ==========================================
    // PASO 6: ASERCIÓN DE CITA CONFIRMADA
    // ==========================================
    // La pantalla de AgendarCita.js renderiza la tarjeta de éxito:
    // <h2>Cita agendada</h2>
    // <p>Te esperamos en Disol Motors. Hemos registrado tu cita exitosamente.</p>
    const successTitle = page.locator('h2:has-text("Cita agendada")');
    const successMessage = page.locator('text=/Hemos registrado tu cita exitosamente|Cita guardada/i');

    await expect(successTitle).toBeVisible({ timeout: 25000 });
    await expect(successMessage).toBeVisible();

    // Captura de evidencia 5: Pantalla de confirmación de cita agendada
    await page.screenshot({ path: 'screenshots/05_cita_agendada_confirmada.png', fullPage: true });

    // Verifica que el botón de agendar otra cita se encuentre disponible
    const agendarOtraBtn = page.locator('button:has-text("Agendar otra")');
    await expect(agendarOtraBtn).toBeVisible();
  });
});
