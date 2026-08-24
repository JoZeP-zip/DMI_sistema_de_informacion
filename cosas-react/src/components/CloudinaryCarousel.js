import React from 'react';
import { cld } from '../utils/cloudinary';

/**
 * Componente de Carrusel Modal que muestra imágenes de Cloudinary
 * Optimizado para visualización en full quality
 */
const CloudinaryCarousel = ({ proyecto, isOpen, onClose }) => {
  if (!isOpen || !proyecto) return null;

  return (
    <div className="modal fade show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 1050 }}>
      <div className="modal-dialog modal-dialog-centered modal-lg">
        <div className="modal-content bg-dark text-white border border-danger rounded-0 shadow-lg">
          <div className="modal-header border-bottom border-danger border-opacity-50">
            <h5 className="modal-title fw-black text-uppercase">
              Detalles del <span className="text-danger">Proyecto</span>
            </h5>
            <button 
              type="button" 
              className="btn-close btn-close-white" 
              onClick={onClose}
              aria-label="Cerrar"
            ></button>
          </div>
          
          <div className="modal-body p-4">
            {/* Carrusel de Bootstrap con imágenes optimizadas de Cloudinary */}
            <div id="carouselProjectDetails" className="carousel slide mb-3 border border-secondary" data-bs-ride="carousel" style={{ aspectRatio: '16/9' }}>
              <div className="carousel-inner h-100">
                {proyecto.imagenes?.map((publicId, idx) => {
                  // Construir URL optimizada para display en modal usando el helper cld
                  const imagenUrl = cld(publicId, 'w_800,h_600,c_fill,q_auto,f_auto');
                  
                  return (
                    <div 
                      key={idx} 
                      className={`carousel-item h-100 ${idx === 0 ? 'active' : ''}`}
                    >
                      <img 
                        src={imagenUrl} 
                        className="d-block w-100 h-100" 
                        alt={`${proyecto.titulo} - Imagen ${idx + 1}`}
                        style={{ objectFit: 'cover' }}
                        loading={idx === 0 ? 'eager' : 'lazy'}
                      />
                    </div>
                  );
                })}
              </div>

              {/* Controles del carrusel */}
              {proyecto.imagenes?.length > 1 && (
                <>
                  <button 
                    className="carousel-control-prev" 
                    type="button" 
                    data-bs-target="#carouselProjectDetails" 
                    data-bs-slide="prev"
                    aria-label="Imagen anterior"
                  >
                    <span className="carousel-control-prev-icon" aria-hidden="true"></span>
                  </button>
                  <button 
                    className="carousel-control-next" 
                    type="button" 
                    data-bs-target="#carouselProjectDetails" 
                    data-bs-slide="next"
                    aria-label="Siguiente imagen"
                  >
                    <span className="carousel-control-next-icon" aria-hidden="true"></span>
                  </button>
                </>
              )}
            </div>

            {/* Información del proyecto */}
            <h4 className="fw-bold text-uppercase tracking-wider mb-2 text-danger">
              {proyecto.titulo}
            </h4>
            <p className="text-muted small mb-0">
              {proyecto.descripcion}
            </p>

            {/* Información adicional */}
            {proyecto.detalles && (
              <div className="mt-3 pt-3 border-top border-danger border-opacity-25">
                <small className="text-muted d-block">
                  <strong>Imágenes:</strong> {proyecto.imagenes?.length || 0}
                </small>
              </div>
            )}
          </div>

          <div className="modal-footer border-top border-danger border-opacity-25">
            <button 
              type="button" 
              className="btn btn-danger rounded-0 fw-bold px-4" 
              onClick={onClose}
            >
              CERRAR
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CloudinaryCarousel;