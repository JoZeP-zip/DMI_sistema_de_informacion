import React, { useState, useEffect } from 'react';
import '../styles/AgendarCita.css';

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

const HORARIOS_TALLER = [
  '08:00', '09:00', '10:00', '11:00',
  '12:00', '14:00', '15:00', '16:00', '17:00'
];

const SERVICIOS_FALLBACK = [
  { idservicios: 'fallback-diagnostico', descripcionservicio: 'Diagnostico computarizado' },
  { idservicios: 'fallback-repro', descripcionservicio: 'Reprogramacion de ECU' },
  { idservicios: 'fallback-mecanica', descripcionservicio: 'Mecanica general' },
];

const obtenerNombreServicio = (servicio) => {
  return String(
    servicio.descripcionservicio
      || servicio.descripcion
      || servicio.nombre
      || servicio.codigoservicio
      || ''
  ).trim();
};

const normalizarFecha = (value) => {
  if (!value) return '';
  return String(value).slice(0, 10);
};

const normalizarHora = (value) => {
  if (!value) return '';
  return String(value).slice(0, 5);
};

const AgendarCita = ({ onNeedLogin, onNeedVehicle, onGoGarage }) => {
  const [confirmado, setConfirmado] = useState(false);
  const [vehiculos, setVehiculos] = useState([]);
  const [citasRegistradas, setCitasRegistradas] = useState([]);
  const [servicios, setServicios] = useState([]);
  const [error, setError] = useState('');
  const [loadingData, setLoadingData] = useState(true);
  const [vehiclePromptShown, setVehiclePromptShown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    vehiculos_idvehiculo: '',
    descripcion_vehiculo: '',
    fecha_cita: '',
    hora_cita: '',
    motivo: '',
    observaciones: '',
  });

  const token = localStorage.getItem('token');

  const cargarDatosAgenda = async () => {
    if (!token) {
      setLoadingData(false);
      if (onNeedLogin) onNeedLogin();
      return;
    }

    setLoadingData(true);

    try {
      const garageRes = await fetch(`${BASE_URL}/api/mi-garage`, {
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
      });
      const garageData = await garageRes.json();
      setVehiculos(Array.isArray(garageData.vehiculos) ? garageData.vehiculos : []);
      setCitasRegistradas(Array.isArray(garageData.citas) ? garageData.citas : []);
    } catch (err) {
      setVehiculos([]);
      setCitasRegistradas([]);
    }

    try {
      const serviciosRes = await fetch(`${BASE_URL}/api/servicios`, {
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
      });
      const serviciosData = await serviciosRes.json();
      const serviciosValidos = Array.isArray(serviciosData)
        ? serviciosData.filter((servicio) => obtenerNombreServicio(servicio))
        : [];
      setServicios(serviciosValidos);
    } catch (err) {
      setServicios([]);
    }

    fetch(`${BASE_URL}/api/citas`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setCitasRegistradas((actuales) => {
            const propias = Array.isArray(actuales) ? actuales : [];
            const ids = new Set(propias.map((cita) => cita.idcita || cita.id));
            return [...propias, ...data.filter((cita) => !ids.has(cita.idcita || cita.id))];
          });
        }
      })
      .catch(() => {});

    setLoadingData(false);
  };

  useEffect(() => {
    cargarDatosAgenda();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (loadingData || !token || vehiclePromptShown) return;
    if (vehiculos.length === 0) {
      setVehiclePromptShown(true);
      if (onNeedVehicle) onNeedVehicle();
    }
  }, [loadingData, token, vehiculos.length, vehiclePromptShown, onNeedVehicle]);

  const horasOcupadas = citasRegistradas
    .filter((cita) => {
      const estado = String(cita.estado || '').toLowerCase();
      const fecha = normalizarFecha(cita.fecha || cita.fecha_cita || cita.fechacita);
      return fecha === formData.fecha_cita && estado !== 'cancelada' && estado !== 'cancelado';
    })
    .map((cita) => normalizarHora(cita.hora || cita.hora_cita || cita.horacita));

  const horariosDisponibles = HORARIOS_TALLER.filter((hora) => !horasOcupadas.includes(hora));
  const selectedVehicle = vehiculos.find((v) => String(v.idvehiculo) === String(formData.vehiculos_idvehiculo));

  const handleChange = (e) => {
    const { name, value } = e.target;
    const vehicle = name === 'vehiculos_idvehiculo'
      ? vehiculos.find((v) => String(v.idvehiculo) === String(value))
      : null;
    setFormData(prev => ({
      ...prev,
      [name]: value,
      ...(vehicle ? { descripcion_vehiculo: [vehicle.marca, vehicle.modelo, vehicle.placa].filter(Boolean).join(' ') } : {}),
      ...(name === 'fecha_cita' ? { hora_cita: '' } : {}),
    }));
  };

  const handleCita = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!horariosDisponibles.includes(formData.hora_cita)) {
      setError('Selecciona una hora disponible para esta fecha.');
      setLoading(false);
      return;
    }

    if (vehiculos.length > 0 && !formData.vehiculos_idvehiculo) {
      setError('Selecciona un vehiculo de Mi Garaje para continuar.');
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${BASE_URL}/citas/nueva`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        body: new URLSearchParams(formData).toString(),
      });

      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || 'No se pudo agendar la cita.');
      }

      setConfirmado(true);
      cargarDatosAgenda();
    } catch (err) {
      setError(err.message || 'No se pudo agendar la cita.');
    } finally {
      setLoading(false);
    }
  };

  const handleNuevaCita = () => {
    setConfirmado(false);
    setError('');
    setFormData({
      vehiculos_idvehiculo: '',
      descripcion_vehiculo: '',
      fecha_cita: '',
      hora_cita: '',
      motivo: '',
      observaciones: '',
    });
    cargarDatosAgenda();
  };

  return (
    <div className="agendar-cita-wrapper">
      <section className="section agendar-cita">
        <div className="section-title">
          <div className="ac-icon-row">
            <div className="ac-icon-box">CI</div>
            <div className="ac-icon-box">DM</div>
          </div>
          <h2>Agendar Cita</h2>
          <p>Disol Motors - Reserva tu servicio</p>
        </div>

        <div className="cita-card">
          {loadingData ? (
            <div className="cita-confirmada">
              <div className="success-icon">...</div>
              <h2>Revisando tu garaje</h2>
              <p>Estamos validando tus vehiculos registrados antes de agendar.</p>
            </div>
          ) : vehiculos.length === 0 ? (
            <div className="cita-confirmada">
              <div className="success-icon">DM</div>
              <h2>Primero registra tu vehiculo</h2>
              <p>
                Para agendar una cita necesitamos asociarla a un vehiculo de tu cuenta.
              </p>
              <div className="btn-row" style={{ justifyContent: 'center' }}>
                <button className="btn primary" onClick={onNeedVehicle} type="button">
                  Registrar vehiculo
                </button>
              </div>
            </div>
          ) : confirmado ? (
            <div className="cita-confirmada">
              <div className="success-icon">OK</div>
              <h2>Cita agendada</h2>
              <p>
                Te esperamos en <span className="highlight">Disol Motors</span>.<br />
                Hemos registrado tu cita exitosamente.
              </p>
              <div className="btn-row" style={{ justifyContent: 'center' }}>
                <button className="btn primary" onClick={handleNuevaCita}>
                  Agendar otra
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="cita-card-head">
                <div className="cita-head-icon">DM</div>
                <p className="cita-head-title">Datos de la cita</p>
              </div>

              {error && (
                <div className="alert alert-danger small py-2 rounded-0 border-danger bg-black text-danger mb-3">
                  {error}
                </div>
              )}

              <form className="cita-form" onSubmit={handleCita}>
                <p className="ac-section">Vehiculo</p>
                <div className="form-group">
                  <label>Selecciona un vehiculo de Mi Garaje <span className="ac-req">*</span></label>
                  <select
                    name="vehiculos_idvehiculo"
                    value={formData.vehiculos_idvehiculo}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Selecciona un vehiculo</option>
                    {vehiculos.map(v => (
                      <option key={v.idvehiculo} value={v.idvehiculo}>
                        {v.placa} - {v.marca} {v.modelo || ''}
                      </option>
                    ))}
                  </select>
                  {onGoGarage && (
                    <span className="hours-help">
                      Tambien puedes revisar tus vehiculos desde Mi Garaje.
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label>Descripcion del vehiculo <span className="ac-req">*</span></label>
                  <textarea
                    name="descripcion_vehiculo"
                    placeholder="Ejemplo: Renault Logan 2012, falla al encender, ruido en motor..."
                    value={formData.descripcion_vehiculo || [selectedVehicle?.marca, selectedVehicle?.modelo, selectedVehicle?.placa].filter(Boolean).join(' ')}
                    onChange={handleChange}
                    rows={3}
                    required
                  />
                </div>

                <p className="ac-section">Programacion</p>
                <div className="form-row">
                  <div className="form-group no-mb">
                    <label>Fecha <span className="ac-req">*</span></label>
                    <input
                      type="date"
                      name="fecha_cita"
                      value={formData.fecha_cita}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-group no-mb">
                    <label>Hora disponible <span className="ac-req">*</span></label>
                    <select
                      name="hora_cita"
                      value={formData.hora_cita}
                      onChange={handleChange}
                      required
                      disabled={!formData.fecha_cita}
                    >
                      <option value="">
                        {formData.fecha_cita ? 'Selecciona una hora' : 'Primero selecciona fecha'}
                      </option>
                      {HORARIOS_TALLER.map((hora) => {
                        const ocupada = horasOcupadas.includes(hora);
                        return (
                          <option key={hora} value={hora} disabled={ocupada}>
                            {hora} {ocupada ? '- Ocupada' : '- Disponible'}
                          </option>
                        );
                      })}
                    </select>
                    {formData.fecha_cita && (
                      <span className="hours-help">
                        {horariosDisponibles.length
                          ? `${horariosDisponibles.length} horarios disponibles para esta fecha.`
                          : 'No hay horarios disponibles para esta fecha.'}
                      </span>
                    )}
                  </div>
                </div>

                <p className="ac-section">Servicio</p>
                <div className="form-group">
                  <label>Servicio <span className="ac-req">*</span></label>
                  <select
                    name="motivo"
                    value={formData.motivo}
                    onChange={handleChange}
                    required
                  >
                    <option value="" disabled>Selecciona un servicio</option>
                    {(servicios.length ? servicios : SERVICIOS_FALLBACK).map((servicio) => {
                      const label = obtenerNombreServicio(servicio);
                      return (
                        <option key={servicio.idservicios || servicio.id || label} value={label}>
                          {label}
                        </option>
                      );
                    })}
                  </select>
                </div>
                <div className="form-group">
                  <label>Observaciones</label>
                  <textarea
                    name="observaciones"
                    placeholder="Describe el problema o detalle adicional..."
                    value={formData.observaciones}
                    onChange={handleChange}
                    rows={4}
                  />
                </div>

                <div className="btn-row">
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={handleNuevaCita}
                    disabled={loading}
                  >
                    Limpiar
                  </button>
                  <button type="submit" className="btn primary" disabled={loading || !horariosDisponibles.length}>
                    {loading ? 'Guardando...' : 'Confirmar cita'}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </section>
    </div>
  );
};

export default AgendarCita;
