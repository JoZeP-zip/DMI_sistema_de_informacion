import React, { useMemo, useState } from 'react';

const getApiBaseUrl = () => {
  const { protocol, hostname } = window.location;

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }

  if (hostname.includes('app.github.dev')) {
    return `${protocol}//${hostname.replace(/-3000\.app\.github\.dev$/, '-8000.app.github.dev')}`;
  }

  return '';
};

const DashboardAdmin = () => {
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const frameUrl = `${apiBaseUrl}/?admin_section=panel`;

  return (
    <div className="react-admin-embed">
      <style>{`
        .react-admin-embed {
          min-height: calc(100vh - 84px);
          background: #050506;
          color: #fff;
          display: block;
          border-top: 1px solid rgba(255, 64, 87, 0.35);
        }

        .react-admin-frame-wrap {
          min-width: 0;
          background: #050506;
        }

        .react-admin-frame {
          display: block;
          width: 100%;
          height: calc(100vh - 84px);
          border: 0;
          background: #050506;
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
