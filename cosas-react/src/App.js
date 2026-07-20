import React, { useEffect, useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min';
import './styles/App.css';

import RegistroVehiculo from './js/RegistrarUnidad.js';
import Contacto from './js/Contacto.js';
import AgendarCita from './js/AgendarCita.js';
import Catalogo from './js/Catalogo.js';
import DashboardAdmin from './js/DashboardAdmin.js';
import MiCuenta from './js/MiCuenta';

const getApiBaseUrl = () => {
  const { protocol, hostname } = window.location;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  if (hostname.includes("app.github.dev")) {
    return `${protocol}//${hostname.replace(/-3000\.app\.github\.dev$/, "-8000.app.github.dev")}`;
  }

  return "";
};

const getDisplayName = (userData) => {
  const rawName = userData?.nombre || userData?.name || userData?.usuarionombre || "";
  const fallback = userData?.email ? userData.email.split("@")[0] : "conductor";
  const name = (rawName || fallback).trim();

  return name.charAt(0).toUpperCase() + name.slice(1);
};

const DmiDialog = ({ dialog, onClose }) => {
  if (!dialog) return null;

  const handleConfirm = () => {
    if (dialog.onConfirm) dialog.onConfirm();
    else onClose();
  };

  return (
    <div
      className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center px-3"
      style={{
        zIndex: 9999,
        background: "rgba(0, 0, 0, 0.78)",
        backdropFilter: "blur(6px)"
      }}
    >
      <div
        className={`dmi-dialog-box w-100 ${dialog.productItems ? "dmi-dialog-box-products" : ""}`}
      >
        <p className="text-uppercase mb-2" style={{ color: "#ff2f55", letterSpacing: "3px", fontSize: "0.78rem" }}>
          {dialog.kicker || "Confirmacion"}
        </p>
        <h3 className="mb-3" style={{ color: "#ff2f55", letterSpacing: "1px", fontWeight: 800 }}>
          {dialog.title}
        </h3>
        <p className="mb-4" style={{ color: "#c9bcc2", lineHeight: 1.6 }}>
          {dialog.message}
        </p>

        {dialog.details && (
          <div className="mb-4" style={{ borderTop: "1px solid rgba(255,47,85,.45)", borderBottom: "1px solid rgba(255,47,85,.35)" }}>
            {dialog.details.map((item) => (
              <div key={item.label} className="d-flex justify-content-between gap-3 py-2">
                <span className="text-muted">{item.label}</span>
                <strong className="text-white text-end">{item.value}</strong>
              </div>
            ))}
          </div>
        )}

        {dialog.productItems && (
          <div className="dmi-dialog-products">
            {dialog.productItems.map((item) => {
              const quantity = Number(item.quantity || 1);
              const price = Number(item.precioVenta || 0);
              const total = price * quantity;

              return (
                <article className="dmi-dialog-product" key={`${item.id || item.codigo || item.nombre}-${quantity}`}>
                  <img
                    src={item.image || item.imagen || "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=300&auto=format&fit=crop"}
                    alt={item.nombre || "Producto"}
                  />
                  <div>
                    <strong>{item.nombre || "Producto"}</strong>
                    <span>{item.codigo || "Sin codigo"} - Cantidad {quantity}</span>
                  </div>
                  <b>{total ? `$${total.toLocaleString("es-CO")}` : "Sin valor"}</b>
                </article>
              );
            })}
          </div>
        )}

        <div className="d-flex flex-column flex-sm-row gap-3">
          <button
            type="button"
            className="btn btn-danger rounded-0 fw-bold py-3 flex-fill"
            onClick={handleConfirm}
            style={{ boxShadow: "0 0 20px rgba(255, 47, 85, 0.25)" }}
          >
            {dialog.confirmText || "Confirmar"}
          </button>

          {dialog.cancelText && (
            <button
              type="button"
              className="btn btn-outline-light rounded-0 fw-bold py-3 flex-fill"
              onClick={onClose}
              style={{ borderColor: "#ff2f55" }}
            >
              {dialog.cancelText}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const DmiToast = ({ toast, onClose }) => {
  if (!toast) return null;

  return (
    <div
      className="position-fixed end-0 bottom-0 m-4"
      style={{
        zIndex: 10000,
        width: "min(420px, calc(100vw - 32px))",
        background: "rgba(8, 8, 10, 0.96)",
        border: "1px solid #ff2f55",
        boxShadow: "0 0 24px rgba(255, 47, 85, 0.22)"
      }}
    >
      <div className="p-3 d-flex gap-3 align-items-start">
        <div className="bg-danger" style={{ width: "10px", minHeight: "56px" }}></div>
        <div className="flex-grow-1">
          <strong className="d-block text-danger text-uppercase mb-1" style={{ letterSpacing: "2px" }}>
            {toast.title}
          </strong>
          <span className="text-white-50">{toast.message}</span>
        </div>
        <button type="button" className="btn-close btn-close-white" aria-label="Cerrar" onClick={onClose}></button>
      </div>
    </div>
  );
};


// Componente para Iniciar Sesion
const LoginView = ({ onLoginSuccess, onSwitchToRegister }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch(getApiBaseUrl() + '/login-react', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || data.message || data.error || 'Credenciales invalidas.');
      } else {
        const token = data.access_token || data.token;
        const role = data.role || data.rol || "usuario";
        const userEmail = data.email || email;
        const nombre = data.nombre || data.name || data.usuarionombre || "";

        localStorage.setItem("token", token);
        localStorage.setItem("role", role);
        localStorage.setItem("email", userEmail);
        localStorage.setItem("nombre", nombre);
        localStorage.setItem("dmiSessionStartedAt", new Date().toISOString());
        window.history.replaceState(null, '', '/');
        onLoginSuccess({ email: userEmail, role, nombre });
      }
    } catch (err) {
      setError('No se pudo conectar con el servidor.');
    }
  };

  return (
    <div className="mx-auto" style={{ maxWidth: '400px' }}>
      <h3 className="text-center text-uppercase fw-black mb-4">
        Control de <span className="text-danger">Acceso</span>
      </h3>
      {error && <div className="alert alert-danger small py-2 rounded-0 border-danger bg-black text-danger">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="form-label text-white small fw-bold">CORREO ELECTRONICO</label>
          <input 
            type="email" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required 
          />
        </div>
        <div className="mb-4">
          <label className="form-label text-white small fw-bold">CONTRASENA</label>
          <input 
            type="password" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required 
          />
        </div>
        <button type="submit" className="btn btn-danger w-100 rounded-0 fw-bold py-2 tracking-widest mb-3">
          INGRESAR
        </button>
        <p className="text-center small text-muted">
          No tienes una cuenta? <span className="text-danger cursor-pointer fw-bold text-decoration-underline" style={{cursor: 'pointer'}} onClick={onSwitchToRegister}>Registrate aqui</span>
        </p>
      </form>
    </div>
  );
};

// NUEVO COMPONENTE: Vista para Registrar Usuarios Nuevos
const RegistroUsuarioView = ({ onRegisterSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nombre, setNombre] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    try {
      const response = await fetch(getApiBaseUrl() + '/registro-react', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ nombre, email, password, role: "usuario" }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        setError(data.error || data.message || data.detail || 'Error al registrar el usuario.');
      } else {
        setSuccess(true);
        setTimeout(() => {
          onRegisterSuccess(); // Redirige al login tras 2 segundos
        }, 2000);
      }
    } catch (err) {
      setError(err.message || 'Error de conexion con el servidor backend.');
    }
  };

  return (
    <div className="mx-auto" style={{ maxWidth: '400px' }}>
      <h3 className="text-center text-uppercase fw-black mb-4">
        Crear <span className="text-danger">Cuenta</span>
      </h3>
      {error && <div className="alert alert-danger small py-2 rounded-0 border-danger bg-black text-danger">{error}</div>}
      {success && <div className="alert alert-success small py-2 rounded-0 border-success bg-black text-success">Registro exitoso! Redirigiendo al login...</div>}
      <form onSubmit={handleRegister}>
        <div className="mb-3">
          <label className="form-label text-white small fw-bold">NOMBRE COMPLETO</label>
          <input 
            type="text" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            required 
          />
        </div>
        <div className="mb-3">
          <label className="form-label text-white small fw-bold">CORREO ELECTRONICO</label>
          <input 
            type="email" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required 
          />
        </div>
        <div className="mb-4">
          <label className="form-label text-white small fw-bold">CONTRASENA</label>
          <input 
            type="password" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required 
          />
        </div>
        <button type="submit" className="btn btn-danger w-100 rounded-0 fw-bold py-2 tracking-widest mb-3">
          REGISTRARSE
        </button>
        <p className="text-center small text-muted">
          Ya tienes cuenta? <span className="text-danger cursor-pointer fw-bold text-decoration-underline" style={{cursor: 'pointer'}} onClick={onRegisterSuccess}>Inicia sesion</span>
        </p>
      </form>
    </div>
  );
};

// Panel para el Usuario Comun
const DashboardUsuarioViejo = ({ user, showNotice, openConfirm }) => {
  const [citas, setCitas] = useState([
    { id: 1, fecha: '2026-06-25', hora: '09:00 AM', vehiculo: 'Porsche 911 GT3', servicio: 'Calibracion de Inyeccion', estado: 'En Espera' },
    { id: 2, fecha: '2026-06-12', hora: '02:30 PM', vehiculo: 'Porsche 911 GT3', servicio: 'Escaneo OBD-II', estado: 'Completado' }
  ]);

  const handleCancelarCita = (id) => {
    const cita = citas.find((item) => item.id === id);

    openConfirm({
      kicker: "Accion requerida",
      title: "Cancelar cita",
      message: "Revisa la cita antes de continuar. Esta accion quitara la cita de tu agenda.",
      confirmText: "Cancelar cita",
      cancelText: "Volver",
      details: [
        { label: "Vehiculo", value: cita?.vehiculo || "No disponible" },
        { label: "Servicio", value: cita?.servicio || "No disponible" },
        { label: "Fecha", value: cita ? `${cita.fecha} - ${cita.hora}` : "No disponible" }
      ],
      onConfirm: () => {
        setCitas(citas.filter(cita => cita.id !== id));
        showNotice("Cita cancelada", "La cita fue retirada de tu agenda correctamente.");
      }
    });
  };

  const handleEditarCita = (id) => {
    const cita = citas.find((item) => item.id === id);

    openConfirm({
      kicker: "Edicion de cita",
      title: "Modificar cita",
      message: "Aqui se abrira el formulario para ajustar fecha, hora o servicio de esta cita.",
      confirmText: "Entendido",
      details: [
        { label: "Cita", value: `#${id}` },
        { label: "Vehiculo", value: cita?.vehiculo || "No disponible" }
      ],
      onConfirm: () => showNotice("Formulario pendiente", "La siguiente mejora sera conectar aqui el formulario real de edicion.")
    });
  };

  return (
    <div>
      <h3 className="text-uppercase fw-black border-bottom border-danger pb-2 mb-4">
        Mi <span className="text-danger">Garaje y Citas</span>
      </h3>
      <p className="mb-4">Hola, <span className="text-danger fw-bold">{getDisplayName(user)}</span>. Desde aqui puedes gestionar los servicios programados para tu unidad.</p>
      
      <div className="table-responsive bg-black border border-secondary p-3">
        <h6 className="fw-bold text-uppercase tracking-widest text-muted mb-3">Historial de Citas Agendadas</h6>
        <table className="table table-dark table-hover align-middle mb-0">
          <thead>
            <tr className="text-muted small border-bottom border-danger">
              <th scope="col" className="py-3">FECHA</th>
              <th scope="col" className="py-3">HORA</th>
              <th scope="col" className="py-3">VEHICULO</th>
              <th scope="col" className="py-3">SERVICIO</th>
              <th scope="col" className="py-3">ESTADO</th>
              <th scope="col" className="py-3 text-center">ACCIONES</th>
            </tr>
          </thead>
          <tbody>
            {citas.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-center py-4 text-muted small">
                  No tienes citas registradas actualmente.
                </td>
              </tr>
            ) : (
              citas.map((cita) => (
                <tr key={cita.id} className="border-bottom border-secondary border-opacity-25">
                  <td className="fw-bold">{cita.fecha}</td>
                  <td>{cita.hora}</td>
                  <td><span className="text-danger">Ã°Å¸Å¡â€”</span> {cita.vehiculo}</td>
                  <td>{cita.servicio}</td>
                  <td>
                    <span className={`badge rounded-0 py-1 px-2 ${cita.estado === 'Completado' ? 'bg-secondary text-white' : 'bg-danger'}`}>
                      {cita.estado.toUpperCase()}
                    </span>
                  </td>
                  <td className="text-center">
                    <div className="d-flex justify-content-center gap-2">
                      <button 
                        className="btn btn-sm btn-outline-light rounded-0 fw-bold px-2 py-1" 
                        onClick={() => handleEditarCita(cita.id)}
                        disabled={cita.estado === 'Completado'}
                      >
                        MODIFICAR
                      </button>
                      <button 
                        className="btn btn-sm btn-danger rounded-0 fw-bold px-2 py-1" 
                        onClick={() => handleCancelarCita(cita.id)}
                        disabled={cita.estado === 'Completado'}
                      >
                        Ã°Å¸â€”â€˜Ã¯Â¸Â CANCELAR
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const heroSlides = [
  './assets/images/like.jpg',
  './assets/images/akira.jpg',
  './assets/images/fotoautos.jpg',
];

const DashboardUsuario = ({ user, openConfirm, goToView }) => {
  const [garage, setGarage] = useState(null);
  const [pendingCart, setPendingCart] = useState([]);
  const [pendingCartSessions, setPendingCartSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    const token = localStorage.getItem("token");
    const emailKey = String(localStorage.getItem("email") || user?.email || "invitado").toLowerCase();
    const cartKey = `dmiPendingCart_${emailKey}`;
    const cartSessionsKey = `dmiPendingCartSessions_${emailKey}`;

    const loadGarage = async () => {
      setLoading(true);
      setError("");
      try {
        const savedCart = localStorage.getItem(cartKey);
        if (mounted) {
          try {
            setPendingCart(savedCart ? JSON.parse(savedCart) : []);
            const savedSessions = JSON.parse(localStorage.getItem(cartSessionsKey) || "{}");
            let sessions = Object.values(savedSessions)
              .filter((session) => session && Array.isArray(session.items) && session.items.length)
              .sort((a, b) => String(b.fecha || "").localeCompare(String(a.fecha || "")));
            const currentCart = savedCart ? JSON.parse(savedCart) : [];
            if (!sessions.length && currentCart.length) {
              const sessionDate = (localStorage.getItem("dmiSessionStartedAt") || new Date().toISOString()).slice(0, 10);
              sessions = [{
                fecha: sessionDate,
                items: currentCart,
                updatedAt: new Date().toISOString()
              }];
            }
            setPendingCartSessions(sessions);
          } catch (cartError) {
            setPendingCart([]);
            setPendingCartSessions([]);
          }
        }

        const response = await fetch(`${getApiBaseUrl()}/api/mi-garage`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          credentials: "include"
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "No se pudo cargar tu garaje.");
        if (mounted) setGarage(data);
      } catch (err) {
        if (mounted) setError(err.message || "No se pudo cargar tu garaje.");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadGarage();
    return () => {
      mounted = false;
    };
  }, []);

  const usuario = garage?.usuario || {};
  const vehiculos = garage?.vehiculos || [];
  const citas = garage?.citas || [];
  const productos = garage?.productos || [];
  const pagos = garage?.pagos || [];
  const activeVehicle = vehiculos[0];
  const pendingCitas = citas.filter((cita) => String(cita.estado || "").toLowerCase() !== "completada");
  const completedCitas = citas.filter((cita) => String(cita.estado || "").toLowerCase() === "completada");
  const pendingSessionsCount = pendingCartSessions.reduce((acc, session) => acc + (session.items?.length || 0), 0);

  const money = (value) => {
    const number = Number(value || 0);
    return number ? `$${number.toLocaleString("es-CO")}` : "Sin valor";
  };
  const displayDate = (value) => value ? String(value).slice(0, 10) : "Sin fecha";
  const displayHour = (value) => value ? String(value).slice(0, 5) : "Sin hora";
  const statusClass = (estado) => {
    const normalized = String(estado || "").toLowerCase();
    if (normalized.includes("complet")) return "done";
    if (normalized.includes("cancel")) return "danger";
    return "active";
  };

  const showCitaDetail = (cita) => {
    openConfirm({
      kicker: "Detalle de cita",
      title: cita.motivo || "Cita registrada",
      message: "Esta es la informacion guardada para tu servicio.",
      confirmText: "Entendido",
      details: [
        { label: "Vehiculo", value: cita.vehiculo || cita.placa || "No disponible" },
        { label: "Fecha", value: `${displayDate(cita.fecha)} - ${displayHour(cita.hora)}` },
        { label: "Estado", value: cita.estado || "pendiente" },
        { label: "Notas", value: cita.notas || "Sin notas" }
      ],
      onConfirm: () => {}
    });
  };

  const sessionTotal = (session) =>
    (session.items || []).reduce((acc, item) => acc + Number(item.precioVenta || 0) * Number(item.quantity || 1), 0);

  const showPendingCart = (session) => {
    const items = session?.items || pendingCart;
    if (!items.length) return;

    openConfirm({
      kicker: "Productos pendientes",
      title: `Sesion del ${displayDate(session?.fecha || new Date().toISOString())}`,
      message: "Estos son los productos que agregaste al carrito ese dia.",
      confirmText: "Ir al catalogo",
      cancelText: "Cerrar",
      productItems: items,
      onConfirm: () => goToView("catalogo")
    });
  };

  if (loading) {
    return <section className="user-garage-shell"><div className="user-garage-loading">Cargando tu cuenta...</div></section>;
  }

  if (error) {
    return (
      <section className="user-garage-shell">
        <div className="user-garage-empty">
          <h3>No pudimos cargar tu cuenta</h3>
          <p>{error}</p>
          <button type="button" onClick={() => window.location.reload()}>Intentar de nuevo</button>
        </div>
      </section>
    );
  }

  return (
    <section className="user-garage-shell">
      <div className="user-garage-hero">
        <div>
          <span>Centro del cliente</span>
          <h3>Mi <strong>Cuenta</strong></h3>
          <p>
            Hola, <b>{usuario.nombre || getDisplayName(user)}</b>. Desde aqui administras tus vehiculos,
            agregas nuevos, agendas citas y consultas tu historial en DMI.
          </p>
        </div>
        <div className="user-garage-actions">
          <button type="button" onClick={() => goToView("registro")}>Agregar vehiculo</button>
          <button type="button" onClick={() => goToView("citas")}>Agendar cita</button>
        </div>
      </div>

      <div className="user-garage-stats">
        <article><span>Vehiculos</span><strong>{vehiculos.length}</strong></article>
        <article><span>Citas activas</span><strong>{pendingCitas.length}</strong></article>
        <article><span>Historial</span><strong>{completedCitas.length}</strong></article>
        <article><span>Productos pendientes</span><strong>{pendingSessionsCount || pendingCart.length}</strong></article>
      </div>

      <div className="user-garage-grid">
        <section className="user-garage-card user-garage-vehicle">
          <div className="user-garage-card-head">
            <span>Vehiculos de mi cuenta</span>
            <button type="button" onClick={() => goToView("registro")}>Actualizar</button>
          </div>
          {activeVehicle ? (
            <div className="vehicle-profile">
              <div className="vehicle-plate">{activeVehicle.placa || "SIN PLACA"}</div>
              <h4>{[activeVehicle.marca, activeVehicle.modelo].filter(Boolean).join(" ") || activeVehicle.descripcionvehiculo || "Vehiculo registrado"}</h4>
              <div className="vehicle-meta">
                <span>Tipo: <b>{activeVehicle.tipo_vehiculo || "No definido"}</b></span>
                <span>Motor: <b>{activeVehicle.motor || "No definido"}</b></span>
                <span>Capacidad: <b>{activeVehicle.capacidad || "No definida"}</b></span>
              </div>
            </div>
          ) : (
            <div className="user-garage-empty compact">
              <h4>No tienes vehiculo registrado</h4>
              <p>Registra tu unidad para agendar servicios mas rapido.</p>
            </div>
          )}
        </section>

        <section className="user-garage-card">
          <div className="user-garage-card-head">
            <span>Proximas citas</span>
            <button type="button" onClick={() => goToView("citas")}>Nueva cita</button>
          </div>
          <div className="appointment-list">
            {citas.length ? citas.slice(0, 4).map((cita) => (
              <button type="button" className="appointment-item" key={cita.idcita} onClick={() => showCitaDetail(cita)}>
                <div>
                  <strong>{cita.motivo || "Servicio programado"}</strong>
                  <span>{displayDate(cita.fecha)} - {displayHour(cita.hora)} - {cita.placa || cita.vehiculo || "Vehiculo"}</span>
                </div>
                <em className={statusClass(cita.estado)}>{cita.estado || "pendiente"}</em>
              </button>
            )) : (
              <div className="user-garage-empty compact">
                <h4>No hay citas registradas</h4>
                <p>Agenda tu primer servicio desde Mi Cuenta.</p>
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="user-garage-grid lower">
        <section className="user-garage-card">
          <div className="user-garage-card-head">
            <span>Productos pendientes</span>
            <button type="button" onClick={() => goToView("catalogo")}>Continuar compra</button>
          </div>
          <div className="purchase-list">
            {pendingCartSessions.length ? (
              <>
                {pendingCartSessions.slice(0, 4).map((session) => (
                  <button
                    type="button"
                    className="pending-cart-summary"
                    key={session.fecha}
                    onClick={() => showPendingCart(session)}
                  >
                    <div>
                      <strong>Sesion del {displayDate(session.fecha)}</strong>
                      <span>
                        {session.items.length} producto{session.items.length === 1 ? "" : "s"} - Total {money(sessionTotal(session))}
                      </span>
                    </div>
                    <em>Ver productos</em>
                  </button>
                ))}
              </>
            ) : (
              <div className="user-garage-empty compact">
                <h4>No tienes productos pendientes</h4>
                <p>Los productos que agregues al carrito se guardaran por fecha aunque cierres sesion.</p>
              </div>
            )}
          </div>
        </section>

        <section className="user-garage-card">
          <div className="user-garage-card-head">
            <span>Productos comprados</span>
            <button type="button" onClick={() => goToView("catalogo")}>Ir al catalogo</button>
          </div>
          <div className="purchase-list">
            {productos.length ? productos.slice(0, 5).map((producto, index) => (
              <article key={`${producto.pedido_idpedido || "producto"}-${index}`} className="purchase-item">
                <div>
                  <strong>{producto.descripcionproductos || "Producto"}</strong>
                  <span>{producto.codigoproductos || "Sin codigo"} - Cantidad {producto.cantidad || 1}</span>
                </div>
                <b>{money(producto.valor_precio)}</b>
              </article>
            )) : (
              <div className="user-garage-empty compact">
                <h4>Sin compras guardadas</h4>
                <p>Cuando finalices compras en el catalogo apareceran aqui.</p>
              </div>
            )}
          </div>
        </section>

        <section className="user-garage-card">
          <div className="user-garage-card-head">
            <span>Facturas y pagos</span>
          </div>
          <div className="payment-list">
            {pagos.length ? pagos.slice(0, 4).map((pago, index) => (
              <article key={`${pago.id || "pago"}-${index}`} className="payment-item">
                <span>{displayDate(pago.fecha)}</span>
                <strong>{money(pago.total)}</strong>
                <em>{pago.metodo || "Metodo no registrado"}</em>
              </article>
            )) : (
              <div className="user-garage-empty compact">
                <h4>Sin pagos registrados</h4>
                <p>Aun no hay pagos asociados a tu cuenta.</p>
              </div>
            )}
          </div>
        </section>
      </div>
    </section>
  );
};

const BackButton = ({ onClick, user }) => (
  <div className="text-center mt-5">
    <button
      className="btn btn-danger px-5 py-2 fw-bold shadow hover-grow"
      onClick={onClick}
      style={{ borderRadius: '50px' }}
    >
      {user ? '<- VOLVER AL PANEL' : '<- VOLVER AL INICIO'}
    </button>
  </div>
);

function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [adminFrameKey, setAdminFrameKey] = useState(0);
  const getInitialView = () => {
    const path = window.location.pathname;
    const routes = {
      '/login': 'login',
      '/catalogo': 'catalogo',
      '/contacto': 'contacto',
      '/citas': 'citas',
      '/registro': 'registro',
    };

    return routes[path] || 'inicio';
  };

  const [view, setView] = useState(getInitialView);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [user, setUser] = useState(null);
  const [selectedProject, setSelectedProject] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [dialog, setDialog] = useState(null);
  const [toast, setToast] = useState(null);
  const [afterLoginView, setAfterLoginView] = useState(null);

  const closeDialog = () => setDialog(null);

  const showNotice = (title, message) => {
    setToast({ title, message });
    window.setTimeout(() => setToast(null), 4200);
  };

  const openConfirm = (options) => {
    setDialog({
      ...options,
      onConfirm: () => {
        setDialog(null);
        if (options.onConfirm) options.onConfirm();
      }
    });
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const email = localStorage.getItem("email");
    const nombre = localStorage.getItem("nombre");

    if (token && role && email) {
      const normalizedRole = role.toLowerCase();
      setUser({ 
        email, 
        role: normalizedRole,
        nombre
      });

      const initialView = getInitialView();
      if (initialView !== 'inicio') {
        setView(initialView);
      } else if (normalizedRole === 'admin') {
        window.history.replaceState(null, '', '/');
        setAdminFrameKey((key) => key + 1);
        setView('admin-dashboard');
      } else if (normalizedRole === 'usuario' || normalizedRole === 'cliente') {
        setView('user-dashboard');
      }
    }
  }, []);

  useEffect(() => {
    if (!user) {
      if (view === 'admin-dashboard' || view === 'user-dashboard') {
        setView('login');
      }
      return;
    }

    if (view === 'admin-dashboard' && user.role !== 'admin') {
      setView('login');
    }
    
    if (view === 'user-dashboard' && user.role !== 'usuario' && user.role !== 'cliente') {
      setView('login');
    }
  }, [view, user]);

  useEffect(() => {
    document.body.style.overflow = 'auto';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [view]);

  useEffect(() => {
    const handlePopState = (e) => {
      if (!e.state || !e.state.section) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        window.history.replaceState(null, '', '/');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    if (view !== 'inicio') return;
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % heroSlides.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [view]);

  useEffect(() => {
    const closeMenuOnDesktop = () => {
      if (window.innerWidth >= 992) {
        setMenuOpen(false);
      }
    };

    const closeMenuWithEscape = (event) => {
      if (event.key === 'Escape') {
        setMenuOpen(false);
      }
    };

    window.addEventListener('resize', closeMenuOnDesktop);
    window.addEventListener('keydown', closeMenuWithEscape);

    return () => {
      window.removeEventListener('resize', closeMenuOnDesktop);
      window.removeEventListener('keydown', closeMenuWithEscape);
    };
  }, []);

  const goToInicio = () => {
    setMenuOpen(false);
    if (user) {
      setView(user.role === 'admin' ? 'admin-dashboard' : 'user-dashboard');
    } else {
      setView('inicio');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      window.history.replaceState(null, '', '/');
    }
  };

  const handleLoginSuccess = (userData) => {
    const normalizedUser = {
      ...userData,
      role: userData.role ? userData.role.toLowerCase() : 'usuario'
    };
    const displayName = getDisplayName(normalizedUser);

    setUser(normalizedUser);
    if (normalizedUser.role === 'admin') {
      window.history.replaceState(null, '', '/');
      setAdminFrameKey((key) => key + 1);
      setView('admin-dashboard');
    } else {
      setView(afterLoginView || 'user-dashboard');
    }
    setAfterLoginView(null);

    setDialog({
      kicker: "Acceso confirmado",
      title: "Bienvenidos a Disol Motors Injections",
      message: `Hola ${displayName}, bienvenido a Disol Motors Injections. Tu sesion fue iniciada correctamente.`,
      confirmText: "Entrar al sistema",
      details: [
        { label: "Usuario", value: displayName },
        { label: "Rol", value: normalizedUser.role === "admin" ? "Administrador" : "Usuario" }
      ],
      onConfirm: () => {
        setDialog(null);
        showNotice("Sesion iniciada", `Hola ${displayName}, ya puedes continuar en el sistema.`);
      }
    });
  };

  const handleLogout = () => {
    openConfirm({
      kicker: "Cerrar sesion",
      title: "Confirmar salida",
      message: "Vas a cerrar tu sesion actual en Disol Motors Injections.",
      confirmText: "Cerrar sesion",
      cancelText: "Cancelar",
      onConfirm: () => {
        localStorage.removeItem("token");
        localStorage.removeItem("role");
        localStorage.removeItem("email");
        localStorage.removeItem("nombre");
        localStorage.removeItem("dmiSessionStartedAt");
        setUser(null);
        setView('inicio');
        showNotice("Sesion cerrada", "Has salido del sistema correctamente.");
      }
    });
  };

  return (
    <div className="bg-black text-white min-vh-100 d-flex flex-column">

      {/* NAVBAR */}
      <nav className="navbar navbar-expand-lg navbar-dark bg-black sticky-top border-bottom border-danger py-3 dmi-navbar">
        <div className="container dmi-navbar-container">
          <button className="navbar-brand bg-transparent border-0 p-0 dmi-navbar-brand" onClick={goToInicio} aria-label="Ir al inicio">
            <img
              src="/assets/images/logoempresaXD.png"
              alt="DMI Logo"
              className="img-fluid dmi-navbar-logo"
            />
          </button>

          <button
            className="navbar-toggler border-0 dmi-navbar-toggler"
            type="button"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-controls="dmiMainMenu"
            aria-expanded={menuOpen}
            aria-label={menuOpen ? "Cerrar menu" : "Abrir menu"}
          >
            <span className="navbar-toggler-icon"></span>
          </button>

          <div id="dmiMainMenu" className={`collapse navbar-collapse dmi-navbar-collapse ${menuOpen ? 'show' : ''}`}>
            <ul className="navbar-nav ms-auto align-items-center gap-3 dmi-navbar-nav">

              {[
                { text: 'INICIO', viewName: 'inicio' },
                { text: 'CATALOGO', viewName: 'catalogo' },
                { text: 'CITAS', viewName: 'citas' },
                { text: 'CONTACTO', viewName: 'contacto' },
              ].map(({ text, viewName }) => (
                <li className="nav-item" key={text}>
                  <button
                    className={`nav-link fw-bold p-2 nav-hover-red bg-transparent border-0 dmi-nav-link ${view === viewName ? 'active' : ''}`}
                    onClick={() => {
                      if (viewName === 'citas' && !user) {
                        setDialog({
                          kicker: "Acceso requerido",
                          title: "Inicia sesion para agendar",
                          message: "Para proteger tus datos y guardar la cita correctamente, primero debes iniciar sesion.",
                          confirmText: "Ir al login",
                          cancelText: "Cancelar",
                          onConfirm: () => {
                            setDialog(null);
                            setAfterLoginView('citas');
                            setView('login');
                          }
                        });
                        setMenuOpen(false);
                        return;
                      }
                      setView(viewName);
                      if (viewName === 'inicio') {
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                        window.history.replaceState(null, '', '/');
                      }
                      setMenuOpen(false);
                    }}
                  >
                    {text}
                  </button>
                </li>
              ))}

              {user && user.role === 'admin' && (
                <li className="nav-item">
                  <button
                    className={`nav-link text-danger fw-black p-2 bg-transparent border-0 dmi-nav-link ${view === 'admin-dashboard' ? 'active' : ''}`}
                    onClick={() => {
                      window.history.replaceState(null, '', '/');
                      setAdminFrameKey((key) => key + 1);
                      setView('admin-dashboard');
                      setMenuOpen(false);
                    }}
                  >
                    PANEL ADMIN
                  </button>
                </li>
              )}
              
              <li className="nav-item">
                <button
                  className={`btn btn-danger px-4 rounded-0 fw-bold shadow-sm dmi-nav-cta ${view === 'user-dashboard' ? 'active' : ''}`}
                  onClick={() => {
                    if (!user) {
                      setView('login');
                    } else if (user.role === 'admin') {
                      window.history.replaceState(null, '', '/');
                      setAdminFrameKey((key) => key + 1);
                      setView('admin-dashboard');
                    } else {
                      setView('user-dashboard');
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }
                    setMenuOpen(false);
                  }}
                >
                  MI CUENTA
                </button>
              </li>

              <li className="nav-item">
                {user ? (
                  <button
                    className="btn btn-outline-light px-3 rounded-0 fw-bold btn-sm dmi-nav-session"
                    onClick={() => {
                      setMenuOpen(false);
                      handleLogout();
                    }}
                  >
                    CERRAR SESION
                  </button>



                ) : (
                  <button
                    className="btn btn-outline-danger px-3 rounded-0 fw-bold btn-sm dmi-nav-session"
                    onClick={() => {
                      setView('login');
                      setMenuOpen(false);
                    }}
                  >
                    LOGIN
                  </button>
                )}
              </li>
            </ul>
          </div>
        </div>
      </nav>

      {/* CONTENEDOR PRINCIPAL */}
      <main className="flex-grow-1">
        {view === 'admin-dashboard' && (
          <section className="admin-full-width" style={{ width: '100%', minHeight: 'calc(100vh - 84px)' }}>
            <DashboardAdmin key={adminFrameKey} onLogout={handleLogout} />
          </section>
        )}

        {view !== 'inicio' && (
          view !== 'admin-dashboard' && (
          <section className="container py-5 dmi-view-section">
            <div className="row justify-content-center">
              <div className="col-12 col-xl-10 animate-slide-in dmi-view-column">
                <div className="card bg-dark text-white border-danger border-opacity-50 shadow-lg p-4 p-md-5 dmi-view-card">

                  {view === 'citas' && (
                    <AgendarCita
                      onNeedLogin={() => {
                        setAfterLoginView('citas');
                        setView('login');
                      }}
                      onNeedVehicle={() => setView('registro')}
                      onGoGarage={() => setView('user-dashboard')}
                    />
                  )}
                  {view === 'registro' && <RegistroVehiculo onComplete={() => setView('user-dashboard')} />}
                  {view === 'catalogo' && (
                    <Catalogo
                      onNeedLogin={() => {
                        setAfterLoginView('catalogo');
                        setView('login');
                      }}
                    />
                  )}
                  {view === 'contacto' && <Contacto />}
                  
                  {/* ASIGNACION DE VISTAS DE AUTENTICACION */}
                  {view === 'login' && (
                    <LoginView 
                      onLoginSuccess={handleLoginSuccess} 
                      onSwitchToRegister={() => setView('registro-usuario')} 
                    />
                  )}
                  {view === 'registro-usuario' && (
                    <RegistroUsuarioView onRegisterSuccess={() => setView('login')} />
                  )}

                  {view === 'user-dashboard' && (
                   <MiCuenta
                        onAddVehicle={() => setView('registro')}
                          onScheduleAppointment={() => setView('citas')}
                     />
                  )}

                  <BackButton onClick={goToInicio} user={user}/>
                </div>
              </div>
            </div>
          </section>
          )
        )}

        {view === 'inicio' && (
          <>
            {/* HERO */}
            <header className="hero-viewport">
              <div
                className="hero-background"
                style={{ backgroundImage: `url(${heroSlides[currentSlide]})` }}
              ></div>
              <div className="hero-overlay"></div>
              <div className="container position-relative z-index-2 text-center animate-fade-up">
                <h1 className="hero-title">
                  DISOL <span className="text-danger">MOTORS</span>
                </h1>
                <p className="hero-subtitle mb-5">
                  Mecanica de Precision - Inyeccion Electronica - Performance
                </p>
                <div className="cta-wrapper">
                  <button
                    className="btn-racing px-5 py-3"
                    onClick={() => {
                      window.history.pushState({ section: 'galeria' }, '', '#galeria');
                      document.getElementById('galeria').scrollIntoView({ behavior: 'smooth' });
                    }}
                  >
                    EXPLORAR GALERIA
                  </button>
                </div>
              </div>

              <div className="slide-progress">
                {heroSlides.map((_, i) => (
                  <div
                    key={i}
                    className={`progress-bar-item ${i === currentSlide ? 'active' : ''}`}
                    onClick={() => setCurrentSlide(i)}
                  ></div>
                ))}
              </div>
            </header>

            {/* GALERIA */}
            <section id="galeria" className="py-5 bg-black">
              <div className="container py-4">
                <h2 className="text-center mb-5 fw-black text-uppercase">
                  Proyectos <span className="text-danger">Elite</span>
                </h2>

                <div 
                  className="pe-2 custom-gallery-scroll" 
                  style={{ maxHeight: '460px', overflowY: 'auto', overflowX: 'hidden' }}
                >
                  <div className="row g-3">
                    {[
                      { 
                        imagenes: ['/assets/images/camaroamarillo.jpg', '/assets/images/camaro verde.jpg', '/assets/images/camaromodificado.jpg'], 
                        titulo: 'Chevrolet Camaro 2018', 
                        descripcion: 'Optimizacion de software y diagnostico computarizado para flotas empresariales, se hizo mantenimiento preventivo y cambio de color.' 
                      },
                      { 
                        imagenes: ['/assets/images/porche.jpg', '/assets/images/lamborghini.jpg', '/assets/images/lamborghini.jpg'], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibracion avanzada del sistema de inyeccion electronica y pruebas de presion en tiempo real.' 
                      },
                      { 
                        imagenes: ['/assets/images/lamborghini.jpg', '/assets/images/porche.jpg', '/assets/images/lamborghini.jpg'], 
                        titulo: 'Lamborghini Aventador', 
                        descripcion: 'Mantenimiento de alta precision en el sistema de admision y mapeo de ECU para rendimiento extremo.' 
                      },
                      { 
                        imagenes: ['/assets/images/lamborghini.jpg', '/assets/images/lamborghini.jpg', '/assets/images/lamborghini.jpg'], 
                        titulo: 'Diagnostico General', 
                        descripcion: 'Escaneo completo de modulos electronicos mediante tecnologia OBD-II de ultima generacion.' 
                      },
                      { 
                        imagenes: ['/assets/images/lamborghini.jpg', '/assets/images/lamborghini.jpg', '/assets/images/lamborghini.jpg'], 
                        titulo: 'Proyecto Mel', 
                        descripcion: 'Ajustes personalizados de alto rendimiento y restauracion de componentes criticos del motor.' 
                      },
                      { 
                        imagenes: ['/assets/images/lamborghini.jpg', '/assets/images/lamborghini.jpg', '/assets/images/lamborghini.jpg'], 
                        titulo: 'Unidad de Potencia', 
                        descripcion: 'Modificacion y ensamble de sistemas de inyeccion a medida para competencia.' 
                      }
                    ].map((proyecto, index) => (
                      <div key={index} className="col-6 col-md-4">
                        <div 
                          className="gallery-card border-danger position-relative overflow-hidden shadow" 
                          style={{ aspectRatio: '16/9', cursor: 'pointer' }}
                          onClick={() => {
                            setSelectedProject(proyecto);
                            setShowModal(true);
                          }}
                        >
                          <img 
                            src={proyecto.imagenes[0]} 
                            alt={proyecto.titulo} 
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          />
                          <div className="gallery-hover-info">
                            <small>VER DETALLES</small>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* MODAL CON CARRUSEL DE IMAGENES */}
              {showModal && selectedProject && (
                <div className="modal fade show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 1050 }}>
                  <div className="modal-dialog modal-dialog-centered">
                    <div className="modal-content bg-dark text-white border border-danger rounded-0 shadow-lg">
                      <div className="modal-header border-bottom border-danger border-opacity-50">
                        <h5 className="modal-title fw-black text-uppercase">
                          Detalles del <span className="text-danger">Proyecto</span>
                        </h5>
                        <button type="button" className="btn-close btn-close-white" onClick={() => setShowModal(false)}></button>
                      </div>
                      <div className="modal-body p-4">
                        <div id="carouselProjectDetails" className="carousel slide mb-3 border border-secondary" data-bs-ride="carousel" style={{ aspectRatio: '16/9' }}>
                          <div className="carousel-inner h-100">
                            {selectedProject.imagenes.map((imgUrl, idx) => (
                              <div key={idx} className={`carousel-item h-100 ${idx === 0 ? 'active' : ''}`}>
                                <img src={imgUrl} className="d-block w-100 h-100" alt={`Slide ${idx + 1}`} style={{ objectFit: 'cover' }} />
                              </div>
                            ))}
                          </div>
                          <button className="carousel-control-prev" type="button" data-bs-target="#carouselProjectDetails" data-bs-slide="prev">
                            <span className="carousel-control-prev-icon" aria-hidden="true"></span>
                          </button>
                          <button className="carousel-control-next" type="button" data-bs-target="#carouselProjectDetails" data-bs-slide="next">
                            <span className="carousel-control-next-icon" aria-hidden="true"></span>
                          </button>
                        </div>
                        <h4 className="fw-bold text-uppercase tracking-wider mb-2 text-danger">{selectedProject.titulo}</h4>
                        <p className="text-muted small mb-0">{selectedProject.descripcion}</p>
                      </div>
                      <div className="modal-footer border-top border-danger border-opacity-25">
                        <button type="button" className="btn btn-danger rounded-0 fw-bold px-4" onClick={() => setShowModal(false)}>
                          CERRAR
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </section>
          </>
        )}
      </main>

      <footer className="bg-black py-4 border-top border-danger border-opacity-25 text-center">
        <p className="small text-muted mb-0 tracking-widest">
          (c) 2026 - DMI - HIGH PERFORMANCE SERVICE
        </p>
      </footer>

      <DmiDialog dialog={dialog} onClose={closeDialog} />
      <DmiToast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}

export default App;
