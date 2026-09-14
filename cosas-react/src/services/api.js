/**
 * api.js - Capa de servicios para DMI Motors.
 * Centraliza las llamadas al backend FastAPI.
 */

// ------------------------------------------------
// BASE URL
// ------------------------------------------------
const getApiBaseUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

  const { protocol, hostname } = window.location;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  const isLocalNetworkHost = /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[0-1])\.)/.test(hostname);
  if (isLocalNetworkHost) {
    return `http://${hostname}:8000`;
  }

  if (hostname.includes("app.github.dev")) {
    return `${protocol}//${hostname.replace(
      /-3000\.app\.github\.dev$/,
      "-8000.app.github.dev"
    )}`;
  }

  return "";
};

const BASE_URL = getApiBaseUrl();
const PASSWORD_RECOVERY_PUBLIC_URL = "https://dmi-sistema-de-informacion.vercel.app/?recovery=1";

const clearAuthSession = () => {
  ["token", "role", "email", "nombre", "dmiSessionStartedAt"].forEach((key) => {
    localStorage.removeItem(key);
  });
};

export const handleUnauthorizedResponse = () => {
  clearAuthSession();
  window.dispatchEvent(new CustomEvent("dmi:session-invalid"));
};

const requireActiveSession = (response) => {
  if (response.status === 401) {
    handleUnauthorizedResponse();
    throw new Error("Tu sesion ya no es valida o tu cuenta ya no existe.");
  }
  return response;
};

const authHeaders = () => {
  const token = localStorage.getItem("token");

  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};
/**
 * Wrapper generico de fetch.
 * Lanza un Error si el servidor responde con { error: "..." }
 * o si el status HTTP no es 2xx.
 */
const request = async (path, options = {}) => {
  const { skipSessionInvalidation = false, ...fetchOptions } = options;
  console.log("BASE_URL:", BASE_URL);
console.log("URL:", `${BASE_URL}${path}`);

let res;

try {
  res = await fetch(`${BASE_URL}${path}`, {
    ...fetchOptions,
    credentials: "include",
  });
} catch (error) {
  console.error("ERROR DE CONEXIÓN CON API:", error);
  console.error("BASE_URL:", BASE_URL);
  console.error("PATH:", path);
  throw error;
}
  const contentType = res.headers.get("content-type") || "";

  if (res.status === 401 && !skipSessionInvalidation) {
    handleUnauthorizedResponse();
  }

  if (contentType.includes("application/json")) {
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || `Error ${res.status}`);
    return data;
  }

  if (!res.ok) throw new Error(`Error ${res.status}`);
  return null;
};


// 
//  AUTH SERVICE
// 
export const AuthService = {
  /**
   * Login — guarda token, role y email en localStorage.
   * @returns {{ token, role, email, nombre }}
   */
  login: async (email, password) => {
    const data = await request("/login-react", {
      method: "POST",
      skipSessionInvalidation: true,
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

  verificarRegistro: (email, pin) => request("/registro-react/verificar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, pin }),
  }),

  validarSesion: () => request("/api/auth/session", {
    headers: authHeaders(),
  }),

  solicitarRecuperacionPassword: (email) => request("/password-recovery/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // Vercel es la URL publica: asi el enlace funciona tambien desde celulares.
    body: JSON.stringify({ email, redirect_url: PASSWORD_RECOVERY_PUBLIC_URL }),
  }),

  restablecerPassword: ({ accessToken, refreshToken, password }) => request("/password-recovery/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      access_token: accessToken,
      refresh_token: refreshToken,
      password,
    }),
  }),

  /** Limpia localStorage y cierra sesion local. */
  logout: () => {
    clearAuthSession();
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



//  VEHICULOS SERVICIO

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
        ...authHeaders(),
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "include",
      body: form.toString(),
    });
    requireActiveSession(res);
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
    requireActiveSession(res);
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
    requireActiveSession(res);
    if (!res.ok) throw new Error(`Error al eliminar vehículo: ${res.status}`);
    return res;
  },
};


// 
//  CITAS SERVICE
// 
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
      headers: {
        ...authHeaders(),
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "include",
      body: form.toString(),
    });
    requireActiveSession(res);
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
    requireActiveSession(res);
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
    requireActiveSession(res);
    if (!res.ok) throw new Error(`Error al eliminar cita: ${res.status}`);
    return res;
  },

  reprogramar: (id, datos) => request(`/api/citas/${id}/reprogramar`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(datos),
  }),

  cancelar: (id, motivo = "") => request(`/api/citas/${id}/cancelar`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ motivo }),
  }),
};

export const NotificacionesService = {
  listar: () => request("/api/notificaciones", { headers: authHeaders() }),
  marcarLeida: (id) => request(`/api/notificaciones/${id}/leer`, { method: "POST", headers: authHeaders() }),
};


// 
//  CONFIGURACIONN SERVICIOS
//  Cubre las 11 entidades del panel admin
// 

/** Helper interno para los endpoints de config que usan form-urlencoded */
const configPost = async (path, datos = {}) => {
  const form = new URLSearchParams(datos);
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    credentials: "include",
    body: form.toString(),
  });
  requireActiveSession(res);
  if (!res.ok) throw new Error(`Error en ${path}: ${res.status}`);
  return res;
};

export const ConfigService = {
  //  Ciudades 
  ciudades: {
    listar:   () => request("/api/ciudades", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/ciudades/nueva", d),
    editar:   (id, d) => configPost(`/config/ciudades/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/ciudades/eliminar/${id}`),
  },

  // Tipos de vehiculos
  tipovehiculos: {
    listar:   () => request("/api/vehiculos", { headers: authHeaders() }), // reutiliza el general
    crear:    (d) => configPost("/config/tipovehiculos/nuevo", d),
    editar:   (id, d) => configPost(`/config/tipovehiculos/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/tipovehiculos/eliminar/${id}`),
  },

  // Metodos de pago 
  metodopago: {
    listar:   () => request("/api/metodospago", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/metodopago/nuevo", d),
    editar:   (id, d) => configPost(`/config/metodopago/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/metodopago/eliminar/${id}`),
  },

  //  Precio producto 
  productoprecio: {
    crear:    (d) => configPost("/config/productoprecio/nuevo", d),
    editar:   (id, d) => configPost(`/config/productoprecio/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/productoprecio/eliminar/${id}`),
  },

  //  Precio servicio 
  serviciosprecio: {
    crear:    (d) => configPost("/config/serviciosprecio/nuevo", d),
    editar:   (id, d) => configPost(`/config/serviciosprecio/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/serviciosprecio/eliminar/${id}`),
  },

  //  Inventario 
  inventario: {
    crear:    (d) => configPost("/config/inventario/nuevo", d),
    editar:   (id, d) => configPost(`/config/inventario/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/inventario/eliminar/${id}`),
    movimiento: (d) => configPost("/config/movimientos/nuevo", d),
  },

  // Oficinas 
  oficinas: {
    listar:   () => request("/api/oficinas", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/oficinas/nuevo", d),
    editar:   (id, d) => configPost(`/config/oficinas/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/oficinas/eliminar/${id}`),
  },

  //Servicios 
  servicios: {
    listar:   () => request("/api/servicios", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/servicios/nuevo", d),
    editar:   (id, d) => configPost(`/config/servicios/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/servicios/eliminar/${id}`),
  },

  //Tipo reparacion
  tiporeparacion: {
    crear:    (d) => configPost("/config/tiporeparacion/nuevo", d),
    editar:   (id, d) => configPost(`/config/tiporeparacion/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/tiporeparacion/eliminar/${id}`),
  },

  //  Pedidos
  pedidos: {
    listar:   () => request("/api/pedidos", { headers: authHeaders() }),
    crear:    (d) => configPost("/config/pedidos/nuevo", d),
    editar:   (id, d) => configPost(`/config/pedidos/editar/${id}`, d),
    eliminar: (id) => configPost(`/config/pedidos/eliminar/${id}`),
  },

  // Productos 
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
  responderCotizacion: (cotizacionId, respuesta) => request(`/api/mi-garage/cotizaciones/${cotizacionId}/respuesta`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ respuesta }),
    credentials: "include",
  }),
  prepararPagoFactura: (facturaId, metodoPago) => request(`/api/mi-garage/facturas/${facturaId}/pago`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ metodo_pago: metodoPago }),
    credentials: "include",
  }),
};

// COMPRA / CHECKOUT
// El pedido se registra en el backend para enlazarlo con el usuario autenticado.
export const CheckoutService = {
  registrarPedido: ({ datos, items }) => request("/api/checkout/pedidos", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ datos, items }),
  }),
};
