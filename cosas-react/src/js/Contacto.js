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
        <span className="contacto-kicker">Hablemos</span>
        <h2 className="contacto-title">Contacto</h2>
        <div className="title-underline"></div>
        <p className="contacto-lead"><strong>Escribenos</strong> y con gusto resolvemos tus dudas o te contamos mas sobre nuestros servicios.</p>
      </div>

      <div className="contact-container">
        <div className="contact-info">
          <div className="info-item">
            <span className="info-index">01</span>
            <span className="icon">DM</span>
            <div>
              <h4>Ubicacion</h4>
              <p>{direccion}</p>
            </div>
          </div>

          <div className="info-item">
            <span className="info-index">02</span>
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
            <span className="info-index">03</span>
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
            <textarea placeholder="Cuentanos sobre tu vehiculo o problema..." rows="6" required></textarea>
          </div>
          <button type="submit" className="btn primary large">Enviar mensaje</button>
          <span className="contacto-form-note">Respondemos en menos de 24 horas habiles.</span>
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
            <span className="mapa-overlay-kicker">Como llegar</span>

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