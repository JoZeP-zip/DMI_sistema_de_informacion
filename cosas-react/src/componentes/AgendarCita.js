import React, { useState } from 'react';
import './AgendarCita.css';
const AgendarCita = () => {
  const [confirmado, setConfirmado] = useState(false);

  const handleCita = (e) => {
    e.preventDefault();
    setConfirmado(true);
    // Aquí podrías conectar luego con tu base de datos
  };

  if (confirmado) {
    return (
      <div className="cita-confirmada">
        <h2>¡Cita Agendada!</h2>
        <p>Te esperamos en Disol Motors. Hemos enviado los detalles a tu correo.</p>
        <button className="btn primary" onClick={() => setConfirmado(false)}>Agendar otra</button>
      </div>
    );
  }

  return (
    <section className="section agendar-cita">
      <div className="section-title">
        <h2>Agendar Cita</h2>
        <div className="title-underline"></div>
      </div>

      <form className="cita-form" onSubmit={handleCita}>
        <div className="form-row">
          <div className="form-group">
            <label>Fecha</label>
            <input type="date" required />
          </div>
          <div className="form-group">
            <label>Hora</label>
            <input type="time" min="08:00" max="18:00" required />
          </div>
        </div>

        <div className="form-group">
          <input type="text" placeholder="Placa del Vehículo" required />
        </div>

        <div className="form-group">
          <select defaultValue="">
            <option value="" disabled>Selecciona el motivo</option>
            <option value="diagnostico">Diagnóstico Computarizado</option>
            <option value="repro">Reprogramación de ECU</option>
            <option value="mecanica">Mecánica General</option>
          </select>
        </div>

        <button type="submit" className="btn primary large">Confirmar Cita</button>
      </form>
    </section>
  );
};

export default AgendarCita;