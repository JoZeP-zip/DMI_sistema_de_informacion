import React, { useEffect, useState } from 'react';
import { AuthService } from './services/api';
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

const isMechanicRole = (role) => {
  const normalizedRole = String(role || "").toLowerCase();
  return normalizedRole === "mecanico" || normalizedRole === "mecanico_taller";
};

const goToMechanicPanel = () => {
  window.location.href = `${getApiBaseUrl()}/mecanico`;
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
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const LoginView = ({ onLoginSuccess, onSwitchToRegister, openConfirm }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const showLoginIssue = ({ title, message }) => {
    openConfirm({
      kicker: "Acceso requerido",
      title,
      message,
      confirmText: "Entendido"
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password) {
      showLoginIssue({
        title: "Completa tus datos",
        message: "Completa tu correo y contrasena."
      });
      return;
    }

    if (!EMAIL_REGEX.test(trimmedEmail)) {
      showLoginIssue({
        title: "Correo invalido",
        message: "Ingresa un correo electronico valido, por ejemplo nombre@dominio.com."
      });
      return;
    }

    try {
      const data = await AuthService.login(trimmedEmail, password);

      onLoginSuccess({
        email: data.email,
        role: data.role
      });

    } catch (err) {
      const rawMessage = String(err?.message || "").toLowerCase();

      const looksLikeConnectionError =
        /failed to fetch|networkerror|network error|conexion|conexion|timeout/.test(rawMessage);

      const looksLikeWrongPassword =
        /contrasena|contrasena|password|clave incorrecta/.test(rawMessage);

      const looksLikeUnknownEmail =
        /usuario no existe|correo no registrado|no encontr|not found|no existe|no registrad/.test(rawMessage);

      // El backend en /login-react puede responder con un mensaje generico
      // (p.ej. "Credenciales invalidas" o "Error 401") que no distingue si
      // fallo el correo o la contrasena. En ese caso mostramos un mensaje
      // combinado en vez de adivinar cual de los dos esta mal.
      const looksLikeGenericInvalidCredentials =
        /error 401|credenciales|invalid|no autorizado|unauthorized/.test(rawMessage);

      if (looksLikeConnectionError) {
        showLoginIssue({
          title: "No se pudo conectar",
          message: "Hubo un problema de conexion con el servidor. Intenta nuevamente en unos segundos."
        });
      } else if (looksLikeUnknownEmail) {
        showLoginIssue({
          title: "Correo no registrado",
          message: "No encontramos una cuenta asociada a ese correo electronico."
        });
      } else if (looksLikeWrongPassword) {
        showLoginIssue({
          title: "Contrasena incorrecta",
          message: "La contrasena ingresada no es correcta. Intentalo de nuevo."
        });
      } else if (looksLikeGenericInvalidCredentials) {
        showLoginIssue({
          title: "Correo o contrasena incorrectos",
          message: "Verifica que tu correo y tu contrasena esten bien escritos e intenta de nuevo."
        });
      } else {
        showLoginIssue({
          title: "No se pudo iniciar sesion",
          message: err?.message || "Verifica tu correo y contrasena e intenta de nuevo."
        });
      }
    }
  };

  return (
    <div className="mx-auto" style={{ maxWidth: '400px' }}>
      <h3 className="text-center text-uppercase fw-black mb-4">
        Control de <span className="text-danger">Acceso</span>
      </h3>
      <form onSubmit={handleSubmit} noValidate>
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
const RegistroUsuarioView = ({ onRegisterSuccess, openConfirm }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nombre, setNombre] = useState('');
  const [apellidos, setApellidos] = useState('');
  const [documento, setDocumento] = useState('');
  const [tipodedocumento, setTipodedocumento] = useState('CC');
  const [telefono, setTelefono] = useState('');
  const [usuarionombre, setUsuarionombre] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();

    const requiredFields = { nombre, apellidos, usuarionombre, documento, telefono, email, password };
    const missingField = Object.values(requiredFields).some((value) => !String(value).trim());

    if (missingField) {
      openConfirm({
        kicker: "Acceso requerido",
        title: "Completa tus datos",
        message: "Completa todos los campos del formulario para registrarte.",
        confirmText: "Entendido"
      });
      return;
    }

    if (!EMAIL_REGEX.test(email.trim())) {
      openConfirm({
        kicker: "Acceso requerido",
        title: "Correo invalido",
        message: "Ingresa un correo electronico valido, por ejemplo nombre@dominio.com.",
        confirmText: "Entendido"
      });
      return;
    }

    try {
      const response = await fetch(getApiBaseUrl() + '/registro-react', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          nombre,
          apellidos,
          documento: documento ? Number(documento) : undefined,
          tipodedocumento,
          telefono,
          usuarionombre,
          email,
          password,
          role: "usuario"
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        openConfirm({
          kicker: "Registro de cuenta",
          title: "No se pudo crear la cuenta",
          message: data.error || data.message || data.detail || 'Error al registrar el usuario.',
          confirmText: "Entendido"
        });
      } else {
        openConfirm({
          kicker: "Cuenta creada",
          title: "Registro exitoso",
          message: "Tu cuenta fue creada correctamente. Ahora puedes iniciar sesion.",
          confirmText: "Ir al login",
          onConfirm: onRegisterSuccess
        });
      }
    } catch (err) {
      openConfirm({
        kicker: "Registro de cuenta",
        title: "No se pudo conectar",
        message: err.message || 'Error de conexion con el servidor backend.',
        confirmText: "Entendido"
      });
    }
  };

  return (
    <div className="mx-auto" style={{ maxWidth: '400px' }}>
      <h3 className="text-center text-uppercase fw-black mb-4">
        Crear <span className="text-danger">Cuenta</span>
      </h3>

      <form onSubmit={handleRegister} noValidate>
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
          <label className="form-label text-white small fw-bold">APELLIDOS</label>
          <input 
            type="text" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={apellidos}
            onChange={(e) => setApellidos(e.target.value)}
            required 
          />
        </div>
        <div className="mb-3">
          <label className="form-label text-white small fw-bold">NOMBRE DE USUARIO</label>
          <input 
            type="text" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={usuarionombre}
            onChange={(e) => setUsuarionombre(e.target.value)}
            required 
          />
        </div>
        <div className="mb-3">
          <label className="form-label text-white small fw-bold">TIPO DE DOCUMENTO</label>
          <select
            className="form-select bg-black text-white border-secondary rounded-0 focus-red"
            value={tipodedocumento}
            onChange={(e) => setTipodedocumento(e.target.value)}
            required
          >
            <option value="CC">CC - Cedula de Ciudadania</option>
            <option value="CE">CE - Cedula de Extranjeria</option>
            <option value="TI">TI - Tarjeta de Identidad</option>
            <option value="RC">RC - Registro Civil</option>
            <option value="NIT">NIT - Numero de Identificacion Tributaria</option>
          </select>
        </div>
        <div className="mb-3">
          <label className="form-label text-white small fw-bold">DOCUMENTO</label>
          <input 
            type="text" 
            inputMode="numeric"
            pattern="[0-9]*"
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={documento}
            onChange={(e) => setDocumento(e.target.value.replace(/\D/g, ''))}
            required 
          />
        </div>
        <div className="mb-3">
          <label className="form-label text-white small fw-bold">TELEFONO</label>
          <input 
            type="tel" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={telefono}
            onChange={(e) => setTelefono(e.target.value)}
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

const heroSlides = [
  './assets/images/like.jpg',
  './assets/images/akira.jpg',
  './assets/images/fotoautos.jpg',
];

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
    const handleDmiMessage = (event) => {
      const detail = event.detail || {};
      setDialog({
        kicker: detail.kicker || "Mensaje del sistema",
        title: detail.title || "Aviso",
        message: detail.message || "",
        confirmText: detail.confirmText || "Entendido",
        cancelText: detail.cancelText || null,
        details: detail.details || null,
        productItems: detail.productItems || null,
        onConfirm: () => {
          setDialog(null);
          if (typeof detail.onConfirm === "function") detail.onConfirm();
        }
      });
    };

    window.addEventListener("dmi:message", handleDmiMessage);
    return () => window.removeEventListener("dmi:message", handleDmiMessage);
  }, []);

  useEffect(() => {
    if (window.location.pathname === '/login') {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      localStorage.removeItem("email");
      localStorage.removeItem("nombre");
      localStorage.removeItem("dmiSessionStartedAt");
      setUser(null);
      setView('login');
      return;
    }

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
      } else if (isMechanicRole(normalizedRole)) {
        setView('inicio');
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
      if (isMechanicRole(user.role)) {
        goToMechanicPanel();
        return;
      }
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
    if (user && user.role === 'admin') {
      setView('admin-dashboard');
      return;
    }
    setView('inicio');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    window.history.replaceState(null, '', '/');
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
    } else if (isMechanicRole(normalizedUser.role)) {
      setView(afterLoginView || 'inicio');
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
        { label: "Rol", value: normalizedUser.role === "admin" ? "Administrador" : isMechanicRole(normalizedUser.role) ? "Mecanico" : "Usuario" }
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
                    } else if (isMechanicRole(user.role)) {
                      setMenuOpen(false);
                      goToMechanicPanel();
                      return;
                    } else {
                      setView('user-dashboard');
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }
                    setMenuOpen(false);
                  }}
                >
                  {user && isMechanicRole(user.role) ? 'MECANICO' : 'MI CUENTA'}
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
                      openConfirm={openConfirm}
                    />
                  )}
                  {view === 'registro-usuario' && (
                    <RegistroUsuarioView onRegisterSuccess={() => setView('login')} openConfirm={openConfirm} />
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


