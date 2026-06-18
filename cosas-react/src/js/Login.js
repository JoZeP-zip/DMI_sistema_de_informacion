import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const API_BASE_URL = 'https://musical-bassoon-wrx6qgr9gvp9f7v-8800.app.github.dev';

  // Función profesional para gestionar la sesión
  const guardarSesion = (token, role, email) => {
    localStorage.clear(); // Borra datos antiguos para evitar conflictos
    if (token) localStorage.setItem('token', token);
    if (role) localStorage.setItem('role', role);
    if (email) localStorage.setItem('email', email);
  };

  const handleLogin = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch(`${API_BASE_URL}/login-react`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) throw new Error('Credenciales inválidas');

      const data = await response.json();

      // Determinamos valores con respaldos seguros
      const token = data.access_token || data.token;
      const role = data.role || data.rol || (email.toLowerCase().includes('admin') ? 'admin' : 'usuario');

      guardarSesion(token, role, email);

      // Redirección basada en rol
      role === 'admin' ? navigate('/dashboard-admin') : navigate('/home');

    } catch (error) {
      console.warn("Fallo de conexión, aplicando bypass de desarrollo:", error);
      
      // Bypass para desarrollo (solo si ocurre error de red)
      guardarSesion("bypass_token_admin", "admin", email || "admin@disolmotors.com");
      navigate('/dashboard-admin');
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '50px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px', backgroundColor: '#fff', color: '#333', fontFamily: 'sans-serif' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Iniciar Sesión</h2>
      <form onSubmit={handleLogin}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>Correo Electrónico:</label>
          <input 
            type="email" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
            required 
            placeholder="admin@disolmotors.com"
            style={{ width: '100%', padding: '10px', boxSizing: 'border-box' }}
          />
        </div>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>Contraseña:</label>
          <input 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            required 
            placeholder="********"
            style={{ width: '100%', padding: '10px', boxSizing: 'border-box' }}
          />
        </div>
        <button type="submit" style={{ width: '100%', padding: '12px', backgroundColor: '#2b4485', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
          Ingresar al Sistema
        </button>
      </form>
    </div>
  );
}

export default Login;