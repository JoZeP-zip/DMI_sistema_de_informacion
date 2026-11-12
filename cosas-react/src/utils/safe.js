// Utilidades para no confiar a ciegas en datos que vienen del servidor.

const HOSTS_PAGO_PERMITIDOS = ["checkout.wompi.co"];

/** Devuelve la URL si es https y apunta a un host de pago permitido; si no, null. */
export function urlPagoSegura(valor) {
  try {
    const url = new URL(String(valor), window.location.origin);
    if (url.protocol === "https:" && HOSTS_PAGO_PERMITIDOS.includes(url.hostname)) {
      return url.href;
    }
  } catch (_) {
    /* URL invalida */
  }
  return null;
}

/** Redirige solo si la URL es de un host de pago permitido. */
export function redirigirAPago(valor) {
  const destino = urlPagoSegura(valor);
  if (!destino) throw new Error("El enlace de pago recibido no es valido.");
  window.location.assign(destino);
}

const ROLES_VALIDOS = ["admin", "usuario", "cliente", "mecanico", "mecanico_taller"];

/** Texto plano, sin caracteres de control y con longitud acotada. */
export function textoSeguro(valor, max = 200) {
  // eslint-disable-next-line no-control-regex
  return String(valor ?? "").replace(/[\u0000-\u001F\u007F]/g, "").slice(0, max);
}

/** Rol en minusculas; si no es conocido, "usuario". */
export function rolSeguro(valor) {
  const rol = textoSeguro(valor, 30).toLowerCase();
  return ROLES_VALIDOS.includes(rol) ? rol : "usuario";
}

/** Token con forma de JWT / token opaco (sin espacios ni caracteres raros). */
export function tokenSeguro(valor) {
  const t = String(valor ?? "");
  return /^[A-Za-z0-9\-._~+/=]{10,4096}$/.test(t) ? t : "";
}
