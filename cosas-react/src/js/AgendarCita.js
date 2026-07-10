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

const AgendarCita = () => {
  const [confirmado, setConfirmado] = useState(false);
  const [vehiculos, setVehiculos] = useState([]);   
  const [error, setError] = useState('');        // eslint-disable-line        
  const [loading, setLoading] = useState(false); // eslint-disable-line    
  const [formData, setFormData] = useState({
    vehiculos_idvehiculo: '',
    descripcion_vehiculo: '',
    fecha_cita: '',
    hora_cita: '',
    motivo: '',
    observaciones: '',
  });

  // ── Cargar vehículos disponibles al montar ──────────────────────
  useEffect(() => {
    fetch(`${BASE_URL}/api/vehiculos`)
      .then(res => res.json())
      .then(data => setVehiculos(Array.isArray(data) ? data : []))
      .catch(() => setVehiculos([]));
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleCita = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
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
  };

  return (
    <div className="agendar-cita-wrapper">
      <section className="section agendar-cita">
        <div className="section-title">
          <div className="ac-icon-row">
            <div className="ac-icon-box">📅</div>
            <div className="ac-icon-box">🚗</div>
          </div>
          <h2>Agendar Cita</h2>
          <p>Disol Motors — Reserva tu servicio</p>
        </div>

        <div className="cita-card">
          {confirmado ? (
            <div className="cita-confirmada">
              <div className="success-icon">✅</div>
              <h2>¡Cita agendada!</h2>
              <p>
                Te esperamos en <span className="highlight">Disol Motors</span>.<br />
                Hemos registrado tu cita exitosamente.
              </p>
              <div className="btn-row" style={{ justifyContent: 'center' }}>
                <button className="btn primary" onClick={handleNuevaCita}>
                  + Agendar otra
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="cita-card-head">
                <div className="cita-head-icon">📋</div>
                <p className="cita-head-title">Datos de la cita</p>
              </div>

              {/* Mensaje de error */}
              {error && (
                <div className="alert alert-danger small py-2 rounded-0 border-danger bg-black text-danger mb-3">
                  ⚠️ {error}
                </div>
              )}

              <form className="cita-form" onSubmit={handleCita}>

                <p className="ac-section">Vehiculo</p>
                {vehiculos.length > 0 && (
                  <div className="form-group">
                    <label>Vehiculo registrado (opcional)</label>
                    <select
                      name="vehiculos_idvehiculo"
                      value={formData.vehiculos_idvehiculo}
                      onChange={handleChange}
                    >
                      <option value="">Usar descripcion del cliente</option>
                      {vehiculos.map(v => (
                        <option key={v.idvehiculo} value={v.idvehiculo}>
                          {v.placa} - {v.marca} {v.modelo || ''}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="form-group">
                  <label>Descripcion del vehiculo <span className="ac-req">*</span></label>
                  <textarea
                    name="descripcion_vehiculo"
                    placeholder="Ejemplo: Renault Logan 2012, falla al encender, ruido en motor..."
                    value={formData.descripcion_vehiculo}
                    onChange={handleChange}
                    rows={3}
                    required
                  />
                </div>

                <p className="ac-section">Programación</p>
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
                    <label>Hora <span className="ac-req">*</span></label>
                    <input
                      type="time"
                      name="hora_cita"
                      min="08:00"
                      max="18:00"
                      value={formData.hora_cita}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>

                <p className="ac-section">Servicio</p>
                <div className="form-group">
                  <label>Motivo <span className="ac-req">*</span></label>
                  <select
                    name="motivo"
                    value={formData.motivo}
                    onChange={handleChange}
                    required
                  >
                    <option value="" disabled>Selecciona el motivo</option>
                    <option value="diagnostico">Diagnóstico computarizado</option>
                    <option value="repro">Reprogramación de ECU</option>
                    <option value="mecanica">Mecánica general</option>
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

                {error && (
                  <p style={{ color: '#e53e3e', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                    ⚠️ {error}
                  </p>
                )}

                <div className="btn-row">
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={handleNuevaCita}
                    disabled={loading}
                  >
                    ↺ Limpiar
                  </button>
                  <button type="submit" className="btn primary" disabled={loading}>
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
