import React, { useRef, useState } from 'react';

/**
 * Componente para subir imágenes a Cloudinary
 * Devuelve el public_id de la imagen cargada
 */
const CloudinaryUploadImage = ({ onUploadSuccess, onUploadError, maxSize = 10, multiple = false }) => {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewImages, setPreviewImages] = useState([]);

  const handleFileSelect = async (event) => {
    const files = multiple 
      ? Array.from(event.target.files || []) 
      : [event.target.files?.[0]].filter(Boolean);
    
    if (!files.length) return;

    // Validar cada archivo
    const validFiles = files.filter(file => {
      if (file.size > maxSize * 1024 * 1024) {
        if (onUploadError) {
          onUploadError(`${file.name} es muy grande. Máximo: ${maxSize}MB`);
        }
        return false;
      }

      const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        if (onUploadError) {
          onUploadError(`${file.name} no es un formato válido`);
        }
        return false;
      }

      return true;
    });

    if (!validFiles.length) return;

    // Mostrar previsualizaciones
    const previews = validFiles.map(file => URL.createObjectURL(file));
    setPreviewImages(previews);

    // Subir archivos
    for (const file of validFiles) {
      await uploadToCloudinary(file);
    }
  };

  const uploadToCloudinary = async (file) => {
    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('upload_preset', process.env.REACT_APP_CLOUDINARY_UPLOAD_PRESET);
    formData.append('cloud_name', process.env.REACT_APP_CLOUDINARY_CLOUD_NAME);
    formData.append('folder', 'dmi-proyectos'); // Organizar en carpeta

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
          publicId: data.public_id,
          url: data.secure_url,
          width: data.width,
          height: data.height,
          format: data.format,
          fileName: file.name,
        });
      }

      // Limpiar input si es una única carga
      if (!multiple && fileInputRef.current) {
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
    e.currentTarget.style.backgroundColor = 'rgba(255, 47, 85, 0.1)';
  };

  const handleDragLeave = (e) => {
    e.currentTarget.style.backgroundColor = '';
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.currentTarget.style.backgroundColor = '';
    
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) {
      const dataTransfer = new DataTransfer();
      files.forEach(file => dataTransfer.items.add(file));
      const input = fileInputRef.current;
      if (input) {
        input.files = dataTransfer.files;
        await handleFileSelect({ target: { files: dataTransfer.files } });
      }
    }
  };

  return (
    <div className="cloudinary-upload-container">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{
          border: '2px dashed #ff2f55',
          borderRadius: '8px',
          padding: '30px',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          backgroundColor: 'rgba(255, 47, 85, 0.05)'
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          multiple={multiple}
          style={{ display: 'none' }}
        />

        {isUploading ? (
          <>
            <div className="spinner-border text-danger" role="status">
              <span className="visually-hidden">Cargando...</span>
            </div>
            <p className="mt-3 text-white">
              Subiendo: <strong>{uploadProgress}%</strong>
            </p>
            <div className="progress" style={{ height: '6px', marginTop: '10px' }}>
              <div 
                className="progress-bar bg-danger" 
                role="progressbar" 
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </>
        ) : (
          <>
            <svg 
              width="48" 
              height="48" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="#ff2f55" 
              strokeWidth="2"
              style={{ marginBottom: '12px' }}
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <p className="text-white fw-bold mb-2">
              Arrastra imágenes aquí
            </p>
            <small className="text-muted">
              O haz clic para seleccionar • Máximo {maxSize}MB • JPG, PNG, GIF, WebP
            </small>
          </>
        )}
      </div>

      {/* Previsualizaciones */}
      {previewImages.length > 0 && (
        <div className="mt-4">
          <h6 className="text-white mb-3">Previsualizaciones:</h6>
          <div className="row g-2">
            {previewImages.map((src, idx) => (
              <div key={idx} className="col-6 col-md-3">
                <div 
                  style={{
                    aspectRatio: '1',
                    overflow: 'hidden',
                    borderRadius: '8px',
                    border: '1px solid #ff2f55'
                  }}
                >
                  <img 
                    src={src} 
                    alt={`Preview ${idx}`}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CloudinaryUploadImage;
