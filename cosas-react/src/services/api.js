/**
 * api.js â€” Capa de servicios para DMI Motors
 * Centraliza todas las llamadas al backend FastAPI.
 * UbicaciÃ³n sugerida: src/services/api.js
 *
 * USO EN CUALQUIER COMPONENTE:
 *   import { AuthService, VehiculosService, CitasService } from '../services/api';
 */

<<<<<<< HEAD
// ─────────────────────────────────────────────
//  BASE URL — cambia este valor si el codespace
//  rota o si pasas a producción.
// ─────────────────────────────────────────────
const BASE_URL = process.env.REACT_APP_API_URL;
=======
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
//  BASE URL â€” cambia este valor si el codespace
//  rota o si pasas a producciÃ³n.
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const getApiBaseUrl = () => {
  const { protocol, hostname } = window.location;
>>>>>>> ff73952eb317d5a23a72c7eefa847811bbd639b8

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  if (hostname.includes("app.github.dev")) {
    return `${protocol}//${hostname.replace(/-3000\.app\.github\.dev$/, "-8000.app.github.dev")}`;
  }

  return "";
};

const BASE_URL = getApiBaseUrl();

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
//  HELPER: construye headers con el token JWT
//  que React guarda en localStorage tras el login.
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const authHeaders = () => {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

/**
 * Wrapper genÃ©rico de fetch.
 * Lanza un Error si el servidor responde con { error: "..." }
 * o si el status HTTP no es 2xx.
 */
const request = async (path, options = {}) => {
  const res = await fetch(`${BASE_URL}${path}`, options);
  const contentType = res.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || `Error ${res.status}`);
    return data;
  }

  if (!res.ok) throw new Error(`Error ${res.status}`);
  return null;
};


// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  AUTH SERVICE
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
export const AuthService = {
  /**
   * Login â€” guarda token, role y email en localStorage.
   * @returns {{ token, role, email, nombre }}
   */
  login: async (email, password) => {
    const data = await request("/login-react", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("token",  data.token);
    localStorage.setItem("role",   data.role);
    localStorage.setItem("email",  data.email);
    localStorage.setItem("nombre", data.nombre);
    localStorage.setItem("dmiSessionStartedAt", new Date().toISOString());
    return data;
  },

  /**
   * Registro de usuario nuevo.
   * @returns {{ success, message }}
   */
  registro: async (formData) => {
    return request("/registro-react", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });
  },

  /** Limpia localStorage y cierra sesiÃ³n local. */
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("email");
    localStorage.removeItem("nombre");
    localStorage.removeItem("dmiSessionStartedAt");
  },

  /** Devuelve el usuario guardado en localStorage o null. */
  getUsuarioActual: () => {
    const token = localStorage.getItem("token");
    const role  = localStorage.getItem("role");
    const email = localStorage.getItem("email");
    const nombre = localStorage.getItem("nombre");
    if (!token) return null;
    return { token, role, email, nombre };
  },

  isAdmin: () => localStorage.getItem("role") === "admin",
};


// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  VEHÃCULOS SERVICE
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
export const VehiculosService = {
  /** Lista todos los vehÃ­culos. */
  listar: () => request("/api/vehiculos", { headers: authHeaders() }),

  /** Crea un vehÃ­culo nuevo.
   * @param {Object} datos â€” campos del formulario
   */
  crear: async (datos) => {
    const form = new URLSearchParams(datos);
    const res = await fetch(`${BASE_URL}/vehiculo/nuevo`, {
      method: "POST",
      headers: { 
        ...authHeaders(),
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "include",
      body: form.toString(),
    });
    if (!res.ok) throw new Error(`Error al crear vehÃ­culo: ${res.status}`);
    return res;
  },
  /**
   * Actualiza un vehÃ­culo existente.
   * @param {number} id
   * @param {Object} datos
   */
  editar: async (id, datos) => {
    const form = new URLSearchParams(datos);
    const res = await fetch(`${BASE_URL}/vehiculo/editar/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      credentials: "include",
      body: form.toString(),
    });
    if (!res.ok) throw new Error(`Error al editar vehÃ­culo: ${res.status}`);
    return res;
  },

  /** Elimina un vehÃ­culo. */
  eliminar: async (id) => {
    const res = await fetch(`${BASE_URL}/vehiculo/eliminar/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Error al eliminar vehÃ­culo: ${res.status}`);
    return res;
  },
};


// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  CITAS SERVICE
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
export const CitasService = {
  /** Lista todas las citas con datos del vehÃ­culo. */
  listar: () => request("/api/citas", { headers: authHeaders() }),

  /**
   * Crea una nueva cita.
   * @param {{ vehiculos_idvehiculo, fecha_cita, hora_cita, motivo, observaciones }} datos
   */
  crear: async (datos) => {
    const form = new URLSearchParams(datos);
    const res = await fetch(`${BASE_URL}/citas/nueva`, {
      method: "POST",
      headers: {
        ...authHeaders(),
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "include",
      body: form.toString(),
    });
    if (!res.ok) throw new Error(`Error al crear cita: ${res.status}`);
    return res;
  },

  /** Cambia el estado de una cita (pendiente / completada / cancelada). */
  cambiarEstado: async (id, estado) => {
    const form = new URLSearchParams({ estado });
    const res = await fetch(`${BASE_URL}/citas/estado/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      credentials: "include",
      body: form.toString(),
    });
    if (!res.ok) throw new Error(`Error al cambiar estado: ${res.status}`);
    return res;
  },

  /** Elimina una cita. */
  eliminar: async (id) => {
    const res = await fetch(`${BASE_URL}/citas/eliminar/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Error al eliminar cita: ${res.status}`);
    return res;
  },
};


// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  CONFIGURACIÃ“N SERVICE
//  Cubre las 11 entidades del panel admin
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

/** Helper interno para los endpoints de config que usan form-urlencoded */
const configPost = async (path, datos = {}) => {
  const form = new URLSearchParams(datos);
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    credentials: "include",
    body: form.toString(),
  });
  if (!res.ok) throw new Error(`Error en ${path}: ${res.status}`);
  return res;
};

export const ConfigService = {
  // â”€â”€ Ciudades â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  ciudades: {
    listar:   () => request("/api/ciudades", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/ciudades/nueva", d),
    editar:   (id, d) => configPost(`/config/ciudades/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/ciudades/eliminar/${id}`),
  },

  // â”€â”€ Tipos de vehÃ­culo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  tipovehiculos: {
    listar:   () => request("/api/vehiculos", { headers: authHeaders() }), // reutiliza el general
    crear:    (d) => configPost("/config/tipovehiculos/nuevo", d),
    editar:   (id, d) => configPost(`/config/tipovehiculos/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/tipovehiculos/eliminar/${id}`),
  },

  // â”€â”€ MÃ©todos de pago â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  metodopago: {
    listar:   () => request("/api/metodospago", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/metodopago/nuevo", d),
    editar:   (id, d) => configPost(`/config/metodopago/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/metodopago/eliminar/${id}`),
  },

  // â”€â”€ Precio producto â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  productoprecio: {
    crear:    (d) => configPost("/config/productoprecio/nuevo", d),
    editar:   (id, d) => configPost(`/config/productoprecio/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/productoprecio/eliminar/${id}`),
  },

  // â”€â”€ Precio servicio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  serviciosprecio: {
    crear:    (d) => configPost("/config/serviciosprecio/nuevo", d),
    editar:   (id, d) => configPost(`/config/serviciosprecio/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/serviciosprecio/eliminar/${id}`),
  },

  // â”€â”€ Inventario â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  inventario: {
    crear:    (d) => configPost("/config/inventario/nuevo", d),
    editar:   (id, d) => configPost(`/config/inventario/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/inventario/eliminar/${id}`),
    movimiento: (d) => configPost("/config/movimientos/nuevo", d),
  },

  // â”€â”€ Oficinas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  oficinas: {
    listar:   () => request("/api/oficinas", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/oficinas/nuevo", d),
    editar:   (id, d) => configPost(`/config/oficinas/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/oficinas/eliminar/${id}`),
  },

  // â”€â”€ Servicios â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  servicios: {
    listar:   () => request("/api/servicios", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/servicios/nuevo", d),
    editar:   (id, d) => configPost(`/config/servicios/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/servicios/eliminar/${id}`),
  },

  // â”€â”€ Tipo reparaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  tiporeparacion: {
    crear:    (d) => configPost("/config/tiporeparacion/nuevo", d),
    editar:   (id, d) => configPost(`/config/tiporeparacion/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/tiporeparacion/eliminar/${id}`),
  },

  // â”€â”€ Pedidos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  pedidos: {
    listar:   () => request("/api/pedidos", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/pedidos/nuevo", d),
    editar:   (id, d) => configPost(`/config/pedidos/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/pedidos/eliminar/${id}`),
  },

  // â”€â”€ Productos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  productos: {
    listar:   () => request("/api/productos", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/productos/nuevo", d),
    editar:   (id, d) => configPost(`/config/productos/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/productos/eliminar/${id}`),
  },
};


export const MiCuentaService = {
  obtener: () => request("/api/mi-garage", {
    headers: authHeaders(),
    credentials: "include",
  }),
};
