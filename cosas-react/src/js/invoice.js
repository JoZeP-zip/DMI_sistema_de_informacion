const COMPANY = {
  name: "Disol Motors Injections",
  nit: "NIT/CC: Por definir",
  phone: "Telefono: Por definir",
  address: "Direccion: Por definir",
  city: "Colombia",
};

const money = (value) => `$${Number(value || 0).toLocaleString("es-CO")}`;

const escapeHtml = (value) =>
  String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const invoiceNumber = (prefix) => {
  const stamp = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  return `${prefix}-${stamp}`;
};

export const buildProductInvoice = ({ customer, items, total, paymentMethod, logoUrl }) => ({
  type: "PRODUCTOS",
  number: invoiceNumber("DMI-PROD"),
  date: new Date().toLocaleString("es-CO"),
  logoUrl,
  customer,
  paymentMethod,
  title: "Factura de venta",
  concept: "Compra de productos",
  items: items.map((item) => ({
    image: item.image || item.imagen || "",
    description: item.nombre || "Producto",
    code: item.codigo || "Sin codigo",
    quantity: Number(item.quantity || 1),
    unitPrice: Number(item.precioVenta || 0),
    total: Number(item.precioVenta || 0) * Number(item.quantity || 1),
  })),
  subtotal: Number(total || 0),
  total: Number(total || 0),
});

export const buildServiceInvoice = ({ customer, service, cost, logoUrl }) => ({
  type: "SERVICIO",
  number: invoiceNumber("DMI-SERV"),
  date: new Date().toLocaleString("es-CO"),
  logoUrl,
  customer,
  paymentMethod: "Pendiente/registrado por taller",
  title: "Factura de servicio",
  concept: service.motivo || "Mantenimiento o reparacion",
  items: [
    {
      image: "",
      description: service.motivo || "Servicio tecnico automotriz",
      code: service.placa || service.vehiculo || "Servicio",
      quantity: 1,
      unitPrice: Number(cost || 0),
      total: Number(cost || 0),
    },
  ],
  service,
  subtotal: Number(cost || 0),
  total: Number(cost || 0),
});

export const saveInvoiceLocally = (invoice, email = "invitado") => {
  const key = `dmiInvoices_${String(email || "invitado").toLowerCase()}`;
  const stored = JSON.parse(localStorage.getItem(key) || "[]");
  stored.unshift(invoice);
  localStorage.setItem(key, JSON.stringify(stored.slice(0, 25)));
};

export const openInvoiceDocument = (invoice) => {
  const invoiceWindow = window.open("", "_blank", "width=980,height=900");
  if (!invoiceWindow) {
    alert("El navegador bloqueo la factura. Permite ventanas emergentes para descargarla.");
    return;
  }

  const rows = invoice.items.map((item) => `
    <tr>
      <td class="product-cell">
        ${item.image ? `<img src="${escapeHtml(item.image)}" alt="">` : `<div class="no-image">DMI</div>`}
        <div>
          <strong>${escapeHtml(item.description)}</strong>
          <span>${escapeHtml(item.code)}</span>
        </div>
      </td>
      <td>${item.quantity}</td>
      <td>${money(item.unitPrice)}</td>
      <td>${money(item.total)}</td>
    </tr>
  `).join("");

  invoiceWindow.document.write(`
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>${escapeHtml(invoice.title)} ${escapeHtml(invoice.number)}</title>
        <style>
          * { box-sizing: border-box; }
          body { margin: 0; background: #111; color: #1d1d1f; font-family: Arial, sans-serif; }
          .toolbar { position: sticky; top: 0; display: flex; justify-content: flex-end; gap: 12px; padding: 14px 24px; background: #050505; border-bottom: 3px solid #e23345; }
          .toolbar button { border: 1px solid #e23345; background: #e23345; color: #fff; padding: 12px 18px; font-weight: 800; cursor: pointer; }
          .toolbar button.secondary { background: transparent; }
          .invoice { width: min(920px, calc(100vw - 32px)); margin: 26px auto; background: #fff; padding: 38px; border-top: 8px solid #e23345; }
          .head { display: grid; grid-template-columns: 1fr auto; gap: 24px; align-items: start; border-bottom: 2px solid #eee; padding-bottom: 24px; }
          .brand { display: flex; gap: 16px; align-items: center; }
          .brand img { width: 82px; height: 82px; object-fit: contain; }
          .brand h1 { margin: 0; font-size: 24px; text-transform: uppercase; }
          .brand p, .meta p, .customer p { margin: 4px 0; color: #666; }
          .meta { text-align: right; }
          .meta h2 { margin: 0 0 8px; color: #e23345; font-size: 28px; text-transform: uppercase; }
          .section { margin-top: 24px; }
          .section h3 { margin: 0 0 12px; color: #e23345; text-transform: uppercase; letter-spacing: 2px; font-size: 13px; }
          .customer { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; background: #f7f7f8; padding: 16px; }
          table { width: 100%; border-collapse: collapse; margin-top: 12px; }
          th { background: #2a1116; color: #fff; text-align: left; padding: 12px; font-size: 12px; text-transform: uppercase; }
          td { border-bottom: 1px solid #eee; padding: 12px; vertical-align: middle; }
          .product-cell { display: flex; gap: 12px; align-items: center; }
          .product-cell img, .no-image { width: 58px; height: 52px; object-fit: cover; border: 1px solid #ddd; background: #f2f2f2; display: grid; place-items: center; color: #e23345; font-weight: 900; }
          .product-cell span { display: block; margin-top: 4px; color: #777; font-size: 12px; }
          .totals { width: min(360px, 100%); margin-left: auto; margin-top: 20px; }
          .totals div { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
          .totals .grand { color: #e23345; font-size: 22px; font-weight: 900; }
          .legal { margin-top: 28px; color: #666; font-size: 12px; line-height: 1.55; border-top: 1px solid #eee; padding-top: 16px; }
          @media print {
            body { background: #fff; }
            .toolbar { display: none; }
            .invoice { width: 100%; margin: 0; box-shadow: none; }
          }
        </style>
      </head>
      <body>
        <div class="toolbar">
          <button onclick="window.print()">Descargar PDF</button>
          <button class="secondary" onclick="window.close()">Cerrar</button>
        </div>
        <main class="invoice">
          <header class="head">
            <div class="brand">
              ${invoice.logoUrl ? `<img src="${escapeHtml(invoice.logoUrl)}" alt="Logo DMI">` : ""}
              <div>
                <h1>${COMPANY.name}</h1>
                <p>${COMPANY.nit}</p>
                <p>${COMPANY.phone}</p>
                <p>${COMPANY.address} - ${COMPANY.city}</p>
              </div>
            </div>
            <div class="meta">
              <h2>${escapeHtml(invoice.title)}</h2>
              <p><strong>No.</strong> ${escapeHtml(invoice.number)}</p>
              <p><strong>Fecha:</strong> ${escapeHtml(invoice.date)}</p>
              <p><strong>Pago:</strong> ${escapeHtml(invoice.paymentMethod)}</p>
            </div>
          </header>

          <section class="section">
            <h3>Cliente</h3>
            <div class="customer">
              <p><strong>Nombre:</strong> ${escapeHtml(invoice.customer?.nombre || "Cliente")}</p>
              <p><strong>Documento:</strong> ${escapeHtml(invoice.customer?.documento || "No registrado")}</p>
              <p><strong>Correo:</strong> ${escapeHtml(invoice.customer?.email || "No registrado")}</p>
              <p><strong>Telefono:</strong> ${escapeHtml(invoice.customer?.telefono || "No registrado")}</p>
              <p><strong>Direccion:</strong> ${escapeHtml(invoice.customer?.direccion || "No registrada")}</p>
              <p><strong>Ciudad:</strong> ${escapeHtml(invoice.customer?.ciudad || "No registrada")}</p>
            </div>
          </section>

          <section class="section">
            <h3>Detalle</h3>
            <table>
              <thead>
                <tr>
                  <th>Concepto</th>
                  <th>Cant.</th>
                  <th>Valor unitario</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </section>

          <section class="totals">
            <div><span>Subtotal</span><strong>${money(invoice.subtotal)}</strong></div>
            <div><span>IVA</span><strong>Incluido/segun regimen</strong></div>
            <div class="grand"><span>Total</span><strong>${money(invoice.total)}</strong></div>
          </section>

          <p class="legal">
            Documento generado por sistema para soporte de compra o servicio. Debe complementarse con los datos tributarios definitivos de la empresa
            (NIT, direccion fiscal, regimen, numeracion autorizada y responsabilidades fiscales) antes de usarlo como factura electronica legal ante la DIAN.
          </p>
        </main>
      </body>
    </html>
  `);
  invoiceWindow.document.close();
};
