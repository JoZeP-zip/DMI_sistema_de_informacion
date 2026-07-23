import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState(null); // { title, message }
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

    const correoLimpio = email.trim();
    const passLimpio = password.trim();

    if (!correoLimpio || !passLimpio) {
      setNotice({
        title: 'Completa tus datos',
        message: 'Ingresa tu correo electronico y tu contrasena para poder iniciar sesion.',
      });
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/login-react`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: "include",
        body: JSON.stringify({ email: correoLimpio, password: passLimpio }),
      });

      const data = await response.json();

      if (!response.ok) {
        setNotice({
          title: 'No se pudo iniciar sesion',
          message: data.detail || data.message || 'Credenciales invalidas. Verifica tu correo y contrasena.',
        });
        return;
      }

      const token = data.access_token || data.token;
      const role = String(data.role || data.rol || 'usuario').toLowerCase();

      guardarSesion(token, role, correoLimpio);

      if (role === 'admin') {
        navigate('/dashboard-admin');
      } else if (role === 'mecanico' || role === 'mecanico_taller') {
        navigate('/home');
      } else {
        navigate('/home');
      }

    } catch (error) {
      console.warn("Error al conectar con el servidor:", error);
      setNotice({
        title: 'Error de conexion',
        message: 'No se pudo conectar con el servidor. Intenta nuevamente en unos segundos.',
      });
    } finally {
      setLoading(false);
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
      fontFamily: 'sans-serif',
      position: 'relative',
    }}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>
        Iniciar Sesion
      </h2>

      <form onSubmit={handleLogin} noValidate>
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
          disabled={loading}
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: '#2b4485',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold',
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? 'Ingresando...' : 'Ingresar al Sistema'}
        </button>
      </form>

      {notice && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 999999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            background: 'rgba(0,0,0,0.88)',
            backdropFilter: 'blur(6px)',
          }}
          onClick={() => setNotice(null)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 'min(420px, 100%)',
              background: 'linear-gradient(160deg, rgba(18,0,0,0.98), rgba(0,0,0,0.99))',
              border: '1px solid rgba(255,0,0,0.4)',
              boxShadow: '0 0 0 1px rgba(255,0,0,0.08), 0 30px 80px rgba(0,0,0,0.7), 0 0 60px rgba(255,0,0,0.18)',
              borderRadius: '6px',
              padding: '30px 28px',
              fontFamily: 'sans-serif',
              color: '#f0f0f0',
            }}
          >
            <p style={{
              margin: '0 0 10px',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '3px',
              textTransform: 'uppercase',
              color: '#ff5b5b',
            }}>
              Aviso
            </p>
            <h3 style={{
              margin: '0 0 12px',
              fontSize: '22px',
              fontWeight: 700,
              letterSpacing: '0.5px',
            }}>
              {notice.title}
            </h3>
            <p style={{
              margin: '0 0 24px',
              fontSize: '14px',
              lineHeight: 1.6,
              color: '#cfcfcf',
            }}>
              {notice.message}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => setNotice(null)}
                style={{
                  padding: '10px 22px',
                  background: '#e63946',
                  border: '1px solid #e63946',
                  borderRadius: '4px',
                  color: '#fff',
                  fontWeight: 700,
                  letterSpacing: '1px',
                  cursor: 'pointer',
                }}
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Login;