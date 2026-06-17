import React, { useState, useEffect } from 'react';

const DashboardAdmin = () => {
  const [stats, setStats] = useState({ citas_pendientes: 0, total_vehiculos: 0, total_usuarios: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('https://musical-bassoon-wrx6qgr9gvp9f7v-8800.app.github.dev/admin/stats', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
      .then(res => res.json())
      .then(data => { setStats(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div>
      <h3 className="text-uppercase fw-black border-bottom border-danger pb-2 mb-4">
        Panel de <span className="text-danger">Administración</span>
      </h3>
      <p className="text-muted">Bienvenido al centro de control de Disol Motors.</p>
      
      {loading ? (
        <p className="text-muted">Cargando estadísticas...</p>
      ) : (
        <>
          {/* Tarjetas de Estadísticas */}
          <div className="row g-3 mt-2">
            <div className="col-md-4">
              <div className="p-3 bg-black border border-secondary text-center">
                <h5 className="text-danger fw-bold">{stats.citas_pendientes}</h5>
                <small className="text-muted">CITAS PENDIENTES</small>
              </div>
            </div>
            <div className="col-md-4">
              <div className="p-3 bg-black border border-secondary text-center">
                <h5 className="text-danger fw-bold">{stats.total_vehiculos}</h5>
                <small className="text-muted">UNIDADES REGISTRADAS</small>
              </div>
            </div>
            <div className="col-md-4">
              <div className="p-3 bg-black border border-secondary text-center">
                <h5 className="text-danger fw-bold">{stats.total_usuarios}</h5>
                <small className="text-muted">USUARIOS REGISTRADOS</small>
              </div>
            </div>
          </div>

          {/* Sección de Acciones de Control */}
          <div className="mt-5">
            <h5 className="text-uppercase fw-bold text-muted mb-3 tracking-widest small">
              Gestión del Taller
            </h5>
            <div className="row g-3">
              <div className="col-md-6">
                <div className="p-4 bg-black border border-danger border-opacity-50 h-100 d-flex flex-column justify-content-between">
                  <div>
                    <h6 className="fw-bold text-uppercase text-white">Calendario de Citas</h6>
                    <p className="text-muted small">Revisa las solicitudes de mantenimiento y asigna los horarios disponibles.</p>
                  </div>
                  <button className="btn btn-outline-danger rounded-0 btn-sm w-100 fw-bold mt-2">
                    VER AGENDA DE CITAS
                  </button>
                </div>
              </div>
              <div className="col-md-6">
                <div className="p-4 bg-black border border-danger border-opacity-50 h-100 d-flex flex-column justify-content-between">
                  <div>
                    <h6 className="fw-bold text-uppercase text-white">Inventario de Unidades</h6>
                    <p className="text-muted small">Controla los vehículos que se encuentran actualmente en diagnóstico o reparación.</p>
                  </div>
                  <button className="btn btn-outline-danger rounded-0 btn-sm w-100 fw-bold mt-2">
                    GESTIONAR VEHÍCULOS
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DashboardAdmin;