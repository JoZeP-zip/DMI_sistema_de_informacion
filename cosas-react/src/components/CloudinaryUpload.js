import React, { useRef, useState } from 'react';

const CloudinaryUpload = ({ onUploadSuccess, onUploadError, maxSize = 5 }) => {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    
    if (!file) return;

    // Validar tamaño (5MB por defecto)
    if (file.size > maxSize * 1024 * 1024) {
      if (onUploadError) {
        onUploadError(`El archivo es muy grande. Máximo: ${maxSize}MB`);
      }
      return;
    }

    // Validar tipo de archivo
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      if (onUploadError) {
        onUploadError('Solo se permiten imágenes (JPEG, PNG, GIF, WebP)');
      }
      return;
    }

    await uploadToCloudinary(file);
  };

  const uploadToCloudinary = async (file) => {
    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('upload_preset', process.env.REACT_APP_CLOUDINARY_UPLOAD_PRESET);
    formData.append('cloud_name', process.env.REACT_APP_CLOUDINARY_CLOUD_NAME);

    try {
      const response = await fetch(
        `https://api.cloudinary.com/v1_1/${process.env.REACT_APP_CLOUDINARY_CLOUD_NAME}/image/upload`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error('Error en la carga');
      }

      const data = await response.json();
      
      setIsUploading(false);
      setUploadProgress(0);

      if (onUploadSuccess) {
        onUploadSuccess({
          url: data.secure_url,
          publicId: data.public_id,
          width: data.width,
          height: data.height,
          format: data.format,
        });
      }

      // Limpiar input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      setIsUploading(false);
      setUploadProgress(0);
      if (onUploadError) {
        onUploadError(error.message);
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.style.backgroundColor = '#f0f0f0';
  };

  const handleDragLeave = (e) => {
    e.currentTarget.style.backgroundColor = '';
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.currentTarget.style.backgroundColor = '';
    
    const file = e.dataTransfer.files[0];
    if (file) {
      await uploadToCloudinary(file);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        border: '2px dashed #ccc',
        borderRadius: '8px',
        padding: '20px',
        textAlign: 'center',
        cursor: 'pointer',
        transition: 'all 0.3s ease',
      }}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />

      {isUploading ? (
        <>
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Cargando...</span>
          </div>
          <p className="mt-2">Subiendo: {uploadProgress}%</p>
        </>
      ) : (
        <>
          <p>
            <strong>Arrastra una imagen aquí</strong> o haz clic para seleccionar
          </p>
          <small className="text-muted">
            Máximo {maxSize}MB • JPG, PNG, GIF, WebP
          </small>
        </>
      )}
    </div>
  );
};

export default CloudinaryUpload;
