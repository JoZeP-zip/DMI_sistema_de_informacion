import React from 'react';
import { cld } from '../utils/cloudinary';

/**
 * Muestra una grilla de tarjetas, una por proyecto, usando la primera
 * imagen de cada proyecto (proyecto.imagenes[0]) como portada.
 *
 * Espera recibir:
 *  - proyectos: [{ titulo, descripcion, imagenes: ['public/id1', 'public/id2', ...] }]
 *  - onSelectProject: (proyecto) => void  -> se llama al hacer click en una tarjeta
 */
const CloudinaryGallery = ({ proyectos = [], onSelectProject }) => {
  if (!proyectos.length) {
    return (
      <p className="text-center text-white-50">No hay proyectos para mostrar.</p>
    );
  }

  return (
    <div className="row g-4">
      {proyectos.map((proyecto) => {
        const portadaId = proyecto.imagenes?.[0];

        return (
          <div className="col-12 col-md-6 col-lg-4" key={proyecto.titulo}>
            <div
              role="button"
              tabIndex={0}
              onClick={() => onSelectProject?.(proyecto)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onSelectProject?.(proyecto);
              }}
              className="border border-danger border-opacity-50"
              style={{
                cursor: 'pointer',
                overflow: 'hidden',
                background: '#0a0a0c',
                transition: 'transform .25s ease, box-shadow .25s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(255,47,85,.25)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div style={{ width: '100%', aspectRatio: '4 / 3', overflow: 'hidden', background: '#111' }}>
                {portadaId ? (
                  <img
                    src={cld(portadaId, 'f_auto,q_auto,w_600,h_450,c_fill')}
                    alt={proyecto.titulo}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                    loading="lazy"
                  />
                ) : (
                  <div className="d-flex align-items-center justify-content-center h-100 text-white-50 small">
                    Sin imagen
                  </div>
                )}
              </div>

              <div className="p-3">
                <h5 className="text-white fw-bold mb-1">{proyecto.titulo}</h5>
                {proyecto.descripcion && (
                  <p className="text-white-50 small mb-0" style={{
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}>
                    {proyecto.descripcion}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default CloudinaryGallery;