import React, { useState, useEffect } from 'react';
import '../styles/AgendarCita.css';

const BASE_URL = "https://musical-bassoon-wrx6qgr9gvp9f7v-8800.app.github.dev";

const AgendarCita = () => {
  const [confirmado, setConfirmado]   = useState(false);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState('');
  const [vehiculos, setVehiculos]     = useState([]);

  const [formData, setFormData] = useState({
    vehiculos_idvehiculo: '',
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

  // ── Submit: llama a POST /citas/nueva ───────────────────────────
  const handleCita = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const form = new URLSearchParams(formData);

      const res = await fetch(`${BASE_URL}/citas/nueva`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',   // envía la cookie access_token que guarda FastAPI
        body: form.toString(),
      });

      // FastAPI responde con redirect 302 en éxito — cualquier 2xx/3xx es OK
      if (res.ok || res.status === 302 || res.redirected) {
        setConfirmado(true);
      } else {
        // Intentar leer mensaje de error si el servidor devuelve JSON
        let msg = `Error del servidor (${res.status})`;
        try {
          const data = await res.json();
          msg = data.error || data.detail || msg;
        } catch (_) {}
        setError(msg);
      }
    } catch (err) {
      setError('No se pudo conectar con el servidor. Verifica tu conexión.');
    } finally {
      setLoading(false);
    }
  };

  const handleNuevaCita = () => {
    setConfirmado(false);
    setError('');
    setFormData({
      vehiculos_idvehiculo: '',
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

                <p className="ac-section">Vehículo</p>
                <div className="form-group">
                  <label>Vehículo <span className="ac-req">*</span></label>
                  {vehiculos.length > 0 ? (
                    <select
                      name="vehiculos_idvehiculo"
                      value={formData.vehiculos_idvehiculo}
                      onChange={handleChange}
                      required
                    >
                      <option value="" disabled>Selecciona un vehículo</option>
                      {vehiculos.map(v => (
                        <option key={v.idvehiculo} value={v.idvehiculo}>
                          {v.placa} — {v.marca} {v.modelo || ''}
                        </option>
                      ))}
                    </select>
                  ) : (
                    // Fallback: ingreso manual si no hay vehículos cargados
                    <input
                      type="text"
                      name="vehiculos_idvehiculo"
                      placeholder="ID del vehículo"
                      value={formData.vehiculos_idvehiculo}
                      onChange={handleChange}
                      required
                    />
                  )}
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

                <div className="btn-row">
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={handleNuevaCita}
                    disabled={loading}
                  >
                    ↺ Limpiar
                  </button>
                  <button
                    type="submit"
                    className="btn primary"
                    disabled={loading}
                  >
                    {loading ? 'Enviando...' : '✓ Confirmar cita'}
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