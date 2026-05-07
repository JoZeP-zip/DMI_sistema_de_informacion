import React, { useState } from 'react';
import './RegistroUsuario.css'; // Importación del CSS externo

const RegistroUsuario = () => {
  const [formData, setFormData] = useState({
    nombre: '',
    email: '',
    password: '',
    confirmPassword: ''
  });

  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!formData.nombre || !formData.email || !formData.password) {
      setError('Por favor, completa todos los campos.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    // Simulación de registro exitoso
    console.log('Usuario registrado:', formData);
    setSuccess(true);
    setFormData({ nombre: '', email: '', password: '', confirmPassword: '' });
  };

  return (
    <div className="registro-container">
      <div className="registro-card">
        <h2 className="registro-title">Registro de Usuario</h2>
        
        {error && <div className="message error-msg">{error}</div>}
        {success && <div className="message success-msg">¡Cuenta creada con éxito!</div>}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Nombre Completo</label>
            <input
              type="text"
              name="nombre"
              className="input-field"
              value={formData.nombre}
              onChange={handleChange}
              placeholder="Ej: Juan Pérez"
            />
          </div>

          <div className="input-group">
            <label>Email</label>
            <input
              type="email"
              name="email"
              className="input-field"
              value={formData.email}
              onChange={handleChange}
              placeholder="correo@empresa.com"
            />
          </div>

          <div className="input-group">
            <label>Contraseña</label>
            <input
              type="password"
              name="password"
              className="input-field"
              value={formData.password}
              onChange={handleChange}
              placeholder="Mínimo 6 caracteres"
            />
          </div>

          <div className="input-group">
            <label>Confirmar Contraseña</label>
            <input
              type="password"
              name="confirmPassword"
              className="input-field"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Repite tu contraseña"
            />
          </div>

          <button type="submit" className="btn-submit">
            Crear Cuenta
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegistroUsuario;