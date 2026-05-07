import React from 'react';
import './Contacto.css';

const Contacto = () => {
  const handleSubmit = (e) => {
    e.preventDefault();
    alert("¡Mensaje enviado a Disol Motors! Nos pondremos en contacto pronto.");
    e.target.reset(); // Limpia el formulario después de enviar
  };

  return (
    /* El ID es fundamental para que el botón de App.js sepa a dónde bajar */
    <section id="contacto" className="section contacto">
      <div className="section-title">
        <h2>Contacto</h2>
        <div className="title-underline"></div>
      </div>

      <div className="contact-container">
        {/* Información de la Empresa */}
        <div className="contact-info">
          <h3>¿Listo para potenciar tu motor?</h3>
          <p>Visítanos en nuestro taller o agenda una cita directamente.</p>
          
          <div className="info-item">
            <span className="icon">📍</span>
            <div>
              <h4>Ubicación</h4>
              <p>Av. Principal de Motores #123, Sector Industrial</p>
            </div>
          </div>

          <div className="info-item">
            <span className="icon">📞</span>
            <div>
              <h4>Teléfono</h4>
              <p>+57 300 123 4567</p>
            </div>
          </div>

          <div className="info-item">
            <span className="icon">✉️</span>
            <div>
              <h4>Email</h4>
              <p>contacto@disolmotors.com</p>
            </div>
          </div>
        </div>

        {/* Formulario */}
        <form className="contact-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <input type="text" placeholder="Nombre Completo" required />
          </div>
          <div className="form-group">
            <input type="email" placeholder="Correo Electrónico" required />
          </div>
          <div className="form-group">
            {/* Usamos defaultValue para que React no lance warnings */}
            <select defaultValue="" required>
              <option value="" disabled>Tipo de Servicio</option>
              <option value="reprogramacion">Reprogramación (Tuning)</option>
              <option value="inyeccion">Inyección Electrónica</option>
              <option value="mantenimiento">Mantenimiento General</option>
              <option value="diagnostico">Diagnóstico Scanner</option>
            </select>
          </div>
          <div className="form-group">
            <textarea placeholder="Cuéntanos sobre tu vehículo o problema..." rows="5" required></textarea>
          </div>
          <button type="submit" className="btn primary large">Enviar Mensaje</button>
        </form>
      </div>
    </section>
  );
};

export default Contacto;