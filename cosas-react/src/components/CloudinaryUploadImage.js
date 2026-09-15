import React from 'react';
import { cld } from '../utils/cloudinary';

/** Ficha visual de un proyecto Elite con carrusel de imágenes. */
const CloudinaryCarousel = ({ proyecto, isOpen, onClose }) => {
  if (!isOpen || !proyecto) return null;

  const imagenes = proyecto.imagenes || [];

  return (
    <div className="dmi-project-modal-overlay" role="dialog" aria-modal="true" aria-label={`Detalles de ${proyecto.titulo}`}>
      <div className="dmi-project-modal">
        <header className="dmi-project-modal__header">
          <div>
            <span className="dmi-project-modal__eyebrow">PROYECTOS ELITE / DISOL MOTORS</span>
            <h2>Ficha del <span>proyecto</span></h2>
          </div>
          <button type="button" className="dmi-project-modal__close" onClick={onClose} aria-label="Cerrar detalles">×</button>
        </header>

        <div className="dmi-project-modal__body">
          <section className="dmi-project-modal__gallery" aria-label="Galería del proyecto">
            <div id="carouselProjectDetails" className="carousel slide dmi-project-modal__carousel" data-bs-ride="carousel">
              <div className="carousel-inner h-100">
                {imagenes.map((publicId, idx) => (
                  <div key={idx} className={`carousel-item h-100 ${idx === 0 ? 'active' : ''}`}>
                    <img
                      src={cld(publicId, 'w_1000,h_700,c_fill,q_auto,f_auto')}
                      className="d-block w-100 h-100"
                      alt={`${proyecto.titulo} - imagen ${idx + 1}`}
                      loading={idx === 0 ? 'eager' : 'lazy'}
                    />
                  </div>
                ))}
              </div>
              {imagenes.length > 1 && (
                <>
                  <button className="carousel-control-prev dmi-project-modal__arrow" type="button" data-bs-target="#carouselProjectDetails" data-bs-slide="prev" aria-label="Imagen anterior">
                    <span className="carousel-control-prev-icon" aria-hidden="true" />
                  </button>
                  <button className="carousel-control-next dmi-project-modal__arrow" type="button" data-bs-target="#carouselProjectDetails" data-bs-slide="next" aria-label="Siguiente imagen">
                    <span className="carousel-control-next-icon" aria-hidden="true" />
                  </button>
                </>
              )}
            </div>
            <div className="dmi-project-modal__counter"><span /> {imagenes.length} {imagenes.length === 1 ? 'imagen' : 'imágenes'}</div>
          </section>

          <section className="dmi-project-modal__info">
            <span className="dmi-project-modal__tag">PROYECTO DESTACADO</span>
            <h3>{proyecto.titulo}</h3>
            <div className="dmi-project-modal__rule" />
            <p>{proyecto.descripcion || 'Una preparación realizada por el equipo Disol Motors.'}</p>
            {proyecto.detalles && (
              <div className="dmi-project-modal__details">
                <span>DETALLES DEL PROYECTO</span>
                <p>{proyecto.detalles}</p>
              </div>
            )}
            <div className="dmi-project-modal__meta"><span>◈</span> DIAGNÓSTICO · PERFORMANCE · PRECISIÓN</div>
          </section>
        </div>

        <footer className="dmi-project-modal__footer">
          <span>DISOL MOTORS / HIGH PERFORMANCE SERVICE</span>
          <button type="button" onClick={onClose}>CERRAR FICHA <b>→</b></button>
        </footer>
      </div>
    </div>
  );
};

export default CloudinaryCarousel;

