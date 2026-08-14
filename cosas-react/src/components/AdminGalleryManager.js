import React, { useState } from 'react';
import CloudinaryUploadImage from './CloudinaryUploadImage';

/**
 * Componente para que admins gestionen las imágenes de proyectos en Cloudinary
 * Permite subir, listar y actualizar proyectos
 */
const AdminGalleryManager = () => {
  const [proyectos, setProyectos] = useState([
    {
      id: 1,
      titulo: 'Chevrolet Camaro 2018',
      descripcion: 'Optimizacion de software y diagnostico computarizado para flotas empresariales',
      imagenes: [],
      estado: 'activo'
    },
    {
      id: 2,
      titulo: 'Porsche 911 GT3',
      descripcion: 'Calibracion avanzada del sistema de inyeccion electronica',
      imagenes: [],
      estado: 'activo'
    },
    {
      id: 3,
      titulo: 'Lamborghini Aventador',
      descripcion: 'Mantenimiento de alta precision en el sistema de admision',
      imagenes: [],
      estado: 'activo'
    },
  ]);

  const [proyectoSeleccionado, setProyectoSeleccionado] = useState(null);
  const [mensajeNotificacion, setMensajeNotificacion] = useState(null);

  const mostrarMensaje = (tipo, mensaje) => {
    setMensajeNotificacion({ tipo, mensaje });
    setTimeout(() => setMensajeNotificacion(null), 4000);
  };

  const handleUploadSuccess = (data) => {
    if (!proyectoSeleccionado) {
      mostrarMensaje('error', 'Selecciona un proyecto primero');
      return;
    }

    setProyectos(proyectos.map(p => {
      if (p.id === proyectoSeleccionado.id) {
        return {
          ...p,
          imagenes: [...(p.imagenes || []), data.publicId]
        };
      }
      return p;
    }));

    mostrarMensaje('success', `Imagen "${data.fileName}" cargada exitosamente`);
    
    // Actualizar el proyecto seleccionado también
    setProyectoSeleccionado({
      ...proyectoSeleccionado,
      imagenes: [...(proyectoSeleccionado.imagenes || []), data.publicId]
    });
  };

  const handleUploadError = (error) => {
    mostrarMensaje('error', error);
  };

  const eliminarImagen = (imagenId) => {
    setProyectos(proyectos.map(p => {
      if (p.id === proyectoSeleccionado.id) {
        return {
          ...p,
          imagenes: p.imagenes.filter(img => img !== imagenId)
        };
      }
      return p;
    }));

    setProyectoSeleccionado({
      ...proyectoSeleccionado,
      imagenes: proyectoSeleccionado.imagenes.filter(img => img !== imagenId)
    });

    mostrarMensaje('success', 'Imagen eliminada');
  };

  const guardarCambios = () => {
    // Aquí puedes guardar en tu backend
    console.log('Proyectos actualizados:', proyectos);
    mostrarMensaje('success', 'Cambios guardados correctamente');
    // Implementa la llamada a tu API
    // await fetch(`/api/proyectos`, { method: 'POST', body: JSON.stringify(proyectos) })
  };

  const exportarJSON = () => {
    const dataStr = JSON.stringify(proyectos, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'proyectos-cloudinary.json';
    link.click();
  };

  return (
    <div className="admin-gallery-manager" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h2 className="mb-4" style={{ color: '#ff2f55', fontSize: '28px', fontWeight: 'bold' }}>
        Gestor de Galería - Cloudinary
      </h2>

      {/* Notificaciones */}
      {mensajeNotificacion && (
        <div 
          className={`alert mb-4 ${mensajeNotificacion.tipo === 'success' ? 'alert-success' : 'alert-danger'}`}
          style={{ 
            borderLeft: `4px solid ${mensajeNotificacion.tipo === 'success' ? '#28a745' : '#dc3545'}`,
            borderRadius: '4px'
          }}
        >
          {mensajeNotificacion.mensaje}
        </div>
      )}

      <div className="row">
        {/* Panel de Proyectos */}
        <div className="col-lg-4 mb-4">
          <div 
            style={{
              backgroundColor: '#1a1a1a',
              border: '1px solid #ff2f55',
              borderRadius: '8px',
              padding: '20px'
            }}
          >
            <h4 className="text-danger mb-3">Proyectos Disponibles</h4>
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {proyectos.map(proyecto => (
                <div
                  key={proyecto.id}
                  onClick={() => setProyectoSeleccionado(proyecto)}
                  style={{
                    padding: '12px',
                    marginBottom: '8px',
                    backgroundColor: proyectoSeleccionado?.id === proyecto.id ? '#ff2f55' : '#0a0a0a',
                    color: proyectoSeleccionado?.id === proyecto.id ? '#000' : '#fff',
                    border: '1px solid #ff2f55',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    fontSize: '14px'
                  }}
                >
                  <strong>{proyecto.titulo}</strong>
                  <small style={{ display: 'block', marginTop: '4px', opacity: 0.8 }}>
                    {proyecto.imagenes?.length || 0} imagen(es)
                  </small>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Panel de Carga y Gestión */}
        <div className="col-lg-8">
          {proyectoSeleccionado ? (
            <>
              {/* Info del Proyecto */}
              <div 
                style={{
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #ff2f55',
                  borderRadius: '8px',
                  padding: '20px',
                  marginBottom: '20px'
                }}
              >
                <h4 className="text-danger mb-3">Detalles del Proyecto</h4>
                <div className="mb-3">
                  <label className="form-label text-white">Título</label>
                  <input
                    type="text"
                    className="form-control bg-black text-white border-secondary"
                    value={proyectoSeleccionado.titulo}
                    onChange={(e) => setProyectoSeleccionado({
                      ...proyectoSeleccionado,
                      titulo: e.target.value
                    })}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label text-white">Descripción</label>
                  <textarea
                    className="form-control bg-black text-white border-secondary"
                    value={proyectoSeleccionado.descripcion}
                    onChange={(e) => setProyectoSeleccionado({
                      ...proyectoSeleccionado,
                      descripcion: e.target.value
                    })}
                    rows="3"
                  ></textarea>
                </div>
              </div>

              {/* Carga de Imágenes */}
              <div 
                style={{
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #ff2f55',
                  borderRadius: '8px',
                  padding: '20px',
                  marginBottom: '20px'
                }}
              >
                <h4 className="text-danger mb-3">Subir Imágenes</h4>
                <CloudinaryUploadImage
                  onUploadSuccess={handleUploadSuccess}
                  onUploadError={handleUploadError}
                  maxSize={10}
                  multiple={true}
                />
              </div>

              {/* Galería de Imágenes Cargadas */}
              {proyectoSeleccionado.imagenes && proyectoSeleccionado.imagenes.length > 0 && (
                <div 
                  style={{
                    backgroundColor: '#1a1a1a',
                    border: '1px solid #ff2f55',
                    borderRadius: '8px',
                    padding: '20px',
                    marginBottom: '20px'
                  }}
                >
                  <h4 className="text-danger mb-3">
                    Imágenes Cargadas ({proyectoSeleccionado.imagenes.length})
                  </h4>
                  <div className="row g-3">
                    {proyectoSeleccionado.imagenes.map((publicId, idx) => (
                      <div key={idx} className="col-6 col-md-4">
                        <div 
                          style={{
                            position: 'relative',
                            overflow: 'hidden',
                            borderRadius: '8px',
                            border: '1px solid #ff2f55',
                            aspectRatio: '1',
                            backgroundColor: '#0a0a0a'
                          }}
                        >
                          <img
                            src={`https://res.cloudinary.com/${process.env.REACT_APP_CLOUDINARY_CLOUD_NAME}/image/upload/w_400,h_400,c_fill,q_auto/${publicId}`}
                            alt={`Proyecto ${idx}`}
                            style={{
                              width: '100%',
                              height: '100%',
                              objectFit: 'cover'
                            }}
                          />
                          <div
                            style={{
                              position: 'absolute',
                              top: 0,
                              left: 0,
                              right: 0,
                              bottom: 0,
                              backgroundColor: 'rgba(0,0,0,0.7)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              opacity: 0,
                              transition: 'opacity 0.3s',
                              cursor: 'pointer'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                            onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
                          >
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => eliminarImagen(publicId)}
                            >
                              Eliminar
                            </button>
                          </div>
                          
                          {/* Mostrar Public ID */}
                          <div
                            style={{
                              position: 'absolute',
                              bottom: 0,
                              left: 0,
                              right: 0,
                              backgroundColor: 'rgba(0,0,0,0.9)',
                              color: '#fff',
                              padding: '8px',
                              fontSize: '11px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}
                            title={publicId}
                          >
                            {publicId}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Código para copiar */}
              <div 
                style={{
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #ff2f55',
                  borderRadius: '8px',
                  padding: '20px',
                  marginBottom: '20px'
                }}
              >
                <h4 className="text-danger mb-3">Código para App.js</h4>
                <p className="text-muted small mb-2">Copia este código en tu array `proyectos` de App.js:</p>
                <pre
                  style={{
                    backgroundColor: '#0a0a0a',
                    border: '1px solid #333',
                    borderRadius: '4px',
                    padding: '12px',
                    color: '#fff',
                    fontSize: '12px',
                    overflow: 'auto',
                    maxHeight: '200px'
                  }}
                >
{`{
  titulo: '${proyectoSeleccionado.titulo}',
  descripcion: '${proyectoSeleccionado.descripcion}',
  imagenes: [${proyectoSeleccionado.imagenes?.map(id => `'${id}'`).join(', ') || ''}],
}`}
                </pre>
                <button
                  className="btn btn-sm btn-outline-danger mt-2"
                  onClick={() => {
                    const code = `{
  titulo: '${proyectoSeleccionado.titulo}',
  descripcion: '${proyectoSeleccionado.descripcion}',
  imagenes: [${proyectoSeleccionado.imagenes?.map(id => `'${id}'`).join(', ') || ''}],
}`;
                    navigator.clipboard.writeText(code);
                    mostrarMensaje('success', 'Código copiado al portapapeles');
                  }}
                >
                  Copiar Código
                </button>
              </div>

              {/* Botones de Acción */}
              <div className="d-flex gap-2">
                <button
                  className="btn btn-danger fw-bold"
                  onClick={guardarCambios}
                >
                  Guardar Cambios
                </button>
                <button
                  className="btn btn-outline-danger fw-bold"
                  onClick={exportarJSON}
                >
                  Exportar JSON
                </button>
              </div>
            </>
          ) : (
            <div 
              style={{
                backgroundColor: '#1a1a1a',
                border: '2px dashed #ff2f55',
                borderRadius: '8px',
                padding: '40px',
                textAlign: 'center',
                color: '#999'
              }}
            >
              <p>Selecciona un proyecto para comenzar a cargar imágenes</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminGalleryManager;
