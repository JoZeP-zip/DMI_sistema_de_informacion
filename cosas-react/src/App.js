import React, { useEffect, useRef, useState } from 'react';
import { AuthService, NotificacionesService } from './services/api';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min';
import './styles/App.css';
import NightSky from './components/NightSky';

import RegistroVehiculo from './js/RegistrarUnidad.js';
import Contacto from './js/Contacto.js';
import AgendarCita from './js/AgendarCita.js';
import Catalogo from './js/Catalogo.js';
import DashboardAdmin from './js/DashboardAdmin.js';
import MiCuenta from './js/MiCuenta';
import CloudinaryGallery from './components/CloudinaryGallery';
import CloudinaryCarousel from './components/CloudinaryCarousel';
import AdminGalleryManager from './components/AdminGalleryManager';
import { cld } from './utils/cloudinary';


const getApiBaseUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

  const { protocol, hostname } = window.location;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  const isLocalNetworkHost = /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[0-1])\.)/.test(hostname);
  if (isLocalNetworkHost) {
    return `http://${hostname}:8000`;
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
  const apiBase = getApiBaseUrl().replace(/\/$/, "");
  const frontendOrigin = window.location.origin;
  const separator = apiBase.includes("?") ? "&" : "?";

  // Enviamos el origen real del frontend al backend para que el
  // mecánico pueda volver al MISMO frontend después de cerrar sesión.
  window.location.href =
    `${apiBase}/mecanico${separator}frontend=${encodeURIComponent(frontendOrigin)}`;
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
                    // 👉 3) Reemplaza 'dmi-productos/placeholder' por el public ID de tu imagen
                    //    de repuesto/producto genérica que quieras usar como fallback
                    src={item.image || item.imagen || cld('dmi-productos/placeholder', 'f_auto,q_auto,w_300')}
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

// Regla de seguridad para todas las contrasenas del sistema.
// Debe tener entre 8 y 20 caracteres y al menos un simbolo.
const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_MAX_LENGTH = 20;
const PASSWORD_SYMBOL_REGEX = /[^A-Za-z0-9\s]/;

const validarPassword = (password) => {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `La contrasena debe tener minimo ${PASSWORD_MIN_LENGTH} caracteres.`;
  }
  if (password.length > PASSWORD_MAX_LENGTH) {
    return `La contrasena debe tener maximo ${PASSWORD_MAX_LENGTH} caracteres.`;
  }
  if (!PASSWORD_SYMBOL_REGEX.test(password)) {
    return 'La contrasena debe contener minimo un simbolo, por ejemplo: @, #, $, ! o %.';
  }
  return '';
};

const LoginView = ({ onLoginSuccess, onSwitchToRegister, onForgotPassword, openConfirm }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

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
        message: "Completa tu correo y contraseña."
      });
      return;
    }

    const passwordError = validarPassword(password);
    if (passwordError) {
      showLoginIssue({
        title: "Contrasena no valida",
        message: passwordError
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
        /contraseña|contraseña|password|clave incorrecta/.test(rawMessage);

      const looksLikeUnknownEmail =
        /usuario no existe|correo no registrado|no encontr|not found|no existe|no registrad/.test(rawMessage);
 
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
          title: "contraseña incorrecta",
          message: "La contraseña ingresada no es correcta. Intentalo de nuevo."
        });
      } else if (looksLikeGenericInvalidCredentials) {
        showLoginIssue({
          title: "Correo o contraseña incorrectos",
          message: "Verifica que tu correo y tu contraseña esten bien escritos e intenta de nuevo."
        });
      } else {
        showLoginIssue({
          title: "No se pudo iniciar sesion",
          message: err?.message || "Verifica tu correo y contraseña e intenta de nuevo."
        });
      }
    }
  };

  return (
    <div className="mx-auto auth-shell auth-login-shell" style={{ maxWidth: '480px' }}>
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
          <label className="form-label text-white small fw-bold">contraseña</label>
          <div className="position-relative">
            <input 
              type={showPassword ? "text" : "password"} 
              className="form-control bg-black text-white border-secondary rounded-0 focus-red pe-5"
              value={password}
              onChange={(e) => setPassword(e.target.value.slice(0, PASSWORD_MAX_LENGTH))}
              maxLength={PASSWORD_MAX_LENGTH}
              required 
            />
            <button
              type="button"
              className="btn btn-sm position-absolute top-50 end-0 translate-middle-y text-danger fw-bold bg-transparent border-0"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Ocultar contraseña" : "Ver contraseña"}
            >
              {showPassword ? "Ocultar" : "Ver"}
            </button>
          </div>
          <small className="text-muted d-block mt-2">8-20 caracteres y minimo 1 simbolo.</small>
        </div>
        <button type="submit" className="btn btn-danger w-100 rounded-0 fw-bold py-2 tracking-widest mb-3">
          INGRESAR
        </button>
        <p className="text-center small mb-3">
          <button
            type="button"
            className="btn btn-link text-danger p-0 small fw-bold text-decoration-underline"
            onClick={() => {
              const trimmedEmail = email.trim();
              if (!EMAIL_REGEX.test(trimmedEmail)) {
                showLoginIssue({
                  title: "Ingresa tu correo",
                  message: "Escribe el correo con el que te registraste antes de solicitar la recuperacion."
                });
                return;
              }
              onForgotPassword(trimmedEmail);
            }}
          >
            Olvide mi contrasena
          </button>
        </p>
        <p className="text-center small text-muted">
          No tienes una cuenta? <span className="text-danger cursor-pointer fw-bold text-decoration-underline" style={{cursor: 'pointer'}} onClick={onSwitchToRegister}>Registrate aqui</span>
        </p>
      </form>
    </div>
  );
};

const RegistroUsuarioView = ({ onRegisterSuccess, onVerificationNeeded, openConfirm }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [nombre, setNombre] = useState('');
  const [apellidos, setApellidos] = useState('');
  const [documento, setDocumento] = useState('');
  const [tipodedocumento, setTipodedocumento] = useState('CC');
  const [telefono, setTelefono] = useState('');
  const [usuarionombre, setUsuarionombre] = useState('');
  const [fechadenacimiento, setFechadenacimiento] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();

    const requiredFields = { nombre, apellidos, usuarionombre, documento, telefono, fechadenacimiento, email, password, confirmPassword };
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

    const passwordError = validarPassword(password);
    if (passwordError) {
      openConfirm({
        kicker: "Seguridad de la cuenta",
        title: "Contrasena no valida",
        message: passwordError,
        confirmText: "Entendido"
      });
      return;
    }

    if (password !== confirmPassword) {
      openConfirm({
        kicker: "Registro de cuenta",
        title: "Las contraseñas no coinciden",
        message: "La contraseña y la confirmacion deben ser iguales para crear tu cuenta.",
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
          fechadenacimiento,
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
          kicker: "Confirma tu correo",
          title: "Te enviamos un codigo",
          message: "Revisa el correo con el que te registraste e ingresa el codigo de 8 digitos para crear tu cuenta.",
          confirmText: "Ingresar codigo",
          onConfirm: () => onVerificationNeeded(email.trim())
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
    <div className="mx-auto auth-shell auth-register-shell" style={{ maxWidth: '720px' }}>
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
        <div className="mb-3 auth-date-field">
          <label className="form-label text-white small fw-bold">FECHA DE NACIMIENTO</label>
          <input
            type="date"
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={fechadenacimiento}
            onChange={(e) => setFechadenacimiento(e.target.value)}
            max={new Date().toISOString().slice(0, 10)}
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
        <div className="mb-3">
          <label className="form-label text-white small fw-bold">contraseña</label>
          <div className="position-relative">
            <input 
              type={showPassword ? "text" : "password"} 
              className="form-control bg-black text-white border-secondary rounded-0 focus-red pe-5"
              value={password}
              onChange={(e) => setPassword(e.target.value.slice(0, PASSWORD_MAX_LENGTH))}
              maxLength={PASSWORD_MAX_LENGTH}
              required 
            />
            <button
              type="button"
              className="btn btn-sm position-absolute top-50 end-0 translate-middle-y text-danger fw-bold bg-transparent border-0"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Ocultar contraseña" : "Ver contraseña"}
            >
              {showPassword ? "Ocultar" : "Ver"}
            </button>
          </div>
          <small className="text-muted d-block mt-2">8-20 caracteres y minimo 1 simbolo.</small>
        </div>
        <div className="mb-4">
          <label className="form-label text-white small fw-bold">CONFIRMAR contraseña</label>
          <div className="position-relative">
            <input 
              type={showConfirmPassword ? "text" : "password"} 
              className="form-control bg-black text-white border-secondary rounded-0 focus-red pe-5"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value.slice(0, PASSWORD_MAX_LENGTH))}
              maxLength={PASSWORD_MAX_LENGTH}
              required 
            />
            <button
              type="button"
              className="btn btn-sm position-absolute top-50 end-0 translate-middle-y text-danger fw-bold bg-transparent border-0"
              onClick={() => setShowConfirmPassword((value) => !value)}
              aria-label={showConfirmPassword ? "Ocultar confirmacion" : "Ver confirmacion"}
            >
              {showConfirmPassword ? "Ocultar" : "Ver"}
            </button>
          </div>
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

const VerificarRegistroView = ({ email, onVerified, onBackToRegister, openConfirm }) => {
  const PIN_LENGTH = 8;
  const [pinDigits, setPinDigits] = useState(() => Array(PIN_LENGTH).fill(''));
  const [verifying, setVerifying] = useState(false);
  const inputRefs = useRef([]);

  const pin = pinDigits.join('');

  const handlePinChange = (index, rawValue) => {
    const digits = rawValue.replace(/\D/g, '').slice(0, PIN_LENGTH - index);
    if (!digits && rawValue) return;

    setPinDigits((previous) => {
      const next = [...previous];
      if (digits) {
        digits.split('').forEach((digit, offset) => {
          next[index + offset] = digit;
        });
      } else {
        next[index] = '';
      }
      return next;
    });

    if (digits) {
      const nextIndex = Math.min(index + digits.length, PIN_LENGTH - 1);
      inputRefs.current[nextIndex]?.focus();
    }
  };

  const handleKeyDown = (index, event) => {
    if (event.key === 'Backspace' && !pinDigits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
    if (event.key === 'ArrowLeft' && index > 0) inputRefs.current[index - 1]?.focus();
    if (event.key === 'ArrowRight' && index < PIN_LENGTH - 1) inputRefs.current[index + 1]?.focus();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!/^\d{8}$/.test(pin)) {
      openConfirm({ kicker: "Confirma tu correo", title: "Codigo incompleto", message: "Ingresa los 8 digitos que recibiste por correo.", confirmText: "Entendido" });
      return;
    }
    setVerifying(true);
    try {
      await AuthService.verificarRegistro(email, pin);
      openConfirm({ kicker: "Cuenta creada", title: "Correo confirmado", message: "Tu cuenta DMI fue creada correctamente. Ya puedes iniciar sesion.", confirmText: "Ir al login", onConfirm: onVerified });
    } catch (error) {
      openConfirm({ kicker: "Confirma tu correo", title: "No se pudo confirmar", message: error.message || "El codigo no es valido o ya vencio.", confirmText: "Entendido" });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="mx-auto" style={{ maxWidth: '400px' }}>
      <div className="dmi-otp-header text-center mb-4">
        <div className="dmi-otp-icon" aria-hidden="true">✉</div>
        <h3 className="text-uppercase fw-black mb-2">Confirma tu <span className="text-danger">Correo</span></h3>
        <p className="text-white-50 small mb-1">Enviamos un código de 8 dígitos a</p>
        <p className="text-white fw-bold mb-0 text-break">{email}</p>
      </div>
      <form onSubmit={handleSubmit} noValidate>
        <div className="mb-4">
          <label className="form-label text-white small fw-bold d-block text-center mb-3">CÓDIGO DE CONFIRMACIÓN</label>
          <div className="dmi-otp-inputs" aria-label="Código de confirmación de 8 dígitos">
            {pinDigits.map((digit, index) => (
              <input
                key={index}
                ref={(element) => { inputRefs.current[index] = element; }}
                type="text"
                inputMode="numeric"
                autoComplete={index === 0 ? 'one-time-code' : 'off'}
                maxLength={index === 0 ? PIN_LENGTH : 1}
                className={`dmi-otp-input ${digit ? 'filled' : ''}`}
                value={digit}
                onChange={(event) => handlePinChange(index, event.target.value)}
                onKeyDown={(event) => handleKeyDown(index, event)}
                aria-label={`Dígito ${index + 1} de ${PIN_LENGTH}`}
              />
            ))}
          </div>
          <p className="text-center text-white-50 small mt-3 mb-0">Puedes escribir o pegar el código completo.</p>
        </div>
        <button type="submit" className="btn btn-danger w-100 rounded-0 fw-bold py-2 tracking-widest mb-3" disabled={verifying}>{verifying ? 'CONFIRMANDO...' : 'CONFIRMAR Y CREAR CUENTA'}</button>
        <p className="text-center small mb-0"><button type="button" className="btn btn-link text-danger p-0 small fw-bold text-decoration-underline" onClick={onBackToRegister}>Volver al registro</button></p>
      </form>
    </div>
  );
};

const RecuperarPasswordView = ({ email, onBackToLogin, openConfirm }) => {
  const [sending, setSending] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!EMAIL_REGEX.test(email)) {
      openConfirm({
        kicker: "Recuperacion de acceso",
        title: "Correo no disponible",
        message: "Vuelve al inicio de sesion y escribe el correo con el que te registraste.",
        confirmText: "Volver al login",
        onConfirm: onBackToLogin
      });
      return;
    }

    setSending(true);
    try {
      await AuthService.solicitarRecuperacionPassword(email);
      openConfirm({
        kicker: "Recuperacion de acceso",
        title: "Revisa tu correo",
        message: "Si este es el correo registrado en DMI, recibiras un enlace seguro para restablecer tu contrasena.",
        confirmText: "Volver al login",
        onConfirm: onBackToLogin
      });
    } catch (error) {
      openConfirm({
        kicker: "Recuperacion de acceso",
        title: "No se pudo enviar la solicitud",
        message: "Revisa tu conexion e intentalo de nuevo.",
        confirmText: "Entendido"
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto" style={{ maxWidth: '400px' }}>
      <h3 className="text-center text-uppercase fw-black mb-3">Recuperar <span className="text-danger">Acceso</span></h3>
      <p className="text-center text-white-50 small mb-2">Enviaremos un enlace seguro al correo con el que inicias sesion.</p>
      <p className="text-center text-white fw-bold mb-4">{email || 'Correo no disponible'}</p>
      <form onSubmit={handleSubmit} noValidate>
        <button type="submit" className="btn btn-danger w-100 rounded-0 fw-bold py-2 tracking-widest mb-3" disabled={sending}>
          {sending ? 'ENVIANDO...' : 'ENVIAR ENLACE'}
        </button>
        <p className="text-center small mb-0"><button type="button" className="btn btn-link text-danger p-0 small fw-bold text-decoration-underline" onClick={onBackToLogin}>Volver al login</button></p>
      </form>
    </div>
  );
};

const NuevaPasswordView = ({ onBackToLogin, openConfirm }) => {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const recoveryParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const accessToken = recoveryParams.get('access_token');
  const refreshToken = recoveryParams.get('refresh_token');

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!accessToken || !refreshToken) {
      openConfirm({ kicker: "Recuperacion de acceso", title: "Enlace no valido", message: "Solicita un nuevo enlace de recuperacion.", confirmText: "Ir a recuperacion", onConfirm: onBackToLogin });
      return;
    }
    const passwordError = validarPassword(password);
    if (passwordError) {
      openConfirm({ kicker: "Nueva contrasena", title: "Contrasena no valida", message: passwordError, confirmText: "Entendido" });
      return;
    }
    if (password !== confirmPassword) {
      openConfirm({ kicker: "Nueva contrasena", title: "Las contrasenas no coinciden", message: "Verifica la confirmacion de tu nueva contrasena.", confirmText: "Entendido" });
      return;
    }
    setSaving(true);
    try {
      await AuthService.restablecerPassword({ accessToken, refreshToken, password });
      window.history.replaceState({}, '', '/login');
      openConfirm({ kicker: "Acceso actualizado", title: "Contrasena actualizada", message: "Ya puedes iniciar sesion con tu nueva contrasena.", confirmText: "Ir al login", onConfirm: onBackToLogin });
    } catch (error) {
      openConfirm({ kicker: "Recuperacion de acceso", title: "No se pudo actualizar", message: error.message || "El enlace vencio o ya fue utilizado. Solicita uno nuevo.", confirmText: "Entendido" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto" style={{ maxWidth: '400px' }}>
      <h3 className="text-center text-uppercase fw-black mb-3">Nueva <span className="text-danger">Contrasena</span></h3>
      <p className="text-center text-white-50 small mb-4">Crea una contrasena de 8 a 20 caracteres con minimo un simbolo.</p>
      <form onSubmit={handleSubmit} noValidate>
        <div className="mb-3"><label className="form-label text-white small fw-bold">NUEVA CONTRASENA</label><input type="password" className="form-control bg-black text-white border-secondary rounded-0 focus-red" value={password} onChange={(event) => setPassword(event.target.value.slice(0, PASSWORD_MAX_LENGTH))} maxLength={PASSWORD_MAX_LENGTH} required /></div>
        <div className="mb-4"><label className="form-label text-white small fw-bold">CONFIRMAR CONTRASENA</label><input type="password" className="form-control bg-black text-white border-secondary rounded-0 focus-red" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value.slice(0, PASSWORD_MAX_LENGTH))} maxLength={PASSWORD_MAX_LENGTH} required /></div>
        <button type="submit" className="btn btn-danger w-100 rounded-0 fw-bold py-2 tracking-widest" disabled={saving}>{saving ? 'ACTUALIZANDO...' : 'ACTUALIZAR CONTRASENA'}</button>
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
  // Proyectos con Public IDs de Cloudinary
  const obtenerProyectosDefecto = () => [
    {
      titulo: 'Chevrolet Camaro 2018',
      descripcion: 'El Chevrolet Camaro es mucho más que un automóvil deportivo; es un ícono de la cultura automotriz global que combina un diseño agresivo, una aerodinámica imponente y una potencia inconfundible. A lo largo de sus generaciones, ha sido sinónimo de libertad, velocidad y carácter en la carretera..',
      imagenes: ['camaroamarillo', 'camaromodificado', 'camaro_verde'],
    },
    {
      titulo: 'Porsche 911 GT3',
      descripcion: 'El Porsche 911 GT (ya sea en sus icónicas variantes GT3, GT3 RS o el radical GT2 RS) representa la máxima expresión de la deportividad y la precisión alemana. A diferencia de otros superdeportivos, el 911 GT toma la legendaria arquitectura de motor trasero del 911 clásico y la transforma en un vehículo de competición homologado para la calle.',
      imagenes: ['porche', 'por1', 'por2', 'por3'],
    },
    {
      titulo: 'Mustang',
      descripcion: 'El Ford Mustang es el patriarca indiscutible de los muscle cars y uno de los automóviles más influyentes de la historia moderna. Desde su debut en 1964, revolucionó la industria al democratizar la potencia y el diseño deportivo, convirtiéndose en un símbolo global de libertad, rebeldía y velocidad en carretera abierta.',
      imagenes: ['mus3', 'mus1', 'mus2'],
    },
    {
      titulo: 'BMW M4 Competition',
      descripcion: 'El BMW M4 es el referente definitivo de los coupés deportivos de alto rendimiento. Nacido de la división Motorsport (M) de la marca bávara, combina la elegancia y sofisticación de un gran turismo con la agresividad, la agilidad y la tecnología visceral de un auténtico auto de competición adaptado para la calle.',
      imagenes: ['bmw3', 'bmw2', 'bmw1'],
    },
    {
      titulo: 'Audi R8 V10',
      descripcion: 'El Audi R8 es, sin duda, una de las obras maestras de la ingeniería automotriz moderna. Este superdeportivo combina la sofisticación de la marca de los cuatro aros con un rendimiento salvaje, destacando principalmente por ser uno de los pocos vehículos de su segmento que conserva un legendario motor atmosférico de alta cilindrada.',
      imagenes: ['audi3', 'audi1', 'audi2'],
    },
    {
      titulo: 'Yamaha R1',
      descripcion: 'La YamahaR1 es un icono indiscutible del motociclismo mundial y el máximo estandarte de la deportividad de la marca de los diapasones. Nacida para dominar tanto las pistas de competición como las carreteras más exigentes, la R1 ha redefinido los estándares de potencia, agilidad y tecnología en el segmento de las superbikes.',
      imagenes: ['yam3', 'yam1', 'yam2'],
    },
    {
      titulo: 'sail',
      descripcion: 'Caben 6 cuerpos y una pala',
      imagenes: ['sai3', 'sai1', 'sai2'],
    },
    {
      titulo: 'Ford Raptor',
      descripcion: 'La familia Ford Raptor (que abarca modelos emblemáticos como la F-150 Raptor, Ranger Raptor y Bronco Raptor) representa la cúspide de las camionetas de alto rendimiento off-road. Desarrollada por la división Ford Performance, esta saga fue concebida no solo para superar caminos difíciles, sino para devorar desiertos,',
      imagenes: ['rap3', 'rap1', 'rap2'],
    },
    {
      titulo: 'yamaha R6',
      descripcion: 'La Yamaha R6 es, sin discusión, una de las motocicletas más influyentes, amadas y radicales de la historia del motociclismo. Durante décadas, este modelo reinó de manera absoluta en la categoría de las 600 cc (Supersport), convirtiéndose en la escuela definitiva de pilotos y en la máquina preferida de quienes buscaban emociones al límite tanto en carretera como en circuito..',
      imagenes: ['r63', 'r61', 'r62'],
    },
    {
      titulo: 'Nissan skyline',
      descripcion: 'El Nissan Skyline es mucho más que un nombre en la historia de los autos deportivos; es una auténtica dinastía de ingeniería que evolucionó desde un sedán familiar hasta convertirse en el terror de los superdeportivos europeos en las pistas de carreras, ganándose el legendario apodo de "Godzilla".',
      imagenes: ['pol3', 'pol1', 'pol2'],
    },
    {
      titulo: 'Benda Napoleon 250',
      descripcion: 'La Benda Napoleon (destacando especialmente en versiones como la Napoleon Bob 500) es una motocicleta que ha revolucionado el segmento de las custom medianas. Lejos de ser una cruiser tradicional, la marca asiática ha apostado por un diseño vanguardista que fusiona la estética minimalista y ruda de las clásicas bobber con toques futuristas y mecánicas muy cuidadas.',
      imagenes: ['nap3', 'nap1', 'nap2'],
    },
    {
      titulo: 'Mazda 3 Skyactiv',
      descripcion: 'El Mazda 3 Skyactiv representa un punto de inflexión en el segmento de los compactos. Lejos de conformarse con ser un vehículo utilitario más, Mazda rediseñó por completo la experiencia de poseer y conducir un auto accesible mediante una filosofía que combina el diseño emocional, la ingeniería de combustión avanzada y un tacto de manejo con aspiraciones premium.',
      imagenes: ['maz3', 'maz1', 'maz2'],
    },
    {
      titulo: 'Herbie (El Volkswagen Escarabajo): El Carro con Alma',
      descripcion: 'Herbie, el inolvidable Volkswagen Sedán (Escarabajo) blanco de 1963 con el número 53 pintado en las puertas, el cofre y la cajera, junto con las franjas azul, blanca y roja, es mucho más que un personaje de cine: es uno de los automóviles más carismáticos y queridos de la cultura pop global.',
      imagenes: ['her3', 'her1', 'her2'],
    },
    {
      titulo: 'Ducati Panigale V4',
      descripcion: 'La Ducati Panigale V4 es, sin lugar a dudas, la motocicleta de producción más cercana a una máquina de MotoGP que un usuario puede tener en su garaje. Es una pieza de arte tecnológico, diseñada en Borgo Panigale, que combina la pasión italiana con una capacidad dinámica que desafía los límites de la física.',
      imagenes: ['duc3', 'duc1', 'duc2'],
    },
  ];

  const [menuOpen, setMenuOpen] = useState(false);
  const [adminFrameKey, setAdminFrameKey] = useState(0);
  const [recoveryEmail, setRecoveryEmail] = useState('');
  const [registrationEmail, setRegistrationEmail] = useState('');
  const [proyectos] = useState(obtenerProyectosDefecto());
  
  const getInitialView = () => {
    const path = window.location.pathname;
    const params = new URLSearchParams(window.location.search);
    if (params.get('recovery') === '1' || window.location.hash.includes('access_token=')) {
      return 'nueva-contrasena';
    }
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

  // Estado de la barra superior y de los modales/notificaciones.
  // Estos estados se perdieron durante el merge y por eso Vercel
  // estaba reportando varios "is not defined".
  const [navNotifications, setNavNotifications] = useState([]);
  const [navNotificationsOpen, setNavNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [userDashboardSection, setUserDashboardSection] = useState('resumen');

  const [selectedProject, setSelectedProject] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const [dialog, setDialog] = useState(null);
  const [toast, setToast] = useState(null);

  const [afterLoginView, setAfterLoginView] = useState(null);

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

  const closeDialog = () => {
    setDialog(null);
  };

  const abrirNotificacionSuperior = async (item) => {
    if (!item) return;

    if (!item.leida) {
      try {
        if (typeof NotificacionesService?.marcarLeida === 'function') {
          await NotificacionesService.marcarLeida(item.idnotificacion);
        }

        setNavNotifications((items) =>
          items.map((actual) =>
            actual.idnotificacion === item.idnotificacion
              ? { ...actual, leida: true }
              : actual
          )
        );
      } catch (error) {
        // No bloqueamos la navegación si falla el marcado de lectura.
        console.warn('No se pudo marcar la notificacion como leida:', error);
      }
    }

    setNavNotificationsOpen(false);

    if (user?.role === 'usuario' || user?.role === 'cliente') {
      const seccionPorReferencia = {
        cotizacion: 'cotizaciones',
        factura: 'facturas',
        orden: 'taller',
        pedido: 'pedidos',
        cita: 'resumen',
      };

      setUserDashboardSection(
        seccionPorReferencia[item.referencia_tipo] || 'resumen'
      );

      setView('user-dashboard');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    if (
      user?.role === 'admin' &&
      item.tipo === 'solicitud_reprogramacion'
    ) {
      window.location.assign(
        `${getApiBaseUrl().replace(/\/$/, '')}/admin/citas?notificacion=${encodeURIComponent(item.idnotificacion)}`
      );
      return;
    }

    const destino =
      item.accion_url ||
      (user?.role === 'admin' ? '/admin/citas' : '/mecanico');

    window.location.assign(
      `${getApiBaseUrl().replace(/\/$/, '')}${destino}`
    );
  };

  useEffect(() => {
    const cargarNotificaciones = async () => {
      if (!user || typeof NotificacionesService?.listar !== 'function') {
        setNavNotifications([]);
        return;
      }

      try {
        const data = await NotificacionesService.listar();
        setNavNotifications(data?.notificaciones || data || []);
      } catch (error) {
        console.warn('No se pudieron cargar las notificaciones:', error);
        setNavNotifications([]);
      }
    };

    cargarNotificaciones();
  }, [user]);

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

        <NightSky />

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
                <>
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
                  <li className="nav-item">
                    <button
                      className={`nav-link text-warning fw-bold p-2 bg-transparent border-0 dmi-nav-link ${view === 'gallery-admin' ? 'active' : ''}`}
                      onClick={() => {
                        setView('gallery-admin');
                        setMenuOpen(false);
                      }}
                    >
                      GALERÍA
                    </button>
                  </li>
                </>
              )}
              
              {/* MI CUENTA / MECANICO SEGUN EL ESTADO DE SESION.
                  PANEL ADMIN YA SE RENDERIZA ARRIBA, UNA SOLA VEZ. */}
              {!user ? (
                <li className="nav-item">
                  <button
                    type="button"
                    className="btn btn-danger px-4 rounded-0 fw-bold shadow-sm dmi-nav-cta"
                    onClick={() => {
                      setView('login');
                      setMenuOpen(false);
                    }}
                  >
                    MI CUENTA
                  </button>
                </li>
              ) : isMechanicRole(user.role) ? (
                <li className="nav-item">
                  <button
                    type="button"
                    className="nav-link text-danger fw-black p-2 bg-transparent border-0 dmi-nav-link"
                    onClick={() => {
                      setMenuOpen(false);
                      goToMechanicPanel();
                    }}
                  >
                    MECANICO
                  </button>
                </li>
              ) : user.role !== 'admin' ? (
                <li className="nav-item">
                  <button
                    type="button"
                    className={`btn btn-danger px-4 rounded-0 fw-bold shadow-sm dmi-nav-cta ${view === 'user-dashboard' ? 'active' : ''}`}
                    onClick={() => {
                      setView('user-dashboard');
                      setMenuOpen(false);
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                  >
                    MI CUENTA
                  </button>
                </li>
              ) : null}

              {user && <li className="nav-item dmi-nav-tools">
                <div className="dmi-nav-popover-wrap">
                  <button
                    type="button"
                    className="dmi-nav-icon"
                    aria-label="Notificaciones"
                    onClick={() => {
                      setNavNotificationsOpen((open) => !open);
                      setProfileOpen(false);
                    }}
                  >
                    <span aria-hidden="true">🔔</span>
                    {navNotifications.filter((item) => !item.leida).length > 0 && (
                      <b>{navNotifications.filter((item) => !item.leida).length}</b>
                    )}
                  </button>

                  {navNotificationsOpen && (
                    <div className="dmi-nav-popover">
                      <header><strong>Notificaciones</strong></header>
                      {navNotifications.length ? (
                        navNotifications.slice(0, 6).map((item) => (
                          <button
                            key={item.idnotificacion}
                            type="button"
                            className={item.leida ? 'read' : 'unread'}
                            onClick={() => abrirNotificacionSuperior(item)}
                          >
                            <strong>{item.titulo}</strong>
                            <span>{item.mensaje}</span>
                          </button>
                        ))
                      ) : (
                        <p>Estás al día.</p>
                      )}
                    </div>
                  )}
                </div>

                <div className="dmi-nav-popover-wrap">
                  <button
                    type="button"
                    className="dmi-nav-icon profile"
                    aria-label="Perfil"
                    onClick={() => {
                      setProfileOpen((open) => !open);
                      setNavNotificationsOpen(false);
                    }}
                  >
                    <span aria-hidden="true">👤</span>
                  </button>

                  {profileOpen && (
                    <div className="dmi-nav-popover profile-card">
                      <strong>{getDisplayName(user)}</strong>
                      <span>{user.email || 'Correo no disponible'}</span>
                      <small>{String(user.role || 'usuario').replace('_', ' ')}</small>

                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm w-100 mt-3 rounded-0 fw-bold"
                        onClick={() => {
                          setProfileOpen(false);
                          setNavNotificationsOpen(false);
                          handleLogout();
                        }}
                      >
                        CERRAR SESIÓN
                      </button>
                    </div>
                  )}
                </div>
              </li>}

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

        {view === 'gallery-admin' && (
          <section style={{ width: '100%', minHeight: 'calc(100vh - 84px)', backgroundColor: '#050506', padding: '0' }}>
            <AdminGalleryManager />
          </section>
        )}

        {view !== 'inicio' && (
          view !== 'admin-dashboard' && (
          <section className={`container py-5 dmi-view-section ${view === 'catalogo' ? 'dmi-catalog-section' : ''}`}>
            <div className="row justify-content-center">
              <div className={`${view === 'catalogo' ? 'col-12' : 'col-12 col-xl-10'} animate-slide-in dmi-view-column`}>
                <div className={`card bg-dark text-white border-danger border-opacity-50 shadow-lg p-4 p-md-5 dmi-view-card ${view === 'catalogo' ? 'dmi-catalog-card' : ''}`}>

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

                  {view === 'login' && (
                    <LoginView 
                      onLoginSuccess={handleLoginSuccess} 
                      onSwitchToRegister={() => setView('registro-usuario')} 
                      onForgotPassword={(email) => {
                        setRecoveryEmail(email);
                        setView('recuperar-contrasena');
                      }}
                      openConfirm={openConfirm}
                    />
                  )}
                  {view === 'recuperar-contrasena' && <RecuperarPasswordView email={recoveryEmail} onBackToLogin={() => setView('login')} openConfirm={openConfirm} />}
                  {view === 'nueva-contrasena' && <NuevaPasswordView onBackToLogin={() => setView('login')} openConfirm={openConfirm} />}
                  {view === 'registro-usuario' && (
                    <RegistroUsuarioView
                      onRegisterSuccess={() => setView('login')}
                      onVerificationNeeded={(email) => {
                        setRegistrationEmail(email);
                        setView('verificar-registro');
                      }}
                      openConfirm={openConfirm}
                    />
                  )}
                  {view === 'verificar-registro' && <VerificarRegistroView email={registrationEmail} onVerified={() => setView('login')} onBackToRegister={() => setView('registro-usuario')} openConfirm={openConfirm} />}

                  {view === 'user-dashboard' && (
                    <MiCuenta
                      onAddVehicle={() => setView('registro')}
                      onScheduleAppointment={() => setView('citas')}
                      initialSection={userDashboardSection}
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

                <CloudinaryGallery 
                  proyectos={proyectos}
                  onSelectProject={(proyecto) => {
                    setSelectedProject(proyecto);
                    setShowModal(true);
                  }}
                />
              </div>
            </section>

            {/* MODAL CON CARRUSEL DE IMAGENES CLOUDINARY */}
            <CloudinaryCarousel 
              proyecto={selectedProject}
              isOpen={showModal}
              onClose={() => setShowModal(false)}
            />
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