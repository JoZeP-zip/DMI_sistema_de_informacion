import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faKey, faCar, faUserCheck, faShield,
  faChevronRight, faChevronLeft, faCheckCircle,
  faEye, faEyeSlash,
} from '@fortawesome/free-solid-svg-icons';
import '../styles/RegistrarUnidad.css';
import { showDmiError, showDmiSuccess } from './DmiMessages';

const getApiBaseUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

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
const STEPS          = ['Cliente', 'VehÃ­culo'];
const tiposDocumento = ['CC', 'CE', 'NIT', 'Pasaporte', 'TI'];

const initialCliente = {
  email: '', contraseña: '', confirmarcontraseña: '', nombre: '', apellido: '',
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
  const [showConfirmPw, setShowConfirmPw] = useState(false);
  const [submitted, setSubmitted]   = useState(false);
  const [loading, setLoading]       = useState(false);
  const [, setError]                = useState('');
  const [tiposVehiculo, setTiposVehiculo] = useState([]);

  // â”€â”€ Cargar tipos de vehÃ­culo desde la BD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        const message = err.message || 'No se pudieron cargar los tipos de vehiculo desde Supabase.';
        setError(message);
        showDmiError('No se pudieron cargar los tipos', message);
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

    if (!isExistingUser && cliente.contraseña !== cliente.confirmarcontraseña) {
      showDmiError('Las contraseñas no coinciden', 'La contraseña y la confirmacion deben ser iguales para continuar.');
      return;
    }

    setStep(1);
  };

  // â”€â”€ Submit final: registro usuario + vehÃ­culo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

      // PASO 1: Registrar usuario vÃ­a /registro-react (devuelve JSON)
      if (!isExistingUser) {
      const regRes = await fetch(`${BASE_URL}/registro-react`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email:            cliente.email,
          password:         cliente.contraseña,
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

      // PASO 2: Login automÃ¡tico para obtener cookie de sesiÃ³n
      const loginRes = await fetch(`${BASE_URL}/login-react`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: cliente.email, password: cliente.contraseña }),
      });

      loginData = await loginRes.json();
      if (!loginRes.ok || loginData.error) throw new Error(loginData.error || loginData.message || 'No se pudo iniciar sesion.');

      // Guardar token en localStorage para uso posterior
      localStorage.setItem('token',  loginData.token);
      localStorage.setItem('role',   loginData.role);
      localStorage.setItem('email',  loginData.email);
      localStorage.setItem('nombre', loginData.nombre);
      }

      // PASO 3: Registrar vehÃ­culo vÃ­a /vehiculo/nuevo (usa cookie de sesiÃ³n)
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
      // Como el registro es nuevo, la cookie no estÃ¡ seteada aÃºn en el browser.
      // SoluciÃ³n: llamar al endpoint /login estÃ¡ndar para que FastAPI setee la cookie.
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
        body: new URLSearchParams({ email: cliente.email, password: cliente.contraseña }).toString(),
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
        showDmiSuccess('Vehiculo registrado', 'El vehiculo quedo guardado correctamente en tu cuenta.');
        if (onComplete) window.setTimeout(onComplete, 900);
      } else {
        if (vehData.error) throw new Error(vehData.error);
        throw new Error(`Error al registrar vehiculo (${vehRes.status})`);
      }

    } catch (err) {
      const message = err.message || 'Error inesperado. Intenta de nuevo.';
      setError(message);
      showDmiError('No se pudo registrar', message);
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

  // â”€â”€ Pantalla de Ã©xito â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  if (submitted) return (
    <div className="ru-wrapper">
      <div className="ru-container">
        <div className="ru-card">
          <div className="ru-success-box">
            <div className="ru-success-icon"><FontAwesomeIcon icon={faCheckCircle} /></div>
            <p className="ru-success-title">Â¡Registro Completado!</p>
            <p className="ru-success-text">
              El cliente{' '}
              <strong className="ru-highlight">{isExistingUser ? existingName : `${cliente.nombre} ${cliente.apellido}`}</strong>{' '}
              y el vehÃ­culo con placa{' '}
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

        {/* â”€â”€ Header â”€â”€ */}
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

        {/* â”€â”€ Stepper â”€â”€ */}
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


        {/* â•â•â•â•â•â• PASO 1 â€“ CLIENTE â•â•â•â•â•â• */}
        {!isExistingUser && step === 0 && (
          <form onSubmit={handleNext}>
            <div className="ru-card">
              <div className="ru-card-head cliente">
                <div className="ru-head-icon"><FontAwesomeIcon icon={faUserCheck} /></div>
                <h5 className="ru-head-title">InformaciÃ³n del Cliente</h5>
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
                    <label className="ru-label">Correo electrÃ³nico <span className="ru-req">*</span></label>
                    <input className="ru-input" type="email" name="email"
                      value={cliente.email} onChange={onCliente}
                      placeholder="juan@email.com" required />
                  </div>
                </div>

                <div className="ru-row mb-22">
                  <div className="ru-field">
                    <label className="ru-label">contraseña <span className="ru-req">*</span></label>
                    <div className="ru-pw-wrap">
                      <input
                        className="ru-input pr-40"
                        type={showPw ? 'text' : 'password'}
                        name="contraseña" value={cliente.contraseña}
                        onChange={onCliente} placeholder="********" required minLength={6}
                      />
                      <button type="button" className="ru-pw-eye" onClick={() => setShowPw((value) => !value)} aria-label={showPw ? 'Ocultar contraseña' : 'Ver contraseña'}>
                        <FontAwesomeIcon icon={showPw ? faEyeSlash : faEye} />
                      </button>
                    </div>
                  </div>
                  <div className="ru-field">
                    <label className="ru-label">Confirmar contraseña <span className="ru-req">*</span></label>
                    <div className="ru-pw-wrap">
                      <input
                        className="ru-input pr-40"
                        type={showConfirmPw ? 'text' : 'password'}
                        name="confirmarcontraseña"
                        value={cliente.confirmarcontraseña}
                        onChange={onCliente}
                        placeholder="Confirma tu contraseña"
                        required
                        minLength={6}
                      />
                      <button type="button" className="ru-pw-eye" onClick={() => setShowConfirmPw((value) => !value)} aria-label={showConfirmPw ? 'Ocultar confirmacion' : 'Ver confirmacion'}>
                        <FontAwesomeIcon icon={showConfirmPw ? faEyeSlash : faEye} />
                      </button>
                    </div>
                  </div>
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
                      placeholder="PÃ©rez" required />
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
                    <label className="ru-label">NÂ° Documento <span className="ru-req">*</span></label>
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
                    <label className="ru-label">TelÃ©fono</label>
                    <input className="ru-input" type="tel" name="telefono"
                      value={cliente.telefono} onChange={onCliente}
                      placeholder="555-0123" />
                  </div>
                </div>
              </div>
            </div>

            <div className="ru-btn-row">
              <button type="submit" className="ru-btn-primary">
                Siguiente: VehÃ­culo <FontAwesomeIcon icon={faChevronRight} />
              </button>
            </div>
          </form>
        )}

        {/* â•â•â•â•â•â• PASO 2 â€“ VEHÃCULO â•â•â•â•â•â• */}
        {step === 1 && (
          <form onSubmit={handleSubmit}>
            <div className="ru-card">
              <div className="ru-card-head vehiculo">
                <div className="ru-head-icon"><FontAwesomeIcon icon={faShield} /></div>
                <h5 className="ru-head-title">Detalles del VehÃ­culo</h5>
              </div>

              <div className="ru-body">
                <p className="ru-section">IdentificaciÃ³n</p>
                <div className="ru-row">
                  <div className="ru-field">
                    <label className="ru-label">CÃ³digo <span className="ru-req">*</span></label>
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
                    <label className="ru-label">Tipo de vehÃ­culo <span className="ru-req">*</span></label>
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
                  <label className="ru-label">DescripciÃ³n</label>
                  <textarea className="ru-textarea" name="descripcion"
                    value={vehiculo.descripcion} onChange={onVehiculo}
                    placeholder="DescripciÃ³n general del vehÃ­culo..." />
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


