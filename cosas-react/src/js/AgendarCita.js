import React, { useState } from 'react';
import '../styles/AgendarCita.css';

const AgendarCita = ({ onNeedLogin }) => {  // ← recibe función del padre
  const [confirmado, setConfirmado] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    vehiculo: '', fecha: '', hora: '', motivo: '', observacion: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleCita = async (e) => {
    e.preventDefault();

    // 🔒 Verificar si el usuario está logueado
    const token = localStorage.getItem('token');
    if (!token) {
      onNeedLogin(); // ← avisa al App.js que mande al login
      return;
    }

    setCargando(true);
    setError(null);

    try {
      const resVehiculo = await fetch(
        `http://localhost:8800/vehiculos/placa/${formData.vehiculo}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      if (!resVehiculo.ok) throw new Error('No se encontró un vehículo con esa placa');
      const vehiculo = await resVehiculo.json();

      const resCita = await fetch('http://localhost:8800/citas', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          vehiculos_idvehiculo: vehiculo.idvehiculo,
          fecha: formData.fecha,
          hora: formData.hora,
          motivo: formData.motivo,
          estado: 'pendiente',
          notas: formData.observacion,
        }),
      });
      if (!resCita.ok) throw new Error('Error al agendar la cita, intenta de nuevo');

      setConfirmado(true);

    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  const handleNuevaCita = () => {
    setConfirmado(false);
    setError(null);
    setFormData({ vehiculo: '', fecha: '', hora: '', motivo: '', observacion: '' });
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
              <p>Te esperamos en <span className="highlight">Disol Motors</span>.<br />Hemos registrado tu cita exitosamente.</p>
              <div className="btn-row" style={{ justifyContent: 'center' }}>
                <button className="btn primary" onClick={handleNuevaCita}>+ Agendar otra</button>
              </div>
            </div>
          ) : (
            <>
              <div className="cita-card-head">
                <div className="cita-head-icon">📋</div>
                <p className="cita-head-title">Datos de la cita</p>
              </div>
              <form className="cita-form" onSubmit={handleCita}>
                <p className="ac-section">Vehículo</p>
                <div className="form-group">
                  <label>Placa <span className="ac-req">*</span></label>
                  <input type="text" name="vehiculo" placeholder="Ej: ABC-123"
                    value={formData.vehiculo} onChange={handleChange} required />
                </div>

                <p className="ac-section">Programación</p>
                <div className="form-row">
                  <div className="form-group no-mb">
                    <label>Fecha <span className="ac-req">*</span></label>
                    <input type="date" name="fecha" value={formData.fecha}
                      onChange={handleChange} required />
                  </div>
                  <div className="form-group no-mb">
                    <label>Hora <span className="ac-req">*</span></label>
                    <input type="time" name="hora" min="08:00" max="18:00"
                      value={formData.hora} onChange={handleChange} required />
                  </div>
                </div>

                <p className="ac-section">Servicio</p>
                <div className="form-group">
                  <label>Motivo <span className="ac-req">*</span></label>
                  <select name="motivo" value={formData.motivo} onChange={handleChange} required>
                    <option value="" disabled>Selecciona el motivo</option>
                    <option value="diagnostico">Diagnóstico computarizado</option>
                    <option value="repro">Reprogramación de ECU</option>
                    <option value="mecanica">Mecánica general</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Observación</label>
                  <textarea name="observacion" placeholder="Describe el problema o detalle adicional..."
                    value={formData.observacion} onChange={handleChange} rows={4} />
                </div>

                {error && (
                  <p style={{ color: '#e53e3e', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                    ⚠️ {error}
                  </p>
                )}

                <div className="btn-row">
                  <button type="button" className="btn secondary" onClick={handleNuevaCita}>
                    ↺ Limpiar
                  </button>
                  <button type="submit" className="btn primary" disabled={cargando}>
                    {cargando ? '⏳ Agendando...' : '✓ Confirmar cita'}
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