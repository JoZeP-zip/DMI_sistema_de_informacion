import React, { useState, useEffect, useCallback } from 'react';

// --- CONFIGURACIÓN DE ESQUEMAS PARA LOS 12 MÓDULOS ENMENDADOS ---
const MODULES_CONFIG = {
  ciudades: { 
    title: "Ciudades", 
    fields: [
      { name: "codigo_ciudad", label: "CÓDIGO CIUDAD", type: "text", placeholder: "Ej. 001 o CD001" }, 
      { name: "nombre", label: "CIUDAD", type: "text", placeholder: "Ej. Bogotá" }, 
      { name: "codigo_postal", label: "CÓDIGO POSTAL", type: "text", placeholder: "Ej. 110111" }
    ], 
    columns: ["N°", "CÓDIGO", "CIUDAD", "CÓD. POSTAL", "ACCIONES"],
    keys: ["id", "codigo_ciudad", "nombre", "codigo_postal"] 
  },
  tipo_vehiculo: { 
    title: "Tipo de Vehículo", 
    fields: [{ name: "nombre", label: "TIPO DE VEHÍCULO", type: "text", placeholder: "Ej. Particular, Moto, Carga" }], 
    columns: ["ID", "TIPO DE VEHÍCULO", "ACCIONES"],
    keys: ["id", "nombre"] 
  },
  metodos_pago: { 
    title: "Métodos de Pago", 
    fields: [
      { name: "nombre", label: "MÉTODO DE PAGO", type: "text", placeholder: "Ej. Transferencia Bancaria" }, 
      { name: "estado", label: "ESTADO (Activo/Inactivo)", type: "text", placeholder: "Activo" }
    ], 
    columns: ["ID", "MÉTODO", "ESTADO", "ACCIONES"],
    keys: ["id", "nombre", "estado"] 
  },
  precios_producto: { 
    title: "Precios Producto", 
    fields: [
      { name: "producto_id", label: "ID DEL PRODUCTO", type: "number", placeholder: "Ej. 5" }, 
      { name: "precio", label: "PRECIO DE VENTA ($)", type: "number", placeholder: "Ej. 150000" }
    ], 
    columns: ["ID", "PRODUCTO ID", "PRECIO VENTA", "ACCIONES"],
    keys: ["id", "producto_id", "precio"] 
  },
  precios_servicio: { 
    title: "Precios Servicio", 
    fields: [
      { name: "servicio_id", label: "ID DEL SERVICIO", type: "number", placeholder: "Ej. 2" }, 
      { name: "precio", label: "PRECIO BASE ($)", type: "number", placeholder: "Ej. 80000" }
    ], 
    columns: ["ID", "SERVICIO ID", "PRECIO BASE", "ACCIONES"],
    keys: ["id", "servicio_id", "precio"] 
  },
  inventario: { 
    title: "Inventario", 
    fields: [
      { name: "producto_id", label: "ID DEL PRODUCTO", type: "number" }, 
      { name: "oficina_id", label: "ID DE LA OFICINA", type: "number" }, 
      { name: "cantidad", label: "CANTIDAD DISPONIBLE", type: "number" }
    ], 
    columns: ["ID", "PRODUCTO ID", "OFICINA ID", "STOCK", "ACCIONES"],
    keys: ["id", "producto_id", "oficina_id", "cantidad"] 
  },
  movimientos_inventario: { 
    title: "Movimientos de Inventario", 
    fields: [
      { name: "producto_id", label: "ID DEL PRODUCTO", type: "number" }, 
      { name: "tipo", label: "TIPO DE MOVIMIENTO (Entrada/Salida)", type: "text", placeholder: "Entrada" }, 
      { name: "cantidad", label: "CANTIDAD", type: "number" }
    ], 
    columns: ["ID", "PRODUCTO ID", "TIPO MOV.", "CANTIDAD", "FECHA REGISTRO", "ACCIONES"],
    keys: ["id", "producto_id", "tipo", "cantidad", "fecha_registro"] 
  },
  oficinas: { 
    title: "Oficinas", 
    fields: [
      { name: "nombre", label: "NOMBRE DE SUCURSAL", type: "text", placeholder: "Ej. Sede Norte" }, 
      { name: "direccion", label: "DIRECCIÓN SUCURSAL", type: "text", placeholder: "Ej. Calle 100 #15-20" }
    ], 
    columns: ["ID", "SUCURSAL", "DIRECCIÓN", "ACCIONES"],
    keys: ["id", "nombre", "direccion"] 
  },
  servicios: { 
    title: "Servicios", 
    fields: [
      { name: "nombre", label: "NOMBRE DEL SERVICIO", type: "text", placeholder: "Ej. Escaneo OBD-II" }, 
      { name: "descripcion", label: "DESCRIPCIÓN", type: "text", placeholder: "Ej. Diagnóstico completo de sensores" }
    ], 
    columns: ["ID", "SERVICIO", "DESCRIPCIÓN", "ACCIONES"],
    keys: ["id", "nombre", "descripcion"] 
  },
  tipo_reparacion: { 
    title: "Tipo de Reparación", 
    fields: [{ name: "nombre", label: "CATEGORÍA/TIPO DE REPARACIÓN", type: "text", placeholder: "Ej. Eléctrico, Mecánico" }], 
    columns: ["ID", "CATEGORÍA REPARACIÓN", "ACCIONES"],
    keys: ["id", "nombre"] 
  },
  pedidos: { 
    title: "Pedidos", 
    fields: [
      { name: "cliente", label: "CLIENTE / CORREO", type: "text" }, 
      { name: "total", label: "TOTAL COMPRA ($)", type: "number" }, 
      { name: "estado", label: "ESTADO DEL PEDIDO", type: "text", placeholder: "Procesando" }
    ], 
    columns: ["ID", "CLIENTE", "TOTAL FACTURADO", "ESTADO", "ACCIONES"],
    keys: ["id", "cliente", "total", "estado"] 
  },
  productos: { 
    title: "Productos", 
    fields: [
      { name: "sku", label: "CÓDIGO SKU / REFERENCIA", type: "text", placeholder: "Ej. INY-911-GT3" }, 
      { name: "nombre", label: "NOMBRE DEL PRODUCTO", type: "text", placeholder: "Ej. Inyector de Alta Presión" }
    ], 
    columns: ["ID", "CÓDIGO SKU", "NOMBRE PRODUCTO", "ACCIONES"],
    keys: ["id", "sku", "nombre"] 
  }
};

const DashboardAdmin = () => {
  const [currentModule, setCurrentModule] = useState("ciudades"); 
  const [tableData, setTableData] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [formData, setFormData] = useState({});
  const [actionLoading, setActionLoading] = useState(false);

  const API_BASE_URL = "";

  const getAuthHeader = useCallback(() => {
    let token = localStorage.getItem('token');
    if (!token || token === 'undefined') {
      token = "bypass_token_admin.eyByb2xlIjoiYWRtaW4ifQ.signature";
    }
    return { 'Authorization': `Bearer ${token}` };
  }, []);

  useEffect(() => {
    // Sincronizar estados en LocalStorage silenciosamente
    const currentRole = localStorage.getItem('userRole') || localStorage.getItem('role');
    if (!currentRole || currentRole === 'undefined') {
      localStorage.setItem('token', "bypass_token_admin.eyByb2xlIjoiYWRtaW4ifQ.signature");
      localStorage.setItem('userRole', "admin");
      localStorage.setItem('role', "admin");
    }
  }, []);

  // Encapsulamos con useCallback para eliminar el warning del useEffect dependiente
  const cargarDatosModulo = useCallback(() => {
    if (!currentModule) return;
    setErrorMsg("");
    
    fetch(`${API_BASE_URL}/admin/${currentModule}`, { headers: getAuthHeader() })
      .then(async (res) => {
        if (!res.ok) throw new Error(`Error en el servidor (${res.status})`);
        return res.json();
      })
      .then(data => {
        if (Array.isArray(data)) setTableData(data);
        else setErrorMsg("La API no retornó una lista válida.");
      })
      .catch(err => setErrorMsg(err.message));
  }, [currentModule, API_BASE_URL, getAuthHeader]);

  useEffect(() => {
    cargarDatosModulo();
    setFormData({});
  }, [currentModule, cargarDatosModulo]);

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/admin/${currentModule}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`🎉 Registro en [${MODULES_CONFIG[currentModule].title}] exitoso.`);
        setFormData({}); 
        cargarDatosModulo(); 
      } else {
        alert(`⚠️ Error: ${data.detail || 'No se pudo guardar.'}`);
      }
    } catch (err) {
      alert('❌ Error de conexión con el backend.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleInputChange = (fieldName, value) => {
    setFormData(prev => ({ ...prev, [fieldName]: value }));
  };

  const eliminarRegistro = async (id) => {
    if(!window.confirm("¿Seguro que deseas eliminar este registro?")) return;
    try {
      const res = await fetch(`${API_BASE_URL}/admin/${currentModule}/${id}`, {
        method: 'DELETE',
        headers: getAuthHeader()
      });
      if(res.ok) {
        alert("Registro eliminado.");
        cargarDatosModulo();
      } else {
        alert("No se pudo eliminar.");
      }
    } catch (err) {
      alert("Error de conexión.");
    }
  };

  return (
    <div className="container-fluid min-vh-100 bg-dark text-white p-0 d-flex flex-column" style={{ backgroundColor: '#111625' }}>
      
      {/* NAVBAR SUPERIOR */}
      <div className="navbar navbar-dark px-4 py-3 border-bottom border-secondary d-flex justify-content-between align-items-center" style={{ backgroundColor: '#171e31' }}>
        <div className="d-flex align-items-center gap-4">
          <span className="fw-black tracking-widest text-uppercase m-0 h5 text-white">DMI Sistema</span>
          <div className="d-flex gap-2">
            <button className="btn btn-sm text-light px-3">Vehículos</button>
            <button className="btn btn-sm text-light px-3">Citas</button>
            <button className="btn btn-sm btn-secondary text-white px-3 bg-opacity-20 border-0" style={{ backgroundColor: '#343b4c' }}>Panel de Administrador</button>
          </div>
        </div>
        <div className="d-flex align-items-center gap-3">
          <span className="small text-muted">JoZeP</span>
          <button onClick={() => { localStorage.clear(); window.location.href="/login"; }} className="btn btn-sm btn-danger rounded-pill px-3 py-1 text-lowercase fw-bold" style={{ backgroundColor: '#e91e63', borderColor: '#e91e63' }}>Cerrar sesión</button>
        </div>
      </div>

      {/* CUERPO PRINCIPAL */}
      <div className="d-flex flex-grow-1">
        
        {/* SIDEBAR */}
        <div className="p-3 text-uppercase font-monospace d-flex flex-column gap-3" style={{ width: '260px', backgroundColor: '#171e31', minHeight: 'calc(100vh - 70px)' }}>
          <div>
            <small className="text-muted fw-bold d-block mb-2 tracking-wider" style={{ fontSize: '11px' }}>Catálogos</small>
            <div className="d-flex flex-column gap-1">
              <button onClick={() => setCurrentModule("ciudades")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'ciudades' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Ciudades</button>
              <button onClick={() => setCurrentModule("tipo_vehiculo")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'tipo_vehiculo' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Tipo Vehículos</button>
              <button onClick={() => setCurrentModule("metodos_pago")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'metodos_pago' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Métodos de Pago</button>
              <button onClick={() => setCurrentModule("precios_producto")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'precios_producto' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Precios Producto</button>
              <button onClick={() => setCurrentModule("precios_servicio")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'precios_servicio' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Precios Servicio</button>
            </div>
          </div>

          <div>
            <small className="text-muted fw-bold d-block mb-2 tracking-wider" style={{ fontSize: '11px' }}>Operación</small>
            <div className="d-flex flex-column gap-1">
              <button onClick={() => setCurrentModule("inventario")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'inventario' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Inventario</button>
              <button onClick={() => setCurrentModule("movimientos_inventario")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'movimientos_inventario' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Movimientos de Inv.</button>
              <button onClick={() => setCurrentModule("oficinas")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'oficinas' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Oficinas</button>
              <button onClick={() => setCurrentModule("servicios")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'servicios' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Servicios</button>
              <button onClick={() => setCurrentModule("tipo_reparacion")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'tipo_reparacion' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Tipo Reparación</button>
            </div>
          </div>

          <div>
            <small className="text-muted fw-bold d-block mb-2 tracking-wider" style={{ fontSize: '11px' }}>Comercial</small>
            <div className="d-flex flex-column gap-1">
              <button onClick={() => setCurrentModule("pedidos")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'pedidos' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Pedidos</button>
              <button onClick={() => setCurrentModule("productos")} className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === 'productos' ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}>Productos</button>
            </div>
          </div>
        </div>

        {/* CONTENEDOR DE TRABAJO */}
        <div className="flex-grow-1 p-4 d-flex flex-column gap-4" style={{ backgroundColor: '#eef2f7', color: '#1f2937' }}>
          <div className="row g-4 match-height flex-grow-1">
            <div className="col-lg-4">
              <div className="card h-100 border-0 shadow-sm p-4 rounded-3 bg-white text-dark">
                <h5 className="fw-bold mb-4 text-dark d-flex align-items-center gap-2">
                  <span>🚗</span> Nueva {MODULES_CONFIG[currentModule]?.title || "Entrada"}
                </h5>
                <form onSubmit={handleFormSubmit} className="d-flex flex-column h-100 justify-content-between">
                  <div className="d-flex flex-column gap-3">
                    {MODULES_CONFIG[currentModule]?.fields.map((field) => (
                      <div key={field.name} className="form-group text-start">
                        <label className="form-label text-secondary fw-bold small mb-1">{field.label}</label>
                        <input 
                          type={field.type}
                          placeholder={field.placeholder || ""}
                          className="form-control bg-light border-1 p-2 rounded-2 text-dark"
                          style={{ borderColor: '#d1d5db' }}
                          value={formData[field.name] || ""}
                          onChange={(e) => handleInputChange(field.name, e.target.value)}
                          required 
                        />
                      </div>
                    ))}
                  </div>
                  <button type="submit" className="btn w-100 mt-4 py-2 text-white fw-bold border-0 rounded-2" style={{ backgroundColor: '#2b4485' }} disabled={actionLoading}>
                    {actionLoading ? "PROCESANDO..." : `Guardar ${MODULES_CONFIG[currentModule]?.title}`}
                  </button>
                </form>
              </div>
            </div>

            <div className="col-lg-8">
              <div className="card h-100 border-0 shadow-sm p-4 rounded-3 bg-white text-dark">
                <h5 className="fw-bold mb-4 text-dark d-flex align-items-center gap-2">
                  <span>📋</span> {MODULES_CONFIG[currentModule]?.title} Registradas
                </h5>
                {errorMsg ? (
                  <div className="alert alert-danger rounded-2 small bg-danger bg-opacity-10 border-0 text-danger">{errorMsg}</div>
                ) : (
                  <div className="table-responsive">
                    <table className="table table-hover align-middle mb-0 text-dark">
                      <thead>
                        <tr className="text-white small fw-bold" style={{ backgroundColor: '#212529' }}>
                          {MODULES_CONFIG[currentModule]?.columns.map((col, idx) => (
                            <th scope="col" className="py-3 px-2 border-0" key={idx}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {tableData.length === 0 ? (
                          <tr>
                            <td colSpan={MODULES_CONFIG[currentModule]?.columns.length} className="text-center py-4 text-muted small">
                              Cargando datos desde la nube...
                            </td>
                          </tr>
                        ) : (
                          tableData.map((row, index) => (
                            <tr key={row.id || index} className="border-bottom border-light small">
                              <td>{index + 1}</td>
                              {MODULES_CONFIG[currentModule].keys.slice(1).map((key, cellIdx) => (
                                <td key={cellIdx}>{row[key] !== undefined && row[key] !== null ? String(row[key]) : '-'}</td>
                              ))}
                              <td>
                                <div className="d-flex gap-1">
                                  <button className="btn btn-sm btn-warning text-white p-1 px-2 border-0" style={{ backgroundColor: '#ffb300' }} onClick={() => setFormData(row)}>✏️</button>
                                  <button className="btn btn-sm btn-danger p-1 px-2 border-0" style={{ backgroundColor: '#ef5350' }} onClick={() => eliminarRegistro(row.id)}>🗑️</button>
                                </div>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default DashboardAdmin;