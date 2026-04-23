import React, { useEffect, useState } from 'react';
import './App.css';
import RegistroVehiculo from './componentes/RegistroVehiculo.js';
import Contacto from './componentes/Contacto.js';  

function App() {
  const [menuOpen] = useState(false);
  const [view, setView] = useState('inicio');

  // 🔒 BLOQUEAR SCROLL
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, []);

  return (
    <>
      {/* NAV */}
      <nav className="main-nav">
        <div className="nav-container">
          <a href="#" className="logo" onClick={() => setView('inicio')}>
            Disol<span>Motors</span>
          </a>

          <ul className={`nav-links ${menuOpen ? 'active' : ''}`}>
            <li><a href="#inicio" onClick={() => setView('inicio')}>Inicio</a></li>
            <li><a href="#galeria">Galería</a></li>
            <li>
              <a href="#" onClick={(e) => {
                e.preventDefault();
                setView('contacto');
              }}>contacto</a>
              </li>
            <li>
              
              <a href="#registro" onClick={(e) => {
                e.preventDefault();
                setView('registro');
              }}>
                Registrar Vehículos
              </a>
            </li>
          </ul>
        </div>
      </nav>

      {view === 'registro' && (
        <section className="section no-scroll-section">
          <RegistroVehiculo />
          <button className="btn outline" onClick={() => setView('inicio')}>
            ← Volver
          </button>
        </section>
      )}

        {view === 'contacto' && (
          <section className="section no-scroll-section">
            <contacto />
            <button className="btn outline" onClick={() => setView('inicio')}>
              ← Volver
            </button>
          </section>
        )}

        {view === 'inicio' && (
          
        <>
          {/* HERO */}
          <header id="inicio" className="hero no-scroll-section">
            <div className="overlay"></div>
            <div className="hero-content">
              <h1>Disol Motors Injection</h1>
              <p className="slogan">
                Rendimiento que se siente • Potencia que se ve
              </p>

              <div className="cta-buttons">
                <a href="#galeria" className="btn primary">Ver Trabajos</a>
              </div>
            </div>
          </header>

          {/* GALERÍA */}
          <section id="galeria" className="section galeria no-scroll-section">
            <h2>Trabajos Realizados</h2>

            <div className="gallery-grid">
              <div className="gallery-item item-1"></div>
              <div className="gallery-item item-2"></div>
              <div className="gallery-item item-3"></div>
              <div className="gallery-item item-4"></div>
              <div className="gallery-item item-5"></div>
              <div className="gallery-item item-6"></div>
            </div>
          </section>
          
        </>
      )}

      {/* FOOTER */}
      <footer>
        <p>© 2026 Disol Motors Injection</p>
      </footer>
    </>
  );
}

export default App;