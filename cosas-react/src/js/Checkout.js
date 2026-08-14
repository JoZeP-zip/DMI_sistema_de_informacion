import { useState } from "react";
import "../styles/Checkout.css";
import { CheckoutService, MiCuentaService } from "../services/api";
import { buildProductInvoice, openInvoiceDocument, saveInvoiceLocally } from "./invoice";
import { showDmiError, showDmiSuccess } from "./DmiMessages";

const LOGO_DMI = "/assets/images/logoempresaXD.png";

const PAYMENT_METHODS = [
  {
    value: "Nequi",
    label: "Nequi",
    color: "#ff1493",
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
        <rect x="2" y="2" width="20" height="20" rx="6" fill="#ff1493" />
        <text x="12" y="16" textAnchor="middle" fontSize="11" fontWeight="700" fill="#000" fontFamily="Arial">
          N
        </text>
      </svg>
    ),
  },
  {
    value: "Daviplata",
    label: "Daviplata",
    color: "#e4002b",
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
        <rect x="2" y="2" width="20" height="20" rx="6" fill="#e4002b" />
        <text x="12" y="16" textAnchor="middle" fontSize="10" fontWeight="700" fill="#fff" fontFamily="Arial">
          DP
        </text>
      </svg>
    ),
  },
  {
    value: "PSE",
    label: "PSE",
    color: "#0033a0",
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
        <rect x="2" y="2" width="20" height="20" rx="6" fill="#0033a0" />
        <text x="12" y="16" textAnchor="middle" fontSize="9" fontWeight="700" fill="#fff" fontFamily="Arial">
          PSE
        </text>
      </svg>
    ),
  },
  {
    value: "Bancolombia",
    label: "Bancolombia",
    color: "#ffd100",
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
        <rect x="2" y="2" width="20" height="20" rx="6" fill="#ffd100" />
        <text x="12" y="16" textAnchor="middle" fontSize="9" fontWeight="700" fill="#000" fontFamily="Arial">
          BC
        </text>
      </svg>
    ),
  },
  {
    value: "Transferencia",
    label: "Transferencia Bancaria",
    color: "#888888",
    icon: (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#fff" strokeWidth="2">
        <rect x="2" y="2" width="20" height="20" rx="6" fill="#444" stroke="none" />
        <path d="M4 10h16M4 14h16M7 6l-2 4M17 6l2 4M7 18l-2-4M17 18l2-4" strokeLinecap="round" />
      </svg>
    ),
  },
];

function Checkout({ total = 0, items = [], onClose, onPaid, factura = null, onInvoicePaymentRequested }) {
  const esPagoFactura = Boolean(factura);
  const [formData, setFormData] = useState({
    nombre: "",
    telefono: "",
    email: "",
    direccion: "",
    ciudad: "",
    metodoPago: "Nequi",
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const registrarPedido = async (e) => {
    e.preventDefault();

    // Una factura no se marca pagada desde el navegador. Cuando Wompi este
    // conectado, este mismo punto abrira su pasarela y el webhook confirmara
    // el pago de forma segura en el servidor.
    if (esPagoFactura) {
      setLoading(true);
      try {
        const intent = await MiCuentaService.prepararPagoFactura(factura.idfactura, formData.metodoPago);
        onInvoicePaymentRequested?.(intent);
        if (intent?.checkout_url) {
          // El enlace de Wompi es el checkout real. Wompi volvera al sitio
          // cuando configures una URL de redireccion en su panel.
          window.location.assign(intent.checkout_url);
          return;
        }
      } catch (error) {
        setLoading(false);
        showDmiError("No se pudo preparar el pago", error.message || "Verifica la factura e intentalo nuevamente.");
        return;
      }
      setLoading(false);
      showDmiSuccess(
        "Pago listo para continuar",
        "Seleccionaste " + formData.metodoPago + ". La factura conserva su estado pendiente hasta que Wompi confirme el pago.",
      );
      onClose?.();
      return;
    }

    if (
      !formData.nombre ||
      !formData.telefono ||
      !formData.email ||
      !formData.direccion ||
      !formData.ciudad
    ) {
      showDmiError("Informacion incompleta", "Completa todos los campos para poder registrar tu pedido.");
      return;
    }

    setLoading(true);

    try {
      await CheckoutService.registrarPedido({ datos: formData, items });
    } catch (error) {
      console.error(error);
      setLoading(false);
      showDmiError("No se pudo registrar", "No se pudo guardar el pedido. Revisa la informacion e intenta nuevamente.");
      return;
    }

    setLoading(false);

    const invoice = buildProductInvoice({
      customer: {
        nombre: formData.nombre,
        telefono: formData.telefono,
        email: formData.email,
        direccion: formData.direccion,
        ciudad: formData.ciudad,
      },
      items,
      total,
      paymentMethod: formData.metodoPago,
      logoUrl: LOGO_DMI,
    });

    saveInvoiceLocally(invoice, formData.email);
    openInvoiceDocument(invoice);

    showDmiSuccess("Pedido registrado", "Tu pedido fue guardado correctamente. La factura se abrio en una nueva ventana para descargarla en PDF.");

    setFormData({
      nombre: "",
      telefono: "",
      email: "",
      direccion: "",
      ciudad: "",
      metodoPago: "Nequi",
    });

    if (onPaid) {
      onPaid(invoice);
    }

    if (onClose) {
      onClose();
    }
  };

  return (
    <div className="checkout-overlay">
      <div className="checkout-container">
        <button className="checkout-close" onClick={onClose} type="button">
          X
        </button>

        <p className="checkout-eyebrow">DMI / {esPagoFactura ? "Pago de factura" : "Paso final"}</p>
        <h2>{esPagoFactura ? "Pagar factura" : "Finalizar compra"}</h2>
        <p className="checkout-intro">
          {esPagoFactura
            ? "Selecciona el medio con el que deseas pagar tu servicio. El pago sera confirmado de forma segura por Wompi."
            : "Confirma tus datos y selecciona tu medio de pago."}
        </p>

        <form onSubmit={registrarPedido}>
          {esPagoFactura ? (
            <div className="checkout-invoice-summary">
              <span>Factura de servicio</span>
              <strong>{factura.codigo_factura}</strong>
              <small>Saldo pendiente: ${Number(factura.saldo ?? factura.total ?? total).toLocaleString("es-CO")}</small>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label className="form-label">Datos de contacto</label>
                <div className="form-row">
                  <input type="text" name="nombre" placeholder="Nombre completo" value={formData.nombre} onChange={handleChange} />
                  <input type="text" name="telefono" placeholder="Telefono" value={formData.telefono} onChange={handleChange} />
                </div>
                <input type="email" name="email" placeholder="Correo electronico" value={formData.email} onChange={handleChange} />
              </div>

              <div className="form-group">
                <label className="form-label">Direccion de entrega</label>
                <div className="form-row">
                  <input type="text" name="direccion" placeholder="Direccion" value={formData.direccion} onChange={handleChange} />
                  <input type="text" name="ciudad" placeholder="Ciudad" value={formData.ciudad} onChange={handleChange} />
                </div>
              </div>
            </>
          )}

          <div className="payment-methods">
            <h3>Metodo de pago</h3>

            <div className="payment-grid">
              {PAYMENT_METHODS.map((method) => (
                <label
                  key={method.value}
                  className={`payment-option ${formData.metodoPago === method.value ? "selected" : ""}`}
                  style={{ "--accent": method.color }}
                >
                  <input
                    type="radio"
                    name="metodoPago"
                    value={method.value}
                    checked={formData.metodoPago === method.value}
                    onChange={handleChange}
                  />
                  <span className="payment-icon">{method.icon}</span>
                  <span className="payment-label">{method.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="checkout-total">
            <span>{esPagoFactura ? "Saldo de la factura" : `${items.length} producto${items.length === 1 ? "" : "s"} facturado${items.length === 1 ? "" : "s"}`}</span>
            <span className="checkout-total-value">${Number(esPagoFactura ? (factura.saldo ?? factura.total ?? total) : total).toLocaleString("es-CO")}</span>
          </div>

          <button type="submit" className="checkout-submit" disabled={loading}>
            {loading ? "PREPARANDO..." : esPagoFactura ? "CONTINUAR AL PAGO" : "CONFIRMAR COMPRA"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Checkout;
