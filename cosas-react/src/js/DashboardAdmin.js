import React, { useMemo, useEffect } from 'react';

const getApiBaseUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

  const { protocol, hostname } = window.location;

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }

  if (hostname.includes('app.github.dev')) {
    return `${protocol}//${hostname.replace(/-3000\.app\.github\.dev$/, '-8000.app.github.dev')}`;
  }

  return '';
};

const DashboardAdmin = ({ onLogout }) => {
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const frameUrl = `${apiBaseUrl}/?admin_section=panel`;

  useEffect(() => {
    const handleMessage = (event) => {


      if (event.data?.type === 'DMI_LOGOUT') {
        // El panel embebido ya eliminó la cookie del backend. Cerramos
        // también el estado React y volvemos directamente al inicio.
        if (onLogout) onLogout(true);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onLogout, apiBaseUrl]);

  return (
    <div className="react-admin-embed">
      <style>{`
        .react-admin-embed {
          min-height: calc(100vh - 84px);
          background:
            radial-gradient(circle at 12% 16%, rgba(255, 47, 85, .14), transparent 24%),
            radial-gradient(circle at 78% 2%, rgba(255, 47, 85, .08), transparent 28%),
            linear-gradient(180deg, #030304, #080509 52%, #030304);
          color: #fff;
          display: block;
          border-top: 1px solid rgba(255, 64, 87, 0.55);
        }

        .react-admin-frame-wrap {
          min-width: 0;
          padding: 0;
          background: transparent;
        }

        .react-admin-frame {
          display: block;
          width: 100%;
          height: calc(100vh - 84px);
          border: 0;
          background: transparent;
        }

        @media (max-width: 900px) {
          .react-admin-frame {
            height: 78vh;
          }
        }
      `}</style>

      <main className="react-admin-frame-wrap">
        <iframe
          title="Panel administrador DMI"
          src={frameUrl}
          className="react-admin-frame"
        />
      </main>
    </div>
  );
};

export default DashboardAdmin;
