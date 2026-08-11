import React from 'react';
import '../styles/Contacto.css';
import { showDmiSuccess } from './DmiMessages';

/* =========================================================
   ICONOS SVG
========================================================= */

const LocationIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 21s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12Z" />
    <circle cx="12" cy="9" r="2.5" />
  </svg>
);

const PhoneIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M6.5 3.5 9 3l2 5-2 1.7c1 2.1 2.7 3.8 4.8 4.8l1.7-2 5 2-.5 2.5c-.3 1.5-1.6 2.5-3.1 2.5C10.2 19.5 4.5 13.8 4.5 7.1c0-1.5 1-2.8 2-3.6Z" />
  </svg>
);

const EmailIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="3" y="5" width="18" height="14" rx="1.5" />
    <path d="m4 7 8 6 8-6" />
  </svg>
);

const WhatsappIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M20.5 11.2a8.4 8.4 0 0 1-12.7 7.2L4 20l1.7-3.7a8.4 8.4 0 1 1 14.8-5.1Z" />
    <path d="M9 8.5c.2-.4.4-.5.7-.5h.7c.2 0 .4.1.5.4l.8 1.8c.1.2.1.4-.1.6l-.6.7c.6 1.1 1.5 2 2.6 2.6l.7-.6c.2-.2.4-.2.6-.1l1.8.8c.3.1.4.3.4.5v.7c0 .3-.1.5-.5.7-.5.2-1.1.2-1.6 0-1.5-.5-2.8-1.4-3.9-2.5s-2-2.4-2.5-3.9c-.2-.5-.2-1.1 0-1.6Z" />
  </svg>
);

const UserIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="8" r="3" />
    <path d="M5 20c.8-3.2 3.1-5 7-5s6.2 1.8 7 5" />
  </svg>
);

const MessageIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 5h16v11H8l-4 3V5Z" />
    <path d="M8 9h8M8 12h5" />
  </svg>
);

const TagIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="m4 4 8-.5L20.5 12 12 20.5 3.5 12 4 4Z" />
    <circle cx="8" cy="8" r="1.2" />
  </svg>
);

const ClockIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7v5l3 2" />
  </svg>
);

const MapIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="m4 5 6-2 8 2 2-1v15l-6 2-8-2-2 1V5Z" />
    <path d="M10 3v16M18 5v16" />
  </svg>
);

/* =========================================================
   COMPONENTE CONTACTO
========================================================= */

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

      {/* =====================================================
          HERO
      ===================================================== */}

      <div className="contact-hero">

        <div className="contact-hero-content">

          <span className="contact-hero-kicker">
            Hablemos
          </span>

          <h1 className="contact-hero-title">
            Estamos para
            <span>ayudarte</span>
          </h1>

          <p className="contact-hero-text">
            ¿Tienes dudas, necesitas asesoría o quieres más información?
            En <strong>Disol Motors</strong> estamos listos para ayudarte.
          </p>

          <div className="contact-hero-line"></div>

        </div>

      </div>


      {/* =====================================================
          CONTENEDOR PRINCIPAL
      ===================================================== */}

      <div className="contact-container">

        {/* ===================================================
            INFORMACIÓN DE CONTACTO
        =================================================== */}

        <div className="contact-info">

          <h3 className="contact-panel-title">
            Nuestras vías de contacto
          </h3>


          {/* UBICACIÓN */}

          <div className="info-item">

            <span className="info-index">
              01
            </span>

            <span className="icon">
              <LocationIcon />
            </span>

            <div>

              <h4>
                Ubicación
              </h4>

              <p>
                {direccion}
              </p>

            </div>

          </div>


          {/* TELÉFONOS */}

          <div className="info-item">

            <span className="info-index">
              02
            </span>

            <span className="icon">
              <PhoneIcon />
            </span>

            <div>

              <h4>
                Teléfonos
              </h4>

              <p>

                <a href="tel:+573133035855">
                  313 303 5855
                </a>

                <br />

                <a href="tel:+573172423496">
                  317 242 3496
                </a>

                <br />

                <a href="tel:+573203788941">
                  320 378 8941
                </a>

              </p>

            </div>

          </div>


          {/* CORREO */}

          <div className="info-item">

            <span className="info-index">
              03
            </span>

            <span className="icon">
              <EmailIcon />
            </span>

            <div>

              <h4>
                Correo electrónico
              </h4>

              <p>

                <a href="mailto:contacto@disolmotors.com">
                  contacto@disolmotors.com
                </a>

              </p>

            </div>

          </div>


          {/* WHATSAPP */}

          <div className="info-item">

            <span className="info-index">
              04
            </span>

            <span className="icon">
              <WhatsappIcon />
            </span>

            <div>

              <h4>
                WhatsApp
              </h4>

              <p>
                Atención rápida y personalizada.
              </p>

            </div>

          </div>


          {/* BOTÓN WHATSAPP */}

          <div className="whatsapp-row">

            <a
              className="btn-whatsapp"
              href="https://wa.me/573133035855"
              target="_blank"
              rel="noopener noreferrer"
            >

              <WhatsappIcon />

              <span>
                Escribenos por WhatsApp
              </span>

            </a>

          </div>

        </div>


        {/* ===================================================
            FORMULARIO
        ===================================================== */}

        <form
          className="contact-form"
          onSubmit={handleSubmit}
        >

          <div className="contact-form-header">

            <h3>
              Envíanos un mensaje
            </h3>

            <p>
              Completa la información y cuéntanos cómo podemos ayudarte.
            </p>

          </div>


          <div className="contact-form-fields">

            {/* NOMBRE */}

            <div className="form-group">

              <div className="input-wrapper">

                <UserIcon />

                <input
                  type="text"
                  name="nombre"
                  placeholder="Nombre completo"
                  autoComplete="name"
                  required
                />

              </div>

            </div>


            {/* CORREO */}

            <div className="form-group">

              <div className="input-wrapper">

                <EmailIcon />

                <input
                  type="email"
                  name="correo"
                  placeholder="Correo electrónico"
                  autoComplete="email"
                  required
                />

              </div>

            </div>


            {/* TELÉFONO */}

            <div className="form-group">

              <div className="input-wrapper">

                <PhoneIcon />

                <input
                  type="tel"
                  name="telefono"
                  placeholder="Teléfono (opcional)"
                  autoComplete="tel"
                />

              </div>

            </div>


            {/* ASUNTO */}

            <div className="form-group">

              <div className="input-wrapper">

                <TagIcon />

                <input
                  type="text"
                  name="asunto"
                  placeholder="Asunto"
                />

              </div>

            </div>


            {/* MENSAJE */}

            <div className="form-group full">

              <div className="textarea-wrapper">

                <MessageIcon />

                <textarea
                  name="mensaje"
                  placeholder="Cuéntanos sobre tu vehículo o problema..."
                  rows="6"
                  required
                ></textarea>

              </div>

            </div>

          </div>


          {/* BOTÓN ENVIAR */}

          <button
            type="submit"
            className="btn primary large"
          >

            <span className="send-icon">
              ➤
            </span>

            Enviar mensaje

          </button>


          <span className="contacto-form-note">
            Respondemos en menos de 24 horas hábiles.
          </span>

        </form>

      </div>


      {/* =====================================================
          MAPA
      ===================================================== */}

      <div className="como-llegar">

        <div className="mapa-wrapper">

          <iframe
            title="Ubicacion Disol Motors"
            className="mapa-embed"
            src={`https://www.google.com/maps?q=${direccionEncoded}&output=embed`}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          ></iframe>


          {/* TARJETA DEL MAPA */}

          <div className="mapa-overlay-card">

            <span className="mapa-overlay-kicker">
              Visítanos
            </span>


            {/* DIRECCIÓN */}

            <div className="info-item">

              <span className="icon">
                <LocationIcon />
              </span>

              <div>

                <h4>
                  Disol Motors
                </h4>

                <p>
                  {direccion}
                </p>

              </div>

            </div>


            {/* HORARIO */}

            <div className="info-item">

              <span className="icon">
                <ClockIcon />
              </span>

              <div>

                <h4>
                  Horario
                </h4>

                <p>
                  Lun - Sab: 8:00 am - 6:00 pm
                </p>

              </div>

            </div>


            {/* GOOGLE MAPS */}

            <a
              className="btn-maps"
              href={`https://www.google.com/maps/dir/?api=1&destination=${direccionEncoded}`}
              target="_blank"
              rel="noopener noreferrer"
            >

              <MapIcon />

              <span>
                Abrir en Google Maps
              </span>

            </a>

          </div>


          {/* ETIQUETA DEL MAPA */}

          <div className="mapa-label">
            UBICACIÓN DISOL MOTORS
          </div>

        </div>

      </div>

    </section>
  );
};

export default Contacto;