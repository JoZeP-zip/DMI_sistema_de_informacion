import { useState } from "react";
import "../styles/Checkout.css";
import { supabase } from "./supabase";

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

function Checkout({ total = 0, onClose }) {
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

    if (
      !formData.nombre ||
      !formData.telefono ||
      !formData.email ||
      !formData.direccion ||
      !formData.ciudad
    ) {
      alert("Completa todos los campos");
      return;
    }

    setLoading(true);

    const { error } = await supabase.from("pedidos").insert([
      {
        nombre: formData.nombre,
        telefono: formData.telefono,
        email: formData.email,
        direccion: formData.direccion,
        ciudad: formData.ciudad,
        metodo_pago: formData.metodoPago,
        total,
      },
    ]);

    setLoading(false);

    if (error) {
      console.error(error);
      alert("No se pudo registrar el pedido");
      return;
    }

    alert("Pedido registrado correctamente");

    setFormData({
      nombre: "",
      telefono: "",
      email: "",
      direccion: "",
      ciudad: "",
      metodoPago: "Nequi",
    });

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

        <p className="checkout-eyebrow">Paso final</p>
        <h2>Finalizar compra</h2>

        <form onSubmit={registrarPedido}>
          <div className="form-group">
            <label className="form-label">Datos de contacto</label>
            <div className="form-row">
              <input
                type="text"
                name="nombre"
                placeholder="Nombre completo"
                value={formData.nombre}
                onChange={handleChange}
              />
              <input
                type="text"
                name="telefono"
                placeholder="Telefono"
                value={formData.telefono}
                onChange={handleChange}
              />
            </div>
            <input
              type="email"
              name="email"
              placeholder="Correo electronico"
              value={formData.email}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Direccion de entrega</label>
            <div className="form-row">
              <input
                type="text"
                name="direccion"
                placeholder="Direccion"
                value={formData.direccion}
                onChange={handleChange}
              />
              <input
                type="text"
                name="ciudad"
                placeholder="Ciudad"
                value={formData.ciudad}
                onChange={handleChange}
              />
            </div>
          </div>

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
            <span className="checkout-total-value">${Number(total).toLocaleString("es-CO")}</span>
          </div>

          <button type="submit" className="checkout-submit" disabled={loading}>
            {loading ? "GUARDANDO..." : "CONFIRMAR COMPRA"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Checkout;
