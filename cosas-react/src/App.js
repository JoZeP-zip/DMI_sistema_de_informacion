import React, { useEffect, useState } from 'react';
import './styles/App.css';
import RegistroVehiculo from './componentes/RegistroVehiculo.js';
import Contacto from './componentes/Contacto.js';
import AgendarCita from './componentes/AgendarCita.js';
import Catalogo from './componentes/Catalogo.js';

// Imágenes del carrusel
const heroSlides = [
  '/assets/images/carmaroblanco.jpg',
  '/assets/images/fotoautos.jpg',
  '/assets/images/rx8.jpg',
];

function App() {
  const [menuOpen] = useState(false);
  const [view, setView] = useState('inicio');
  const [currentSlide, setCurrentSlide] = useState(0);

  //BLOQUEAR SCROLL
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, []);

  //CARRUSEL 
  useEffect(() => {
    if (view !== 'inicio') return;
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % heroSlides.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [view]);


  return (
    <>
      {/* NAV */}
      <nav className="main-nav">
        <div className="nav-container">
          <a href="#inicio" className="logo" onClick={() => setView('inicio')}>
            <img src="/assets/images/LOGOGOTY.png" alt="Disol Motors Logo" style={{ height: '60px', width: 'auto' }} />
          </a>

          <ul className={`nav-links ${menuOpen ? 'active' : ''}`}>
            <li><a href="#inicio" onClick={() => setView('inicio')}>Inicio</a></li>
            
            <li>
              <a href="#catalogo" onClick={(e) => {
                e.preventDefault();
                setView('catalogo');
              }}>Catálogo</a>
            </li>

            <li><a href="#galeria">Galería</a></li>

            <li>
              <a href="#citas" onClick={(e) =>{
                e.preventDefault();
                setView('citas');
              }}>Agendar Cita</a>
            </li>

            <li>
              <a href="#contacto" onClick={(e) => {
                e.preventDefault();
                setView('contacto');
              }}>Contacto</a>
            </li>

            <li>
              <a href="#registro" onClick={(e) => {
                e.preventDefault();
                setView('registro');
              }}>Registrar Vehículos</a>
            </li>
          </ul>
        </div>
      </nav>

      {/* VISTA: AGENDAR CITA */}
      {view === 'citas' && (
        <section className="section no-scroll-section">
          <AgendarCita />
          <button className="btn outline" onClick={() => setView('inicio')}>
            ← Volver al Inicio
          </button>
        </section>
      )}

      {/* VISTA REGISTRO */}
      {view === 'registro' && (
        <section className="section no-scroll-section">
          <RegistroVehiculo />
          <button className="btn outline" onClick={() => setView('inicio')}>
            ← Volver
          </button>
        </section>
      )}

      {/* VISTA: CATÁLOGO */}
      {view === 'catalogo' && (
        <section className="section no-scroll-section">
          <Catalogo />
          <button className="btn outline" onClick={() => setView('inicio')}>
            ← Volver al Inicio
          </button>
        </section>
      )}

      {/* VISTA CONTACTO */}
      {view === 'contacto' && (
        <section className="section no-scroll-section">
          <Contacto />
          <button className="btn outline" onClick={() => setView('inicio')}>
            ← Volver
          </button>
        </section>
      )}

      {/* VISTA INICIO */}
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