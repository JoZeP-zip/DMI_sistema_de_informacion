import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faKey, faCar, faUserCheck, faShield,
  faChevronRight, faChevronLeft, faCheckCircle,
  faEye, faEyeSlash,
} from '@fortawesome/free-solid-svg-icons';
import '../styles/RegistrarUnidad.css';

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

const BASE_URL = getApiBaseUrl();
const STEPS          = ['Cliente', 'Vehículo'];
const tiposDocumento = ['CC', 'CE', 'NIT', 'Pasaporte', 'TI'];

const initialCliente = {
  email: '', contrasena: '', nombre: '', apellido: '',
  fechaNacimiento: '', tipoDocumento: '', documento: '',
  telefono: '', nombreUsuario: '',
};

const initialVehiculo = {
  codigo: '', placa: '', marca: '', tipoVehiculo: '',
  tipoVehiculoNuevo: '', descripcion: '', motor: '', asientos: '', capacidad: '', modelos: '',
};

const cx = (...classes) => classes.filter(Boolean).join(' ');

export default function RegistrarUnidad({ onComplete } = {}) {
  const existingToken = localStorage.getItem('token');
  const existingName = localStorage.getItem('nombre') || localStorage.getItem('email') || '';
  const isExistingUser = Boolean(existingToken);
  const [step, setStep]             = useState(isExistingUser ? 1 : 0);
  const [cliente, setCliente]       = useState(initialCliente);
  const [vehiculo, setVehiculo]     = useState(initialVehiculo);
  const [showPw, setShowPw]         = useState(false);
  const [submitted, setSubmitted]   = useState(false);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [tiposVehiculo, setTiposVehiculo] = useState([]);

  // ── Cargar tipos de vehículo desde la BD ───────────────────────
  useEffect(() => {
    fetch(`${BASE_URL}/api/tipovehiculos`)
      .then(res => {
        if (!res.ok) throw new Error('No se pudieron cargar los tipos de vehiculo.');
        return res.json();
      })
      .then(data => {
        setTiposVehiculo(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        setTiposVehiculo([]);
        setError(err.message || 'No se pudieron cargar los tipos de vehiculo desde Supabase.');
      });
  }, []);

  const onCliente  = e => setCliente(p  => ({ ...p, [e.target.name]: e.target.value }));
  const onVehiculo = e => {
    const { name, value } = e.target;
    setVehiculo(p => ({
      ...p,
      [name]: value,
      ...(name === 'tipoVehiculo' && value !== 'nuevo' ? { tipoVehiculoNuevo: '' } : {}),
    }));
  };

  const handleNext = (e) => {
    e.preventDefault();
    setError('');
    setStep(1);
  };

  // ── Submit final: registro usuario + vehículo ──────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      let loginData = {
        token: existingToken,
        role: localStorage.getItem('role') || 'usuario',
        email: localStorage.getItem('email') || '',
        nombre: localStorage.getItem('nombre') || '',
      };

      // PASO 1: Registrar usuario vía /registro-react (devuelve JSON)
      if (!isExistingUser) {
      const regRes = await fetch(`${BASE_URL}/registro-react`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email:            cliente.email,
          password:         cliente.contrasena,
          nombre:           cliente.nombre,
          apellidos:        cliente.apellido,
          documento:        cliente.documento,
          tipodedocumento:  cliente.tipoDocumento,
          fechadenacimiento: cliente.fechaNacimiento,
          telefono:         cliente.telefono,
          usuarionombre:    cliente.nombreUsuario,
        }),
      });

      const regData = await regRes.json();
      if (!regRes.ok || regData.error) throw new Error(regData.error || regData.message || 'No se pudo registrar el usuario.');

      // PASO 2: Login automático para obtener cookie de sesión
      const loginRes = await fetch(`${BASE_URL}/login-react`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: cliente.email, password: cliente.contrasena }),
      });

      loginData = await loginRes.json();
      if (!loginRes.ok || loginData.error) throw new Error(loginData.error || loginData.message || 'No se pudo iniciar sesion.');

      // Guardar token en localStorage para uso posterior
      localStorage.setItem('token',  loginData.token);
      localStorage.setItem('role',   loginData.role);
      localStorage.setItem('email',  loginData.email);
      localStorage.setItem('nombre', loginData.nombre);
      }

      // PASO 3: Registrar vehículo vía /vehiculo/nuevo (usa cookie de sesión)
      // Como FastAPI lee la cookie httponly, necesitamos hacer login tradicional
      // para que la cookie quede seteada correctamente.
      // Usamos el token JWT como header Authorization en su lugar:
      let tipoVehiculoId = vehiculo.tipoVehiculo;
      if (vehiculo.tipoVehiculo === 'nuevo') {
        const tipoRes = await fetch(`${BASE_URL}/api/tipovehiculos/nuevo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ vehiculo: vehiculo.tipoVehiculoNuevo }),
        });
        const tipoData = await tipoRes.json().catch(() => ({}));
        if (!tipoRes.ok || tipoData.error) {
          throw new Error(tipoData.error || 'No se pudo crear el tipo de vehiculo.');
        }
        tipoVehiculoId = tipoData.idtipovehiculos || tipoData.id;
      }

      const vehForm = new URLSearchParams({
        codigovehiculo:               vehiculo.codigo,
        placa:                        vehiculo.placa,
        marca:                        vehiculo.marca,
        tipovehiculos_idtipovehiculos: tipoVehiculoId,
        descripcionvehiculo:          vehiculo.descripcion || '',
        motor:                        vehiculo.motor || '',
        cantidad_asientos:            vehiculo.asientos || '',
        capacidad:                    vehiculo.capacidad || '',
        modelo:                       vehiculo.modelos || '',
      });

      // Nota: /vehiculo/nuevo lee la cookie access_token.
      // Como el registro es nuevo, la cookie no está seteada aún en el browser.
      // Solución: llamar al endpoint /login estándar para que FastAPI setee la cookie.
      if (!isExistingUser) {
      await fetch(`${BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          ...(loginData.token ? { Authorization: `Bearer ${loginData.token}` } : {}),
        },
        credentials: 'include',
        body: new URLSearchParams({ email: cliente.email, password: cliente.contrasena }).toString(),
      });
      // (ignoramos el redirect, lo que nos importa es que la cookie quede seteada)
      }

      const vehRes = await fetch(`${BASE_URL}/vehiculo/nuevo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          ...(loginData.token ? { Authorization: `Bearer ${loginData.token}` } : {}),
        },
        credentials: 'include',
        body: vehForm.toString(),
      });

      const vehData = await vehRes.json().catch(() => ({}));

      if (vehRes.ok && !vehData.error) {
        setSubmitted(true);
        if (onComplete) window.setTimeout(onComplete, 900);
      } else {
        if (vehData.error) throw new Error(vehData.error);
        throw new Error(`Error al registrar vehículo (${vehRes.status})`);
      }

    } catch (err) {
      setError(err.message || 'Error inesperado. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setSubmitted(false);
    setStep(isExistingUser ? 1 : 0);
    setError('');
    setCliente(initialCliente);
    setVehiculo(initialVehiculo);
  };

  // ── Pantalla de éxito ──────────────────────────────────────────
  if (submitted) return (
    <div className="ru-wrapper">
      <div className="ru-container">
        <div className="ru-card">
          <div className="ru-success-box">
            <div className="ru-success-icon"><FontAwesomeIcon icon={faCheckCircle} /></div>
            <p className="ru-success-title">¡Registro Completado!</p>
            <p className="ru-success-text">
              El cliente{' '}
              <strong className="ru-highlight">{isExistingUser ? existingName : `${cliente.nombre} ${cliente.apellido}`}</strong>{' '}
              y el vehículo con placa{' '}
              <strong className="ru-highlight">{vehiculo.placa}</strong>{' '}
              han sido registrados exitosamente en Disol Motors.
            </p>
            <button className="ru-btn-primary centered" onClick={reset}>
              Nuevo Registro
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="ru-wrapper">
      <div className="ru-container">

        {/* ── Header ── */}
        <div className="ru-header">
          <div className="ru-icon-row">
            <div className="ru-icon-box"><FontAwesomeIcon icon={faKey} /></div>
            <div className="ru-icon-box"><FontAwesomeIcon icon={faCar} /></div>
          </div>
          <h1 className="ru-title">{isExistingUser ? 'Registrar Vehiculo' : 'Asistente de Cuenta y Vehiculo'}</h1>
          <p className="ru-subtitle">
            {isExistingUser
              ? 'Agrega un vehiculo a tu cuenta para continuar con tus citas.'
              : 'Paso 1: crea tu cuenta. Paso 2: registra tu vehiculo.'}
          </p>
        </div>

        {/* ── Stepper ── */}
        <div className="ru-stepper">
          {STEPS.map((label, i) => (
            <React.Fragment key={i}>
              <div className="ru-step-wrap">
                <div className={cx('ru-step-circle', step === i && 'active', step > i && 'done')}>
                  {step > i ? <FontAwesomeIcon icon={faCheckCircle} /> : i + 1}
                </div>
                <span className={cx('ru-step-label', step === i && 'active', step > i && 'done')}>
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={cx('ru-step-conn', step > i && 'done')} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Banner de error global */}
        {error && (
          <div className="alert alert-danger small py-2 rounded-0 border-danger bg-black text-danger mb-3">
            ⚠️ {error}
          </div>
        )}

        {/* ══════ PASO 1 – CLIENTE ══════ */}
        {!isExistingUser && step === 0 && (
          <form onSubmit={handleNext}>
            <div className="ru-card">
              <div className="ru-card-head cliente">
                <div className="ru-head-icon"><FontAwesomeIcon icon={faUserCheck} /></div>
                <h5 className="ru-head-title">Información del Cliente</h5>
              </div>

              <div className="ru-body">
                <p className="ru-section">Datos de acceso</p>
                <div className="ru-row">
                  <div className="ru-field">
                    <label className="ru-label">Nombre de usuario <span className="ru-req">*</span></label>
                    <input className="ru-input" type="text" name="nombreUsuario"
                      value={cliente.nombreUsuario} onChange={onCliente}
                      placeholder="juanperez92" required />
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">Correo electrónico <span className="ru-req">*</span></label>
                    <input className="ru-input" type="email" name="email"
                      value={cliente.email} onChange={onCliente}
                      placeholder="juan@email.com" required />
                  </div>
                </div>

                <div className="ru-row mb-22">
                  <div className="ru-field">
                    <label className="ru-label">Contraseña <span className="ru-req">*</span></label>
                    <div className="ru-pw-wrap">
                      <input
                        className="ru-input pr-40"
                        type={showPw ? 'text' : 'password'}
                        name="contrasena" value={cliente.contrasena}
                        onChange={onCliente} placeholder="••••••••" required minLength={6}
                      />
                      <button type="button" className="ru-pw-eye" onClick={() => setShowPw(p => !p)}>
                        <FontAwesomeIcon icon={showPw ? faEyeSlash : faEye} />
                      </button>
                    </div>
                  </div>
                  <div className="ru-field empty" />
                </div>

                <p className="ru-section">Datos personales</p>
                <div className="ru-row">
                  <div className="ru-field">
                    <label className="ru-label">Nombre <span className="ru-req">*</span></label>
                    <input className="ru-input" type="text" name="nombre"
                      value={cliente.nombre} onChange={onCliente}
                      placeholder="Juan" required />
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">Apellido <span className="ru-req">*</span></label>
                    <input className="ru-input" type="text" name="apellido"
                      value={cliente.apellido} onChange={onCliente}
                      placeholder="Pérez" required />
                  </div>
                </div>

                <div className="ru-row">
                  <div className="ru-field w-155">
                    <label className="ru-label">Tipo doc. <span className="ru-req">*</span></label>
                    <select className="ru-select" name="tipoDocumento"
                      value={cliente.tipoDocumento} onChange={onCliente} required>
                      <option value="">Seleccionar</option>
                      {tiposDocumento.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">N° Documento <span className="ru-req">*</span></label>
                    <input className="ru-input" type="text" name="documento"
                      value={cliente.documento} onChange={onCliente}
                      placeholder="1234567890" required />
                  </div>
                </div>

                <div className="ru-row">
                  <div className="ru-field">
                    <label className="ru-label">Fecha de nacimiento <span className="ru-req">*</span></label>
                    <input className="ru-input" type="date" name="fechaNacimiento"
                      value={cliente.fechaNacimiento} onChange={onCliente} required />
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">Teléfono</label>
                    <input className="ru-input" type="tel" name="telefono"
                      value={cliente.telefono} onChange={onCliente}
                      placeholder="555-0123" />
                  </div>
                </div>
              </div>
            </div>

            <div className="ru-btn-row">
              <button type="submit" className="ru-btn-primary">
                Siguiente: Vehículo <FontAwesomeIcon icon={faChevronRight} />
              </button>
            </div>
          </form>
        )}

        {/* ══════ PASO 2 – VEHÍCULO ══════ */}
        {step === 1 && (
          <form onSubmit={handleSubmit}>
            <div className="ru-card">
              <div className="ru-card-head vehiculo">
                <div className="ru-head-icon"><FontAwesomeIcon icon={faShield} /></div>
                <h5 className="ru-head-title">Detalles del Vehículo</h5>
              </div>

              <div className="ru-body">
                <p className="ru-section">Identificación</p>
                <div className="ru-row">
                  <div className="ru-field">
                    <label className="ru-label">Código <span className="ru-req">*</span></label>
                    <input className="ru-input" type="text" name="codigo"
                      value={vehiculo.codigo} onChange={onVehiculo}
                      placeholder="VEH-001" required />
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">Placa <span className="ru-req">*</span></label>
                    <input className="ru-input uppercase" type="text" name="placa"
                      value={vehiculo.placa} onChange={onVehiculo}
                      placeholder="XYZ-123" required />
                  </div>
                </div>

                <div className="ru-row">
                  <div className="ru-field">
                    <label className="ru-label">Marca <span className="ru-req">*</span></label>
                    <input className="ru-input" type="text" name="marca"
                      value={vehiculo.marca} onChange={onVehiculo}
                      placeholder="Nissan" required />
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">Tipo de vehículo <span className="ru-req">*</span></label>
                    <select className="ru-select" name="tipoVehiculo"
                      value={vehiculo.tipoVehiculo} onChange={onVehiculo} required>
                      <option value="">Seleccionar</option>
                      {tiposVehiculo.map(t => (
                        <option key={t.idtipovehiculos || t.id} value={t.idtipovehiculos || t.id}>
                          {t.vehiculo || t.nombre || t.codigotipovehiculos}
                        </option>
                      ))}
                      <option value="nuevo">Agregar otro tipo</option>
                    </select>
                    {vehiculo.tipoVehiculo === 'nuevo' && (
                      <input
                        className="ru-input"
                        type="text"
                        name="tipoVehiculoNuevo"
                        value={vehiculo.tipoVehiculoNuevo}
                        onChange={onVehiculo}
                        placeholder="Escribe el nuevo tipo de vehiculo"
                        required
                      />
                    )}
                  </div>
                </div>

                <p className="ru-section">Especificaciones</p>
                <div className="ru-row">
                  <div className="ru-field">
                    <label className="ru-label">Motor</label>
                    <input className="ru-input" type="text" name="motor"
                      value={vehiculo.motor} onChange={onVehiculo}
                      placeholder="2.0L Turbo" />
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">Modelo</label>
                    <input className="ru-input" type="text" name="modelos"
                      value={vehiculo.modelos} onChange={onVehiculo}
                      placeholder="Sentra 2022" />
                  </div>
                </div>

                <div className="ru-row">
                  <div className="ru-field">
                    <label className="ru-label">Asientos</label>
                    <input className="ru-input" type="number" name="asientos"
                      value={vehiculo.asientos} onChange={onVehiculo}
                      placeholder="5" min="1" />
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">Capacidad (kg)</label>
                    <input className="ru-input" type="text" name="capacidad"
                      value={vehiculo.capacidad} onChange={onVehiculo}
                      placeholder="1500 kg" />
                  </div>
                </div>

                <div className="ru-field">
                  <label className="ru-label">Descripción</label>
                  <textarea className="ru-textarea" name="descripcion"
                    value={vehiculo.descripcion} onChange={onVehiculo}
                    placeholder="Descripción general del vehículo..." />
                </div>
              </div>
            </div>

            <div className="ru-btn-row">
              {!isExistingUser && (
                <button
                  type="button"
                  className="ru-btn-secondary"
                  onClick={() => setStep(0)}
                  disabled={loading}
                >
                  <FontAwesomeIcon icon={faChevronLeft} /> Volver
                </button>
              )}
              <button
                type="submit"
                className="ru-btn-primary"
                disabled={loading}
              >
                {loading
                  ? 'Registrando...'
                  : <><FontAwesomeIcon icon={faCheckCircle} /> Finalizar Registro</>
                }
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  );
}
