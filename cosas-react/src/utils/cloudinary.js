// 👉 El cloud name se lee desde tu .env (REACT_APP_CLOUDINARY_CLOUD_NAME).
//    Si por alguna razón no está definida, se usa 'wzgznvhl' como respaldo.
export const CLOUDINARY_CLOUD_NAME = process.env.REACT_APP_CLOUDINARY_CLOUD_NAME || 'wzgznvhl';

/**
 * Arma la URL final de una imagen de Cloudinary a partir de su public ID.
 * @param {string} publicId - ej: 'dmi-proyectos/camaroamarillo'
 * @param {string} transform - transformaciones de Cloudinary (calidad/formato/tamaño)
 */
export const cld = (publicId, transform = 'f_auto,q_auto,w_800') =>
  `https://res.cloudinary.com/${CLOUDINARY_CLOUD_NAME}/image/upload/${transform}/${publicId}`;