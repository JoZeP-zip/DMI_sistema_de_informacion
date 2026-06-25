import React, { useState, useEffect, useCallback } from 'react';

const MODULES_CONFIG = {
  ciudades: {
    title: "Ciudades",
    fields: [
      { name: "codigo_ciudad", label: "CÓDIGO CIUDAD", type: "text", placeholder: "Ej. 001" },
      { name: "descripcion_ciudad", label: "CIUDAD", type: "text", placeholder: "Ej. Bogotá" },
      { name: "codigo_postal", label: "CÓDIGO POSTAL", type: "text", placeholder: "Ej. 110111" }
    ],
    columns: ["N°", "CÓDIGO", "CIUDAD", "CÓD. POSTAL", "ACCIONES"],
    keys: ["idciudades", "codigo_ciudad", "descripcion_ciudad", "codigo_postal"],
    idKey: "idciudades",
    listEndpoint: "/api/ciudades",
    createEndpoint: "/config/ciudades/nueva",
    editEndpoint: (id) => `/config/ciudades/editar/${id}`,
    deleteEndpoint: (id) => `/config/ciudades/eliminar/${id}`,
  },
  tipo_vehiculo: {
    title: "Tipo de Vehículo",
    fields: [
      { name: "codigotipovehiculos", label: "CÓDIGO", type: "text", placeholder: "Ej. TV001" },
      { name: "vehiculo", label: "TIPO DE VEHÍCULO", type: "text", placeholder: "Ej. Particular" }
    ],
    columns: ["ID", "CÓDIGO", "TIPO DE VEHÍCULO", "ACCIONES"],
    keys: ["idtipovehiculos", "codigotipovehiculos", "vehiculo"],
    idKey: "idtipovehiculos",
    listEndpoint: "/api/tipovehiculos",
    createEndpoint: "/config/tipovehiculos/nuevo",
    editEndpoint: (id) => `/config/tipovehiculos/editar/${id}`,
    deleteEndpoint: (id) => `/config/tipovehiculos/eliminar/${id}`,
  },
  metodos_pago: {
    title: "Métodos de Pago",
    fields: [
      { name: "codigompago", label: "CÓDIGO", type: "text", placeholder: "Ej. MP001" },
      { name: "descripcionmpago", label: "MÉTODO DE PAGO", type: "text", placeholder: "Ej. Transferencia" }
    ],
    columns: ["ID", "CÓDIGO", "MÉTODO", "ACCIONES"],
    keys: ["idmetodopago", "codigompago", "descripcionmpago"],
    idKey: "idmetodopago",
    listEndpoint: "/api/metodospago",
    createEndpoint: "/config/metodopago/nuevo",
    editEndpoint: (id) => `/config/metodopago/editar/${id}`,
    deleteEndpoint: (id) => `/config/metodopago/eliminar/${id}`,
  },
  precios_producto: {
    title: "Precios Producto",
    fields: [
      { name: "codigoproductoprecio", label: "CÓDIGO", type: "text", placeholder: "Ej. PP001" },
      { name: "descripcionprprecio", label: "DESCRIPCIÓN", type: "text", placeholder: "Ej. Filtro de aceite" },
      { name: "valor", label: "VALOR ($)", type: "number", placeholder: "Ej. 45000" }
    ],
    columns: ["ID", "CÓDIGO", "DESCRIPCIÓN", "VALOR", "ACCIONES"],
    keys: ["idproductoprecio", "codigoproductoprecio", "descripcionprprecio", "valor"],
    idKey: "idproductoprecio",
    listEndpoint: "/api/precios_producto",
    createEndpoint: "/config/productoprecio/nuevo",
    editEndpoint: (id) => `/config/productoprecio/editar/${id}`,
    deleteEndpoint: (id) => `/config/productoprecio/eliminar/${id}`,
  },
  precios_servicio: {
    title: "Precios Servicio",
    fields: [
      { name: "codigoserviciosprecio", label: "CÓDIGO", type: "text", placeholder: "Ej. SP001" },
      { name: "descripcionserviciosprecio", label: "DESCRIPCIÓN", type: "text", placeholder: "Ej. Revisión de frenos" },
      { name: "precioserviciosprecio", label: "PRECIO ($)", type: "text", placeholder: "Ej. 80000" }
    ],
    columns: ["ID", "CÓDIGO", "DESCRIPCIÓN", "PRECIO", "ACCIONES"],
    keys: ["idserviciosprecio", "codigoserviciosprecio", "descripcionserviciosprecio", "precioserviciosprecio"],
    idKey: "idserviciosprecio",
    listEndpoint: "/api/precios_servicio",
    createEndpoint: "/config/serviciosprecio/nuevo",
    editEndpoint: (id) => `/config/serviciosprecio/editar/${id}`,
    deleteEndpoint: (id) => `/config/serviciosprecio/eliminar/${id}`,
  },
  inventario: {
    title: "Inventario",
    fields: [
      { name: "codigoinventario", label: "CÓDIGO", type: "text", placeholder: "Ej. INV001" },
      { name: "descripcioninventario", label: "DESCRIPCIÓN", type: "text", placeholder: "Ej. Filtro de aire" },
      { name: "cantidad", label: "CANTIDAD", type: "number", placeholder: "0" },
      { name: "costo_unitario", label: "COSTO UNITARIO ($)", type: "number", placeholder: "0" },
      { name: "unidad_medida", label: "UNIDAD DE MEDIDA", type: "text", placeholder: "UND" }
    ],
    columns: ["ID", "CÓDIGO", "DESCRIPCIÓN", "CANTIDAD", "COSTO", "ACCIONES"],
    keys: ["idinventario", "codigoinventario", "descripcioninventario", "cantidad", "costo_unitario"],
    idKey: "idinventario",
    listEndpoint: "/api/inventario",
    createEndpoint: "/config/inventario/nuevo",
    editEndpoint: (id) => `/config/inventario/editar/${id}`,
    deleteEndpoint: (id) => `/config/inventario/eliminar/${id}`,
  },
  movimientos_inventario: {
    title: "Movimientos de Inventario",
    fields: [
      { name: "inventario_id", label: "ID DE ÍTEM EN INVENTARIO", type: "number", placeholder: "Ej. 1" },
      { name: "tipo_movimiento", label: "TIPO (entrada / salida)", type: "text", placeholder: "entrada" },
      { name: "cantidad", label: "CANTIDAD", type: "number", placeholder: "Ej. 10" },
      { name: "motivo", label: "MOTIVO (opcional)", type: "text", placeholder: "Ej. Compra a proveedor" }
    ],
    columns: ["ID", "INV. ID", "TIPO", "CANTIDAD", "FECHA", "ACCIONES"],
    keys: ["idmovimiento", "inventario_id", "tipo_movimiento", "cantidad", "fecha"],
    idKey: "idmovimiento",
    listEndpoint: "/api/movimientos_inventario",
    createEndpoint: "/config/movimientos/nuevo",
    editEndpoint: null,
    deleteEndpoint: null,
  },
  oficinas: {
    title: "Oficinas",
    fields: [
      { name: "codigo_oficina", label: "CÓDIGO", type: "text", placeholder: "Ej. OF001" },
      { name: "descripcionof", label: "NOMBRE DE SUCURSAL", type: "text", placeholder: "Ej. Sede Norte" },
      { name: "direccion", label: "DIRECCIÓN", type: "text", placeholder: "Ej. Calle 100 #15-20" },
      { name: "telefono_oficina", label: "TELÉFONO", type: "text", placeholder: "Ej. 3101234567" },
      { name: "ciudades_idciudades", label: "ID CIUDAD", type: "number", placeholder: "Ej. 1" },
      { name: "inventario_idinventario", label: "ID INVENTARIO", type: "number", placeholder: "Ej. 1" }
    ],
    columns: ["ID", "CÓDIGO", "SUCURSAL", "DIRECCIÓN", "ACCIONES"],
    keys: ["idoficinas", "codigo_oficina", "nombre", "direccion"],
    idKey: "idoficinas",
    listEndpoint: "/api/oficinas",
    createEndpoint: "/config/oficinas/nueva",
    editEndpoint: (id) => `/config/oficinas/editar/${id}`,
    deleteEndpoint: (id) => `/config/oficinas/eliminar/${id}`,
  },
  servicios: {
    title: "Servicios",
    fields: [
      { name: "codigoservicio", label: "CÓDIGO", type: "text", placeholder: "Ej. SRV001" },
      { name: "descripcionservicio", label: "DESCRIPCIÓN DEL SERVICIO", type: "text", placeholder: "Ej. Escaneo OBD-II" },
      { name: "serviciosprecio_idserviciosprecio", label: "ID PRECIO SERVICIO", type: "number", placeholder: "Ej. 1" }
    ],
    columns: ["ID", "CÓDIGO", "DESCRIPCIÓN", "ACCIONES"],
    keys: ["idservicios", "codigoservicio", "descripcionservicio"],
    idKey: "idservicios",
    listEndpoint: "/api/servicios",
    createEndpoint: "/config/servicios/nuevo",
    editEndpoint: (id) => `/config/servicios/editar/${id}`,
    deleteEndpoint: (id) => `/config/servicios/eliminar/${id}`,
  },
  tipo_reparacion: {
    title: "Tipo de Reparación",
    fields: [
      { name: "codigotiporeparacion", label: "CÓDIGO", type: "text", placeholder: "Ej. TR001" },
      { name: "descripciontiporeparacion", label: "CATEGORÍA/TIPO", type: "text", placeholder: "Ej. Mecánico" },
      { name: "servicios_idservicios", label: "ID SERVICIO", type: "number", placeholder: "Ej. 1" },
      { name: "pedido_idpedido", label: "ID PEDIDO", type: "number", placeholder: "Ej. 1" }
    ],
    columns: ["ID", "CÓDIGO", "CATEGORÍA", "ACCIONES"],
    keys: ["idtiporeparacion", "codigotiporeparacion", "descripciontiporeparacion"],
    idKey: "idtiporeparacion",
    listEndpoint: "/api/tipo_reparacion",
    createEndpoint: "/config/tiporeparacion/nuevo",
    editEndpoint: (id) => `/config/tiporeparacion/editar/${id}`,
    deleteEndpoint: (id) => `/config/tiporeparacion/eliminar/${id}`,
  },
  pedidos: {
    title: "Pedidos",
    fields: [
      { name: "codigopedido", label: "CÓDIGO PEDIDO", type: "text", placeholder: "Ej. PED001" },
      { name: "fecha", label: "FECHA (YYYY-MM-DD)", type: "text", placeholder: "Ej. 2026-06-23" },
      { name: "fecha_cita", label: "FECHA CITA (ISO)", type: "text", placeholder: "Ej. 2026-06-23T10:00:00" },
      { name: "metodopago_idmetodopago", label: "ID MÉTODO DE PAGO", type: "number", placeholder: "Ej. 1" },
      { name: "estado", label: "ESTADO", type: "text", placeholder: "pendiente" },
      { name: "descripcion", label: "DESCRIPCIÓN (opcional)", type: "text", placeholder: "" }
    ],
    columns: ["ID", "CÓDIGO", "FECHA", "ESTADO", "ACCIONES"],
    keys: ["idpedido", "codigopedido", "fecha", "estado"],
    idKey: "idpedido",
    listEndpoint: "/api/pedidos",
    createEndpoint: "/config/pedidos/nuevo",
    editEndpoint: (id) => `/config/pedidos/editar/${id}`,
    deleteEndpoint: (id) => `/config/pedidos/eliminar/${id}`,
  },
  productos: {
    title: "Productos",
    fields: [
      { name: "codigoproductos", label: "CÓDIGO SKU", type: "text", placeholder: "Ej. INY-001" },
      { name: "descripcionproductos", label: "NOMBRE DEL PRODUCTO", type: "text", placeholder: "Ej. Inyector de alta presión" },
      { name: "productoprecio_idproductoprecio", label: "ID PRECIO PRODUCTO", type: "number", placeholder: "Ej. 1" },
      { name: "pedido_idpedido", label: "ID PEDIDO", type: "number", placeholder: "Ej. 1" }
    ],
    columns: ["ID", "CÓDIGO", "NOMBRE PRODUCTO", "ACCIONES"],
    keys: ["idproductos", "codigoproductos", "descripcionproductos"],
    idKey: "idproductos",
    listEndpoint: "/api/productos",
    createEndpoint: "/config/productos/nuevo",
    editEndpoint: (id) => `/config/productos/editar/${id}`,
    deleteEndpoint: (id) => `/config/productos/eliminar/${id}`,
  },
};

const DashboardAdmin = () => {
  const [currentModule, setCurrentModule] = useState("ciudades");
  const [tableData, setTableData] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [formData, setFormData] = useState({});
  const [editingId, setEditingId] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const getAuthHeader = useCallback(() => {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }, []);

  const cargarDatosModulo = useCallback(() => {
    const cfg = MODULES_CONFIG[currentModule];
    if (!cfg) return;
    setErrorMsg("");

    fetch(cfg.listEndpoint, {
      headers: getAuthHeader(),
      credentials: 'include'
    })
      .then(res => {
        if (!res.ok) throw new Error(`Error ${res.status}`);
        return res.json();
      })
      .then(data => setTableData(Array.isArray(data) ? data : []))
      .catch(err => setErrorMsg(`No se pudieron cargar los datos: ${err.message}`));
  }, [currentModule, getAuthHeader]);

  useEffect(() => {
    cargarDatosModulo();
    setFormData({});
    setEditingId(null);
    setSuccessMsg("");
    setErrorMsg("");
  }, [currentModule, cargarDatosModulo]);

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setErrorMsg("");
    setSuccessMsg("");

    const cfg = MODULES_CONFIG[currentModule];
    const endpoint = editingId && cfg.editEndpoint
      ? cfg.editEndpoint(editingId)
      : cfg.createEndpoint;

    if (!endpoint) {
      setErrorMsg("Este módulo no soporta creación/edición directa.");
      setActionLoading(false);
      return;
    }

    try {
      const form = new URLSearchParams(formData);
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...getAuthHeader() },
        credentials: 'include',
        body: form.toString(),
      });

      if (res.ok || res.redirected) {
        setSuccessMsg(editingId ? "Registro actualizado correctamente." : "Registro creado correctamente.");
        setFormData({});
        setEditingId(null);
        cargarDatosModulo();
      } else {
        const text = await res.text();
        setErrorMsg(`Error al guardar: ${res.status} — ${text.slice(0, 120)}`);
      }
    } catch (err) {
      setErrorMsg(`Error de conexión: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleEdit = (row) => {
    const cfg = MODULES_CONFIG[currentModule];
    setFormData({ ...row });
    setEditingId(row[cfg.idKey]);
    setSuccessMsg("");
    setErrorMsg("");
  };

  const handleCancelEdit = () => {
    setFormData({});
    setEditingId(null);
  };

  const eliminarRegistro = async (id) => {
    const cfg = MODULES_CONFIG[currentModule];
    if (!cfg.deleteEndpoint) {
      alert("Este módulo no permite eliminación directa.");
      return;
    }
    if (!window.confirm("¿Seguro que deseas eliminar este registro?")) return;

    try {
      const res = await fetch(cfg.deleteEndpoint(id), {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...getAuthHeader() },
        credentials: 'include',
      });
      if (res.ok || res.redirected) {
        setSuccessMsg("Registro eliminado.");
        cargarDatosModulo();
      } else {
        setErrorMsg(`No se pudo eliminar. Error ${res.status}`);
      }
    } catch (err) {
      setErrorMsg(`Error de conexión: ${err.message}`);
    }
  };

  const cfg = MODULES_CONFIG[currentModule];

  const navItems = [
    { group: "Catálogos", items: ["ciudades", "tipo_vehiculo", "metodos_pago", "precios_producto", "precios_servicio"] },
    { group: "Operación", items: ["inventario", "movimientos_inventario", "oficinas", "servicios", "tipo_reparacion"] },
    { group: "Comercial", items: ["pedidos", "productos"] },
  ];

  const labelMap = {
    ciudades: "Ciudades", tipo_vehiculo: "Tipo Vehículos", metodos_pago: "Métodos de Pago",
    precios_producto: "Precios Producto", precios_servicio: "Precios Servicio",
    inventario: "Inventario", movimientos_inventario: "Movimientos Inv.",
    oficinas: "Oficinas", servicios: "Servicios", tipo_reparacion: "Tipo Reparación",
    pedidos: "Pedidos", productos: "Productos",
  };

  return (
    <div className="container-fluid min-vh-100 bg-dark text-white p-0 d-flex flex-column" style={{ backgroundColor: '#111625' }}>

      {/* NAVBAR */}
      <div className="navbar navbar-dark px-4 py-3 border-bottom border-secondary d-flex justify-content-between align-items-center" style={{ backgroundColor: '#171e31' }}>
        <div className="d-flex align-items-center gap-4">
          <span className="fw-black text-uppercase m-0 h5 text-white">DMI Sistema</span>
          <div className="d-flex gap-2">
            <button className="btn btn-sm text-light px-3">Vehículos</button>
            <button className="btn btn-sm text-light px-3">Citas</button>
            <button className="btn btn-sm btn-secondary text-white px-3 bg-opacity-20 border-0" style={{ backgroundColor: '#343b4c' }}>
              Panel Admin
            </button>
          </div>
        </div>
        <div className="d-flex align-items-center gap-3">
          <span className="small text-muted">Admin</span>
          <button
            onClick={() => { localStorage.clear(); window.location.href = "/login"; }}
            className="btn btn-sm btn-danger rounded-pill px-3 py-1 fw-bold"
          >
            Cerrar sesión
          </button>
        </div>
      </div>

      {/* BODY */}
      <div className="d-flex flex-grow-1">

        {/* SIDEBAR */}
        <div className="p-3 text-uppercase font-monospace d-flex flex-column gap-3" style={{ width: '220px', backgroundColor: '#171e31', minHeight: 'calc(100vh - 70px)' }}>
          {navItems.map(({ group, items }) => (
            <div key={group}>
              <small className="text-muted fw-bold d-block mb-2" style={{ fontSize: '11px' }}>{group}</small>
              <div className="d-flex flex-column gap-1">
                {items.map(key => (
                  <button
                    key={key}
                    onClick={() => setCurrentModule(key)}
                    className={`btn btn-sm text-start w-100 py-2 border-0 rounded-0 ${currentModule === key ? 'text-white fw-bold bg-primary bg-opacity-10 border-start border-3 border-primary' : 'text-muted'}`}
                  >
                    {labelMap[key]}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* WORK AREA */}
        <div className="flex-grow-1 p-4 d-flex flex-column gap-4" style={{ backgroundColor: '#eef2f7', color: '#1f2937' }}>

          {/* Mensajes globales */}
          {successMsg && (
            <div className="alert alert-success py-2 small border-0 rounded-2" style={{ backgroundColor: '#d1fae5', color: '#065f46' }}>
              ✅ {successMsg}
            </div>
          )}
          {errorMsg && (
            <div className="alert alert-danger py-2 small border-0 rounded-2" style={{ backgroundColor: '#fee2e2', color: '#991b1b' }}>
              ⚠️ {errorMsg}
            </div>
          )}

          <div className="row g-4 flex-grow-1">

            {/* FORMULARIO */}
            <div className="col-lg-4">
              <div className="card h-100 border-0 shadow-sm p-4 rounded-3 bg-white text-dark">
                <h5 className="fw-bold mb-1 text-dark">
                  {editingId ? `✏️ Editar ${cfg?.title}` : `➕ Nueva ${cfg?.title}`}
                </h5>
                {editingId && (
                  <p className="text-muted small mb-3">Editando ID: <strong>{editingId}</strong></p>
                )}
                <form onSubmit={handleFormSubmit} className="d-flex flex-column h-100 justify-content-between">
                  <div className="d-flex flex-column gap-3 mt-3">
                    {cfg?.fields.map((field) => (
                      <div key={field.name}>
                        <label className="form-label text-secondary fw-bold small mb-1">{field.label}</label>
                        <input
                          type={field.type}
                          placeholder={field.placeholder || ""}
                          className="form-control bg-light border-1 p-2 rounded-2 text-dark"
                          style={{ borderColor: '#d1d5db' }}
                          value={formData[field.name] ?? ""}
                          onChange={(e) => setFormData(prev => ({ ...prev, [field.name]: e.target.value }))}
                          required={currentModule !== 'movimientos_inventario' || field.name !== 'motivo'}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="d-flex gap-2 mt-4">
                    <button
                      type="submit"
                      className="btn flex-grow-1 py-2 text-white fw-bold border-0 rounded-2"
                      style={{ backgroundColor: '#2b4485' }}
                      disabled={actionLoading}
                    >
                      {actionLoading ? "PROCESANDO..." : (editingId ? "ACTUALIZAR" : `GUARDAR`)}
                    </button>
                    {editingId && (
                      <button type="button" className="btn btn-outline-secondary rounded-2" onClick={handleCancelEdit}>
                        CANCELAR
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>

            {/* TABLA */}
            <div className="col-lg-8">
              <div className="card h-100 border-0 shadow-sm p-4 rounded-3 bg-white text-dark">
                <div className="d-flex justify-content-between align-items-center mb-4">
                  <h5 className="fw-bold text-dark mb-0">📋 {cfg?.title} registradas</h5>
                  <button
                    className="btn btn-sm btn-outline-secondary rounded-2"
                    onClick={cargarDatosModulo}
                  >
                    🔄 Recargar
                  </button>
                </div>

                <div className="table-responsive">
                  <table className="table table-hover align-middle mb-0 text-dark">
                    <thead>
                      <tr className="text-white small fw-bold" style={{ backgroundColor: '#212529' }}>
                        {cfg?.columns.map((col, idx) => (
                          <th key={idx} className="py-3 px-2 border-0">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tableData.length === 0 ? (
                        <tr>
                          <td colSpan={cfg?.columns.length} className="text-center py-4 text-muted small">
                            Sin datos — verifica la conexión con el backend
                          </td>
                        </tr>
                      ) : (
                        tableData.map((row, index) => (
                          <tr key={row[cfg.idKey] || index} className="border-bottom border-light small">
                            <td className="text-muted">{index + 1}</td>
                            {cfg.keys.slice(1).map((key, cellIdx) => (
                              <td key={cellIdx}>
                                {row[key] !== undefined && row[key] !== null ? String(row[key]) : '—'}
                              </td>
                            ))}
                            <td>
                              <div className="d-flex gap-1">
                                {cfg.editEndpoint && (
                                  <button
                                    className="btn btn-sm btn-warning text-white p-1 px-2 border-0"
                                    style={{ backgroundColor: '#ffb300' }}
                                    onClick={() => handleEdit(row)}
                                  >
                                    ✏️
                                  </button>
                                )}
                                {cfg.deleteEndpoint && (
                                  <button
                                    className="btn btn-sm btn-danger p-1 px-2 border-0"
                                    style={{ backgroundColor: '#ef5350' }}
                                    onClick={() => eliminarRegistro(row[cfg.idKey])}
                                  >
                                    🗑️
                                  </button>
                                )}
                                {!cfg.editEndpoint && !cfg.deleteEndpoint && (
                                  <span className="text-muted small">solo lectura</span>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardAdmin;