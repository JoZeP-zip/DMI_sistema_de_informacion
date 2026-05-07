import React, { useEffect, useState } from 'react';
import './styles/App.css';
import RegistroVehiculo from './componentes/RegistroVehiculo.js';
import Contacto from './componentes/Contacto.js';
import AgendarCita from './componentes/AgendarCita.js';
import Catalogo from './componentes/Catalogo.js';
import Registrodeusuario from './componentes/RegistroUsuario.js';

// Imágenes del carrusel
const heroSlides = [
  '/assets/images/lamborghini.jpg',
  '/assets/images/fotoautos.jpg',
  '/assets/images/porche.jpg',
];

// Componente reutilizable para el botón de volver
const BackButton = ({ onClick }) => (
  <button className="btn outline" onClick={onClick}>
    ← Volver al Inicio
  </button>
);

function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [view, setView] = useState('inicio');
  const [currentSlide, setCurrentSlide] = useState(0);

  // CONTROLAR SCROLL SEGÚN VISTA
  useEffect(() => {
    document.body.style.overflow = view === 'inicio' ? 'hidden' : 'auto';
  }, [view]);

  // CARRUSEL
  useEffect(() => {
    if (view !== 'inicio') return;
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % heroSlides.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [view]);

  const goToInicio = () => {
    setView('inicio');
    setMenuOpen(false);
  };

  return (
    <>
      {/* NAV */}
      <nav className="main-nav">
        <div className="nav-container">
          <a href="#inicio" className="logo" onClick={goToInicio}>
            <img
              src="/assets/images/LOGOGOTY.png"
              alt="Disol Motors Logo"
              style={{ height: '60px', width: 'auto' }}
            />
          </a>

          {/* Botón hamburguesa para mobile */}
          <button
            className="menu-toggle"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Abrir menú"
          >
            ☰
          </button>

          <ul className={`nav-links ${menuOpen ? 'active' : ''}`}>
            <li>
              <a href="#inicio" onClick={() => {
                goToInicio();
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}>
                Inicio
              </a>
            </li>

            <li>
              <a href="#catalogo" onClick={(e) => { e.preventDefault(); setView('catalogo'); setMenuOpen(false); }}>
                Catálogo
              </a>
            </li>

            <li>
              <a href="#citas" onClick={(e) => { e.preventDefault(); setView('citas'); setMenuOpen(false); }}>
                Agendar Cita
              </a>
            </li>

            <li>
              <a href="#contacto" onClick={(e) => { e.preventDefault(); setView('contacto'); setMenuOpen(false); }}>
                Contacto
              </a>
            </li>

            <li>
              <a href="#registro-usuario" onClick={(e) => { e.preventDefault(); setView('registro_usuario'); setMenuOpen(false); }}>
                Registrar Usuario
              </a>
            </li>

            <li>
              <a href="#registro" onClick={(e) => { e.preventDefault(); setView('registro'); setMenuOpen(false); }}>
                Registrar Vehículos
              </a>
            </li>
          </ul>
        </div>
      </nav>

      {/* VISTA: AGENDAR CITA */}
      {view === 'citas' && (
        <section className="section no-scroll-section">
          <AgendarCita />
          <BackButton onClick={goToInicio} />
        </section>
      )}

      {/* VISTA: REGISTRO DE VEHÍCULO */}
      {view === 'registro' && (
        <section className="section no-scroll-section">
          <RegistroVehiculo />
          <BackButton onClick={goToInicio} />
        </section>
      )}

      {/* VISTA: CATÁLOGO */}
      {view === 'catalogo' && (
        <section className="section no-scroll-section">
          <Catalogo />
          <BackButton onClick={goToInicio} />
        </section>
      )}

      {/* VISTA: CONTACTO */}
      {view === 'contacto' && (
        <section className="section no-scroll-section">
          <Contacto />
          <BackButton onClick={goToInicio} />
        </section>
      )}

      {/* VISTA: REGISTRO DE USUARIO */}
      {view === 'registro_usuario' && (
        <section className="section no-scroll-section">
          <Registrodeusuario />
          <BackButton onClick={goToInicio} />
        </section>
      )}

      {/* VISTA: INICIO */}
      {view === 'inicio' && (
        <>
          {/* HERO */}
          <header
            id="inicio"
            className="hero no-scroll-section"
            style={{
              backgroundImage: `url(${heroSlides[currentSlide]})`,
              transition: 'background-image 0.8s ease-in-out',
            }}
          >
            <div className="overlay"></div>
            <div className="hero-content">
              <h1>Disol Motors Injection</h1>
              <p className="slogan">
                Rendimiento que se siente • Potencia que se ve
              </p>
              <div className="cta-buttons">
                <a href="#galeria" className="btn primary">Ver Trabajos</a>
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '20px' }}>
                {heroSlides.map((_, i) => (
                  <span
                    key={i}
                    onClick={() => setCurrentSlide(i)}
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      background: i === currentSlide ? '#fff' : 'rgba(255,255,255,0.4)',
                      cursor: 'pointer',
                      display: 'inline-block',
                      transition: 'background 0.3s',
                    }}
                  />
                ))}
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