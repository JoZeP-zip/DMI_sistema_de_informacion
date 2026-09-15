import React from 'react';
import './DmiLoader.css';

export default function DmiLoader({ visible, text = 'CARGANDO SISTEMA...' }) {
  if (!visible) return null;

  return (
    <div className="dmi-loader-overlay" role="status" aria-live="polite" aria-label={text}>
      <div className="dmi-loader-card">
        <div className="dmi-loader-brand">
          <span className="dmi-loader-mark">DMI</span>
          <span className="dmi-loader-brand-name">MOTORS / WORKSHOP</span>
        </div>
        <div className="dmi-loader-visual" aria-hidden="true">
          <div className="dmi-loader-orbit dmi-loader-orbit-one" />
          <div className="dmi-loader-orbit dmi-loader-orbit-two" />
          <div className="dmi-loader-gear">⚙</div>
          <div className="dmi-loader-wrench">⚒</div>
        </div>
        <div className="dmi-loader-copy">
          <strong>{text}</strong>
          <span>Preparando tu taller</span>
        </div>
        <div className="dmi-loader-progress" aria-hidden="true"><span /></div>
        <small className="dmi-loader-caption">DISOL MOTORS · HIGH PERFORMANCE SERVICE</small>
      </div>
    </div>
  );
}
