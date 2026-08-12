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
      <div className="section-title contact-hero">
        <h2 className="contacto-title">Estamos para <span>ayudarte</span></h2>
        <p className="contacto-lead">¿Tienes dudas, necesitas una cotización o quieres agendar una revisión? <strong>Escríbenos o llámanos</strong>; nuestro equipo te orientará.</p>
        <div className="contact-hero-actions">
          <a className="contact-hero-button primary" href="https://wa.me/573133035855" target="_blank" rel="noopener noreferrer">WhatsApp directo</a>
          <a className="contact-hero-button" href={`https://www.google.com/maps/dir/?api=1&destination=${direccionEncoded}`} target="_blank" rel="noopener noreferrer">Cómo llegar</a>
        </div>
      </div>

      <div className="contact-container">
        <aside className="contact-info">
          <div className="panel-heading">
            <span>01 / Contacto</span>
            <h3>Hablemos hoy</h3>
            <p>Elige el medio que te resulte más cómodo.</p>
          </div>
          <div className="info-item">
            <span className="info-index">01</span>
            <span className="icon" aria-hidden="true">⌖</span>
            <div>
              <h4>Ubicacion</h4>
              <p><a href={`https://www.google.com/maps/dir/?api=1&destination=${direccionEncoded}`} target="_blank" rel="noopener noreferrer">{direccion}</a></p>
            </div>
          </div>

          <div className="info-item">
            <span className="info-index">02</span>
            <span className="icon" aria-hidden="true">☎</span>
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
            <span className="info-index">03</span>
            <span className="icon" aria-hidden="true">✉</span>
            <div>
              <h4>Email</h4>
              <p><a href="mailto:contacto@disolmotors.com">contacto@disolmotors.com</a></p>
            </div>
          </div>

          <div className="whatsapp-row">
            <a className="btn-whatsapp"
              href="https://wa.me/573133035855"
              target="_blank"
              rel="noopener noreferrer"
            >
              Abrir WhatsApp
            </a>
          </div>
        </aside>

        <form className="contact-form" onSubmit={handleSubmit}>
          <div className="form-heading">
            <span>02 / Mensaje</span>
            <h3>Cuéntanos qué necesitas</h3>
            <p>Déjanos tus datos y te responderemos lo antes posible.</p>
          </div>
          <div className="contact-form-grid">
          <div className="form-group">
            <label htmlFor="contact-name">Nombre completo</label>
            <input id="contact-name" type="text" placeholder="Ej. Camilo Pérez" required />
          </div>
          <div className="form-group">
            <label htmlFor="contact-email">Correo electrónico</label>
            <input id="contact-email" type="email" placeholder="nombre@correo.com" required />
          </div>
          <div className="form-group">
            <label htmlFor="contact-phone">Teléfono <em>(opcional)</em></label>
            <input id="contact-phone" type="tel" placeholder="Tu número de contacto" />
          </div>
          <div className="form-group">
            <label htmlFor="contact-subject">Asunto</label>
            <input id="contact-subject" type="text" placeholder="Ej. Cotización de reparación" />
          </div>
          </div>
          <div className="form-group">
            <label htmlFor="contact-message">Mensaje</label>
            <textarea id="contact-message" placeholder="Cuéntanos sobre tu vehículo, el servicio que buscas o tu inquietud..." rows="6" required></textarea>
          </div>
          <div className="contact-form-footer">
            <span className="contacto-form-note">◷ Respondemos en menos de 24 horas hábiles.</span>
            <button type="submit" className="btn primary large">Enviar mensaje <span>→</span></button>
          </div>
        </form>
      </div>

      <div className="como-llegar">
        <div className="mapa-wrapper">
          <iframe
            title="Ubicacion Disol Motors"
            className="mapa-embed"
            src={`https://www.google.com/maps?q=${direccionEncoded}&output=embed`}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          ></iframe>

          <div className="mapa-overlay-card">
            <span className="mapa-overlay-kicker">03 / Visítanos</span>
            <h3>Encuentra el taller</h3>

            <div className="info-item">
              <span className="icon" aria-hidden="true">⌖</span>
              <div>
                <h4>Direccion</h4>
                <p>{direccion}</p>
              </div>
            </div>
            <div className="info-item">
              <span className="icon" aria-hidden="true">◷</span>
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
