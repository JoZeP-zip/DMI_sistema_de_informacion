import React from 'react';
import '../styles/Contacto.css';
import { showDmiSuccess } from './DmiMessages';

const Contacto = () => {
  const handleSubmit = (e) => {
    e.preventDefault();
    showDmiSuccess(
      'Mensaje enviado',
      'Recibimos tu mensaje correctamente. El equipo de Disol Motors se pondra en contacto contigo pronto.'
    );
    e.target.reset();
  };

  const direccion = 'Carrera 2a B, Soacha, Cundinamarca';
  const direccionEncoded = encodeURIComponent(direccion);

  return (
    <section id="contacto" className="section contacto">
      <div className="section-title">
        <h2>Contacto</h2>
        <div className="title-underline"></div>
      </div>

      <div className="contact-container">
        <div className="contact-info">
          <h3>Listo para potenciar tu vehiculo?</h3>
          <p>Visitanos en nuestro taller o agenda una cita directamente.</p>

          <div className="info-item">
            <span className="icon">DM</span>
            <div>
              <h4>Ubicacion</h4>
              <p>{direccion}</p>
            </div>
          </div>

          <div className="info-item">
            <span className="icon">TEL</span>
            <div>
              <h4>Telefono</h4>
              <p>
                <a href="tel:+573133035855">313 303 5855</a><br />
                <a href="tel:+573172423496">317 242 3496</a><br />
                <a href="tel:+573203788941">320 378 8941</a>
              </p>
            </div>
          </div>

          <div className="info-item">
            <span className="icon">@</span>
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
              Escribenos por WhatsApp
            </a>
          </div>
        </div>

        <form className="contact-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <input type="text" placeholder="Nombre completo" required />
          </div>
          <div className="form-group">
            <input type="email" placeholder="Correo electronico" required />
          </div>
          <div className="form-group">
            <select defaultValue="" required>
              <option value="" disabled>Tipo de servicio</option>
              <option value="reprogramacion">Reprogramacion</option>
              <option value="inyeccion">Inyeccion electronica</option>
              <option value="mantenimiento">Mantenimiento general</option>
              <option value="diagnostico">Diagnostico scanner</option>
            </select>
          </div>
          <div className="form-group">
            <textarea placeholder="Cuentanos sobre tu vehiculo o problema..." rows="5" required></textarea>
          </div>
          <button type="submit" className="btn primary large">Enviar mensaje</button>
        </form>
      </div>

      <div className="como-llegar">
        <div className="como-llegar-header">
          <h3>Como llegar</h3>
        </div>
        <div className="como-llegar-body">
          <div className="mapa-wrapper">
            <iframe
              title="Ubicacion Disol Motors"
              className="mapa-embed"
              src={`https://www.google.com/maps?q=${direccionEncoded}&output=embed`}
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            ></iframe>
          </div>
          <div className="mapa-info">
            <div className="info-item">
              <span className="icon">DM</span>
              <div>
                <h4>Direccion</h4>
                <p>{direccion}</p>
              </div>
            </div>
            <div className="info-item">
              <span className="icon">8-6</span>
              <div>
                <h4>Horario</h4>
                <p>Lun - Sab: 8:00 am - 6:00 pm</p>
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
