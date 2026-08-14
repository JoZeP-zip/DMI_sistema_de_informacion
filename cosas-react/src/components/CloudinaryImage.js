import React from 'react';

/**
 * Componente para mostrar imágenes desde Cloudinary con optimización automática
 */
const CloudinaryImage = ({ 
  publicId, 
  width = 300, 
  height = 300, 
  crop = 'fill',
  quality = 'auto',
  fetchFormat = 'auto',
  alt = 'Imagen',
  className = '',
}) => {
  if (!publicId) return null;

  // Construir la URL optimizada
  const cloudName = process.env.REACT_APP_CLOUDINARY_CLOUD_NAME;
  const imageUrl = `https://res.cloudinary.com/${cloudName}/image/upload/w_${width},h_${height},c_${crop},q_${quality},f_${fetchFormat}/${publicId}`;

  return (
    <img
      src={imageUrl}
      alt={alt}
      className={className}
      style={{
        maxWidth: '100%',
        height: 'auto',
      }}
    />
  );
};

export default CloudinaryImage;
