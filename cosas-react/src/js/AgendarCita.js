import React, { useState } from 'react';
import '../styles/AgendarCita.css';

const AgendarCita = () => {
  const [confirmado, setConfirmado] = useState(false);
  const [formData, setFormData] = useState({
    vehiculo: '', fecha: '', hora: '', motivo: '', observacion: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleCita = (e) => {
    e.preventDefault();
    setConfirmado(true);
  };

  const handleNuevaCita = () => {
    setConfirmado(false);
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

                <div className="btn-row">
                  <button type="button" className="btn secondary" onClick={handleNuevaCita}>
                    ↺ Limpiar
                  </button>
                  <button type="submit" className="btn primary">
                    ✓ Confirmar cita
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