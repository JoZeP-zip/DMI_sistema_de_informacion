import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const getApiBaseUrl = () => {
    const { protocol, hostname } = window.location;

    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return "http://localhost:8000";
    }

    if (hostname.includes("app.github.dev")) {
      return `${protocol}//${hostname.replace(/-\d+\.app\.github\.dev$/, "-8000.app.github.dev")}`;
    }

    return "";
  };

  const API_BASE_URL = getApiBaseUrl();

  const guardarSesion = (token, role, email) => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('email');
    localStorage.removeItem('nombre');
    localStorage.removeItem('dmiSessionStartedAt');

    if (token) localStorage.setItem('token', token);
    if (role) localStorage.setItem('role', role);
    if (email) localStorage.setItem('email', email);
    if (token) localStorage.setItem('dmiSessionStartedAt', new Date().toISOString());
  };

  const handleLogin = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch(`${API_BASE_URL}/login-react`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        alert(data.detail || data.message || 'Credenciales invalidas');
        return;
      }

      const token = data.access_token || data.token;
      const role = data.role || data.rol || 'usuario';

      guardarSesion(token, role, email);

      if (role === 'admin') {
        navigate('/dashboard-admin');
      } else {
        navigate('/home');
      }

    } catch (error) {
      console.warn("Error al conectar con el servidor:", error);
      alert("No se pudo conectar con el servidor");
    }
  };

  return (
    <div style={{
      maxWidth: '400px',
      margin: '50px auto',
      padding: '20px',
      border: '1px solid #ccc',
      borderRadius: '8px',
      backgroundColor: '#fff',
      color: '#333',
      fontFamily: 'sans-serif'
    }}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>
        Iniciar Sesion
      </h2>

      <form onSubmit={handleLogin}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{
            fontWeight: 'bold',
            display: 'block',
            marginBottom: '5px'
          }}>
            Correo Electronico:
          </label>

          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="admin@disolmotors.com"
            style={{
              width: '100%',
              padding: '10px',
              boxSizing: 'border-box'
            }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{
            fontWeight: 'bold',
            display: 'block',
            marginBottom: '5px'
          }}>
            Contrasena:
          </label>

          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="********"
            style={{
              width: '100%',
              padding: '10px',
              boxSizing: 'border-box'
            }}
          />
        </div>

        <button
          type="submit"
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: '#2b4485',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          Ingresar al Sistema
        </button>
      </form>
    </div>
  );
}

export default Login;
