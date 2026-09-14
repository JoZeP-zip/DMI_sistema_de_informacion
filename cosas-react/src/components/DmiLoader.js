import React from 'react';
import './DmiLoader.css';

export default function DmiLoader({
  visible,
  text = 'DIAGNOSTICANDO SISTEMA...',
}) {
  if (!visible) return null;

  return (
    <div className="dmi-loader-overlay" role="status" aria-live="polite">
      <div className="dmi-loader-workshop">
        <div className="dmi-loader-header">
          <span className="dmi-loader-led" />
          <span>DMI MOTORS / WORKSHOP</span>
        </div>

        <div className="dmi-loader-machine">
          <div className="dmi-gear dmi-gear-large">⚙</div>
          <div className="dmi-gear dmi-gear-small">⚙</div>
          <div className="dmi-wrench">🔧</div>
        </div>

        <strong>{text}</strong>

        <div className="dmi-loader-progress">
          <span />
        </div>

        <small>Verificando módulos del taller</small>
      </div>
    </div>
  );
}