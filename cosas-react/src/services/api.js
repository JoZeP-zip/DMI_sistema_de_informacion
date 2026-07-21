/**
 * api.js — Capa de servicios para DMI Motors
 * Centraliza todas las llamadas al backend FastAPI.
 * Ubicación sugerida: src/services/api.js
 *
 * USO EN CUALQUIER COMPONENTE:
 *   import { AuthService, VehiculosService, CitasService } from '../services/api';
 */

// ─────────────────────────────────────────────
//  BASE URL — cambia este valor si el codespace
//  rota o si pasas a producción.
// ─────────────────────────────────────────────
const BASE_URL = process.env.REACT_APP_API_URL;

// ─────────────────────────────────────────────
//  HELPER: construye headers con el token JWT
//  que React guarda en localStorage tras el login.
// ─────────────────────────────────────────────
const authHeaders = () => {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

/**
 * Wrapper genérico de fetch.
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


// ══════════════════════════════════════════════
//  AUTH SERVICE
// ══════════════════════════════════════════════
export const AuthService = {
  /**
   * Login — guarda token, role y email en localStorage.
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

  /** Limpia localStorage y cierra sesión local. */
  logout: () => {
    localStorage.clear();
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


// ══════════════════════════════════════════════
//  VEHÍCULOS SERVICE
// ══════════════════════════════════════════════
export const VehiculosService = {
  /** Lista todos los vehículos. */
  listar: () => request("/api/vehiculos", { headers: authHeaders() }),

  /** Crea un vehículo nuevo.
   * @param {Object} datos — campos del formulario
   */
  crear: async (datos) => {
    const form = new URLSearchParams(datos);
    const res = await fetch(`${BASE_URL}/vehiculo/nuevo`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/x-www-form-urlencoded",
        ...authHeaders() 
      },
      body: form.toString(),
    });
    if (!res.ok) throw new Error(`Error al crear vehículo: ${res.status}`);
    return res;
  },
  /**
   * Actualiza un vehículo existente.
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
    if (!res.ok) throw new Error(`Error al editar vehículo: ${res.status}`);
    return res;
  },

  /** Elimina un vehículo. */
  eliminar: async (id) => {
    const res = await fetch(`${BASE_URL}/vehiculo/eliminar/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Error al eliminar vehículo: ${res.status}`);
    return res;
  },
};


// ══════════════════════════════════════════════
//  CITAS SERVICE
// ══════════════════════════════════════════════
export const CitasService = {
  /** Lista todas las citas con datos del vehículo. */
  listar: () => request("/api/citas", { headers: authHeaders() }),

  /**
   * Crea una nueva cita.
   * @param {{ vehiculos_idvehiculo, fecha_cita, hora_cita, motivo, observaciones }} datos
   */
  crear: async (datos) => {
    const form = new URLSearchParams(datos);
    const res = await fetch(`${BASE_URL}/citas/nueva`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
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


// ══════════════════════════════════════════════
//  CONFIGURACIÓN SERVICE
//  Cubre las 11 entidades del panel admin
// ══════════════════════════════════════════════

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
  // ── Ciudades ──────────────────────────────
  ciudades: {
    listar:   () => request("/api/ciudades", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/ciudades/nueva", d),
    editar:   (id, d) => configPost(`/config/ciudades/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/ciudades/eliminar/${id}`),
  },

  // ── Tipos de vehículo ────────────────────
  tipovehiculos: {
    listar:   () => request("/api/vehiculos", { headers: authHeaders() }), // reutiliza el general
    crear:    (d) => configPost("/config/tipovehiculos/nuevo", d),
    editar:   (id, d) => configPost(`/config/tipovehiculos/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/tipovehiculos/eliminar/${id}`),
  },

  // ── Métodos de pago ───────────────────────
  metodopago: {
    listar:   () => request("/api/metodospago", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/metodopago/nuevo", d),
    editar:   (id, d) => configPost(`/config/metodopago/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/metodopago/eliminar/${id}`),
  },

  // ── Precio producto ───────────────────────
  productoprecio: {
    crear:    (d) => configPost("/config/productoprecio/nuevo", d),
    editar:   (id, d) => configPost(`/config/productoprecio/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/productoprecio/eliminar/${id}`),
  },

  // ── Precio servicio ───────────────────────
  serviciosprecio: {
    crear:    (d) => configPost("/config/serviciosprecio/nuevo", d),
    editar:   (id, d) => configPost(`/config/serviciosprecio/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/serviciosprecio/eliminar/${id}`),
  },

  // ── Inventario ────────────────────────────
  inventario: {
    crear:    (d) => configPost("/config/inventario/nuevo", d),
    editar:   (id, d) => configPost(`/config/inventario/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/inventario/eliminar/${id}`),
    movimiento: (d) => configPost("/config/movimientos/nuevo", d),
  },

  // ── Oficinas ──────────────────────────────
  oficinas: {
    listar:   () => request("/api/oficinas", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/oficinas/nueva", d),
    editar:   (id, d) => configPost(`/config/oficinas/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/oficinas/eliminar/${id}`),
  },

  // ── Servicios ─────────────────────────────
  servicios: {
    listar:   () => request("/api/servicios", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/servicios/nuevo", d),
    editar:   (id, d) => configPost(`/config/servicios/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/servicios/eliminar/${id}`),
  },

  // ── Tipo reparación ───────────────────────
  tiporeparacion: {
    crear:    (d) => configPost("/config/tiporeparacion/nuevo", d),
    editar:   (id, d) => configPost(`/config/tiporeparacion/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/tiporeparacion/eliminar/${id}`),
  },

  // ── Pedidos ───────────────────────────────
  pedidos: {
    listar:   () => request("/api/pedidos", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/pedidos/nuevo", d),
    editar:   (id, d) => configPost(`/config/pedidos/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/pedidos/eliminar/${id}`),
  },

  // ── Productos ─────────────────────────────
  productos: {
    listar:   () => request("/api/productos", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/productos/nuevo", d),
    editar:   (id, d) => configPost(`/config/productos/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/productos/eliminar/${id}`),
  },
};