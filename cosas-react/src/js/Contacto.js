import React from 'react';
import '../styles/Contacto.css';

const Contacto = () => {
  const handleSubmit = (e) => {
    e.preventDefault();
    alert("¡Mensaje enviado a Disol Motors! Nos pondremos en contacto pronto.");
    e.target.reset(); // Limpia el formulario después de enviar
  };

  const direccion = "Carrera 2a B, Soacha, Cundinamarca";
  const direccionEncoded = encodeURIComponent(direccion);

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
          <h3>¿Listo para potenciar tu vehiculo?</h3>
          <p>Visítanos en nuestro taller o agenda una cita directamente.</p>

          <div className="info-item">
            <span className="icon">📍</span>
            <div>
              <h4>Ubicación</h4>
              <p>{direccion}</p>
            </div>
          </div>

          <div className="info-item">
            <span className="icon">📞</span>
            <div>
              <h4>Teléfono</h4>
              <p>
                <a href="tel:+573133035855">313 303 5855</a><br />
                <a href="tel:+573172423496">317 242 3496</a><br />
                <a href="tel:+573203788941">320 378 8941</a>
              </p>
            </div>
          </div>

          <div className="info-item">
            <span className="icon">✉️</span>
            <div>
              <h4>Email</h4>
              <p>contacto@disolmotors.com</p>
            </div>
          </div>

          <div className="whatsapp-row">
            <a
              className="btn-whatsapp"
              href="https://wa.me/573133035855"
              target="_blank"
              rel="noopener noreferrer"
            >
              Escríbenos por WhatsApp
            </a>
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

      {/* Cómo llegar */}
      <div className="como-llegar">
        <div className="como-llegar-header">
          <h3>Cómo llegar</h3>
        </div>
        <div className="como-llegar-body">
          <div className="mapa-wrapper">
            <iframe
              title="Ubicación Disol Motors"
              className="mapa-embed"
              src={`https://www.google.com/maps?q=${direccionEncoded}&output=embed`}
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            ></iframe>
          </div>
          <div className="mapa-info">
            <div className="info-item">
              <span className="icon">📍</span>
              <div>
                <h4>Dirección</h4>
                <p>{direccion}</p>
              </div>
            </div>
            <div className="info-item">
              <span className="icon">🕒</span>
              <div>
                <h4>Horario</h4>
                <p>Lun - Sáb: 8:00 am - 6:00 pm</p>
              </div>
            </div>
            <a
              className="btn-maps"
              href={`https://www.google.com/maps/dir/?api=1&destination=${direccionEncoded}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              Abrir en Google Maps
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Contacto;