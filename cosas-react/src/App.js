import React, { useEffect, useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min';
import './styles/App.css';

import RegistroVehiculo from './js/RegistrarUnidad.js';
import Contacto from './js/Contacto.js';
import AgendarCita from './js/AgendarCita.js';
import Catalogo from './js/Catalogo.js';
import DashboardAdmin from './js/DashboardAdmin.js';

// Componente de Login Integrado a la Estética DMI
const LoginView = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('https://musical-bassoon-wrx6qgr9gvp9f7v-8800.app.github.dev/login-react', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        localStorage.setItem("token", data.token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("email", data.email);
        onLoginSuccess({ email: data.email, role: data.role });
      }
    } catch (err) {
      setError('No se pudo conectar con el servidor.');
    }
  };

  return (
    <div className="mx-auto" style={{ maxWidth: '400px' }}>
      <h3 className="text-center text-uppercase fw-black mb-4">
        Control de <span className="text-danger">Acceso</span>
      </h3>
      {error && <div className="alert alert-danger small py-2 rounded-0 border-danger bg-black text-danger">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="form-label text-muted small fw-bold">CORREO ELECTRÓNICO</label>
          <input 
            type="email" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required 
          />
        </div>
        <div className="mb-4">
          <label className="form-label text-muted small fw-bold">CONTRASEÑA</label>
          <input 
            type="password" 
            className="form-control bg-black text-white border-secondary rounded-0 focus-red"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required 
          />
        </div>
        <button type="submit" className="btn btn-danger w-100 rounded-0 fw-bold py-2 tracking-widest">
          INGRESAR
        </button>
      </form>
    </div>
  );
};

// Panel exclusivo para el Usuario Común (Cliente)
const DashboardUsuario = ({ user }) => (
  <div>
    <h3 className="text-uppercase fw-black border-bottom border-danger pb-2 mb-4">
      Mi <span className="text-danger">Garaje</span>
    </h3>
    <p>Hola, <span className="text-danger fw-bold">{user.email}</span>. Bienvenido a tu espacio personal.</p>
    <div className="p-4 bg-black border border-secondary mt-3">
      <h6 className="fw-bold text-uppercase tracking-widest text-muted mb-3">Estado de tu Vehículo</h6>
      <p className="mb-1">🚗 **Porsche 911 GT3** — *En Diagnóstico de Inyección*</p>
      <span className="badge bg-danger rounded-0">TRABAJO EN PROCESO</span>
    </div>
  </div>
);

// --- FIN DE LOS NUEVOS COMPONENTES ---

const heroSlides = [
  './assets/images/motorlike.jpg',
  './assets/images/contactos.jpg',
  './assets/images/servicios.jpg',
];

const BackButton = ({ onClick, user }) => (
  <div className="text-center mt-5">
    <button
      className="btn btn-danger px-5 py-2 fw-bold shadow hover-grow"
      onClick={onClick}
      style={{ borderRadius: '50px' }}
    >
      {user ? '← VOLVER AL PANEL' : '← VOLVER AL INICIO'}
    </button>
  </div>
);

function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [view, setView] = useState('inicio');
  const [currentSlide, setCurrentSlide] = useState(0);
  const [user, setUser] = useState(null);

  const [selectedProject, setSelectedProject] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const email = localStorage.getItem("email");

    if (token && role && email) {
      setUser({ email, role });
    }
  }, []);

  useEffect(() => {
    if (view === 'admin-dashboard' && (!user || user.role !== 'admin')) {
      setView('login');
    }
    if (view === 'user-dashboard' && (!user || user.role !== 'usuario')) {
      setView('login');
    }
  }, [view, user]);

  useEffect(() => {
    document.body.style.overflow = view === 'inicio' ? 'hidden' : 'auto';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [view]);

  useEffect(() => {
    const handlePopState = (e) => {
      if (!e.state || !e.state.section) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        window.history.replaceState(null, '', '/');  // 👈 replaceState va AQUÍ
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    if (view !== 'inicio') return;
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % heroSlides.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [view]);

  const goToInicio = () => {
    setMenuOpen(false);
    if (user) {
      setView(user.role === 'admin' ? 'admin-dashboard' : 'user-dashboard');
    } else {
      setView('inicio');
      // Si ya estamos en inicio, hacer scroll al top
      window.scrollTo({ top: 0, behavior: 'smooth' });
      window.history.replaceState(null, '', '/');
    }
  };

  // Manejadores de autenticación
  const handleLoginSuccess = (userData) => {
    setUser(userData);
    // Redirección inteligente inmediata según el rol
    if (userData.role === 'admin') {
      setView('admin-dashboard');
    } else {
      setView('user-dashboard');
    }
  };

  const handleLogout = () => {
    localStorage.clear(); 
    setUser(null);
    setView('inicio');
  };

  return (
    <div className="bg-black text-white min-vh-100 d-flex flex-column">

      {/* NAVBAR */}
      <nav className="navbar navbar-expand-lg navbar-dark bg-black sticky-top border-bottom border-danger py-3">
        <div className="container">

          <button className="navbar-brand bg-transparent border-0 p-0" onClick={goToInicio}>
            <img
              src="/assets/images/logoempresaXD.png"
              alt="DMI Logo"
              className="img-fluid"
              style={{ height: '50px', objectFit: 'contain' }}
            />
          </button>

          <button className="navbar-toggler border-0" type="button" onClick={() => setMenuOpen(!menuOpen)}>
            <span className="navbar-toggler-icon"></span>
          </button>

          <div className={`collapse navbar-collapse ${menuOpen ? 'show' : ''}`}>
            <ul className="navbar-nav ms-auto align-items-center gap-3">

              {['INICIO', 'CATÁLOGO', 'CITAS', 'CONTACTO'].map((text) => (
                <li className="nav-item" key={text}>
                  <button
                    className="nav-link fw-bold p-2 nav-hover-red bg-transparent border-0"
                    onClick={() => {
                      const v = text.toLowerCase().replace('á', 'a');
                      setView(v);
                      if (v === 'inicio') {
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                        window.history.replaceState(null, '', '/');
                      }
                      setMenuOpen(false);
                    }}
                  >
                    {text}
                  </button>
                </li>
              ))}

              {/* NUEVO: Accesos rápidos en el menú dinámico según el Rol */}
              {user && user.role === 'admin' && (
                <li className="nav-item">
                  <button className="nav-link text-danger fw-black p-2" onClick={() => setView('admin-dashboard')}>
                    PANEL ADMIN
                  </button>
                </li>
              )}
              
              {user && user.role === 'usuario' && (
                <li className="nav-item">
                  <button className="nav-link text-danger fw-black p-2" onClick={() => setView('user-dashboard')}>
                    MI GARAGE
                  </button>
                </li>
              )}

              <li className="nav-item">
                <button
                  className="btn btn-danger px-4 rounded-0 fw-bold shadow-sm"
                  onClick={() => {
                    setView('registro');
                    setMenuOpen(false);
                  }}
                >
                  REGISTRAR UNIDAD
                </button>
              </li>

              {/* NUEVO: Botón Dinámico de Login / Logout */}
              <li className="nav-item">
                {user ? (
                  <button className="btn btn-outline-light px-3 rounded-0 fw-bold btn-sm" onClick={handleLogout}>
                    CERRAR SESIÓN
                  </button>
                ) : (
                  <button className="btn btn-outline-danger px-3 rounded-0 fw-bold btn-sm" onClick={() => setView('login')}>
                    LOGIN
                  </button>
                )}
              </li>

            </ul>
          </div>
        </div>
      </nav>

      {/* CONTENEDOR PRINCIPAL DE COMPONENTES */}
      <main className="flex-grow-1">

        {view !== 'inicio' && (
          <section className="container py-5">
            <div className="row justify-content-center">
              <div className="col-12 col-xl-10 animate-slide-in">
                <div className="card bg-dark text-white border-danger border-opacity-50 shadow-lg p-4 p-md-5">

                  {view === 'citas' && <AgendarCita />}
                  {view === 'registro' && <RegistroVehiculo />}
                  {view === 'catalogo' && <Catalogo />}
                  {view === 'contacto' && <Contacto />}
                  
                  {/* NUEVAS VISTAS CONTROLADAS */}
                  {view === 'login' && <LoginView onLoginSuccess={handleLoginSuccess} />}
                  {view === 'admin-dashboard' && <DashboardAdmin />}
                  {view === 'user-dashboard' && <DashboardUsuario user={user} />}

                  <BackButton onClick={goToInicio} user={user}/>
                </div>
              </div>
            </div>
          </section>
        )}

        {view === 'inicio' && (
          <>
            {/* HERO */}
            <header className="hero-viewport">
              <div
                className="hero-background"
                style={{ backgroundImage: `url(${heroSlides[currentSlide]})` }}
              ></div>
              <div className="hero-overlay"></div>
              <div className="container position-relative z-index-2 text-center animate-fade-up">
                <h1 className="hero-title">
                  DISOL <span className="text-danger">MOTORS</span>
                </h1>
                <p className="hero-subtitle mb-5">
                  Mecánica de Precisión • Inyección Electrónica • Performance
                </p>
                <div className="cta-wrapper">
                  <button
                    className="btn-racing px-5 py-3"
                    onClick={() => {
                      window.history.pushState({ section: 'galeria' }, '', '#galeria');
                      document.getElementById('galeria').scrollIntoView({ behavior: 'smooth' });
                    }}
                  >
                    EXPLORAR GALERÍA
                  </button>
                </div>
              </div>

              {/* BARRAS DEL SLIDE */}
              <div className="slide-progress">
                {heroSlides.map((_, i) => (
                  <div
                    key={i}
                    className={`progress-bar-item ${i === currentSlide ? 'active' : ''}`}
                    onClick={() => setCurrentSlide(i)}
                  ></div>
                ))}
              </div>
            </header>

            {/* CUADRÍCULA DE IMÁGENES CON SCROLL INTERNO Y MODAL CON CARRUSEL */}
            <section id="galeria" className="py-5 bg-black">
              <div className="container py-4">
                <h2 className="text-center mb-5 fw-black text-uppercase">
                  Proyectos <span className="text-danger">Elite</span>
                </h2>

                {/* Contenedor con scroll para la cuadrícula */}
                <div 
                  className="pe-2 custom-gallery-scroll" 
                  style={{ maxHeight: '460px', overflowY: 'auto', overflowX: 'hidden' }}
                >
                  <div className="row g-3">
                    {[
                      { 
                        // RESTRUCTURADO: Ahora maneja un arreglo de 3 imágenes para el carrusel
                        imagenes: [
                          '/assets/images/mundoejecutivo.jpg', 
                          '/assets/images/mundocarrito.jpg', 
                          '/assets/images/porche.jpg'
                        ], 
                        titulo: 'Mundo Ejecutivo', 
                        descripcion: 'Optimización de software y diagnóstico computarizado para flotas empresariales.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/porche.jpg', 
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/mundocarrito.jpg'
                        ], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibración avanzada del sistema de inyección electrónica y pruebas de presión en tiempo real.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/porche.jpg', 
                          '/assets/images/Ambessa_1.jpg'
                        ], 
                        titulo: 'Lamborghini Aventador', 
                        descripcion: 'Mantenimiento de alta precisión en el sistema de admisión y mapeo de ECU para rendimiento extremo.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/mundocarrito.jpg', 
                          '/assets/images/mundoejecutivo.jpg', 
                          '/assets/images/Mel.jpg'
                        ], 
                        titulo: 'Diagnóstico General', 
                        descripcion: 'Escaneo completo de módulos electrónicos mediante tecnología OBD-II de última generación.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/Mel.jpg', 
                          '/assets/images/Ambessa_1.jpg', 
                          '/assets/images/porche.jpg'
                        ], 
                        titulo: 'Proyecto Mel', 
                        descripcion: 'Ajustes personalizados de alto rendimiento y restauración de componentes críticos del motor.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/Ambessa_1.jpg', 
                          '/assets/images/Mel.jpg', 
                          '/assets/images/lamborghini.jpg'
                        ], 
                        titulo: 'Unidad de Potencia', 
                        descripcion: 'Modificación y ensamble de sistemas de inyección a medida para competencia.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/porche.jpg', 
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/mundocarrito.jpg'
                        ], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibración avanzada del sistema de inyección electrónica y pruebas de presión en tiempo real.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/porche.jpg', 
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/mundocarrito.jpg'
                        ], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibración avanzada del sistema de inyección electrónica y pruebas de presión en tiempo real.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/porche.jpg', 
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/mundocarrito.jpg'
                        ], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibración avanzada del sistema de inyección electrónica y pruebas de presión en tiempo real.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/porche.jpg', 
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/mundocarrito.jpg'
                        ], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibración avanzada del sistema de inyección electrónica y pruebas de presión en tiempo real.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/porche.jpg', 
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/mundocarrito.jpg'
                        ], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibración avanzada del sistema de inyección electrónica y pruebas de presión en tiempo real.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/porche.jpg', 
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/mundocarrito.jpg'
                        ], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibración avanzada del sistema de inyección electrónica y pruebas de presión en tiempo real.' 
                      },
                      { 
                        imagenes: [
                          '/assets/images/porche.jpg', 
                          '/assets/images/lamborghini.jpg', 
                          '/assets/images/mundocarrito.jpg'
                        ], 
                        titulo: 'Porsche 911 GT3', 
                        descripcion: 'Calibración avanzada del sistema de inyección electrónica y pruebas de presión en tiempo real.' 
                      }
                    ].map((proyecto, index) => (
                      <div key={index} className="col-6 col-md-4">
                        <div 
                          className="gallery-card border-danger position-relative overflow-hidden shadow" 
                          style={{ aspectRatio: '16/9', cursor: 'pointer' }}
                          onClick={() => {
                            setSelectedProject(proyecto);
                            setShowModal(true);
                          }}
                        >
                          {/* Muestra la primera imagen del arreglo como portada en la cuadrícula */}
                          <img 
                            src={proyecto.imagenes[0]} 
                            alt={proyecto.titulo} 
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          />
                          
                          <div className="gallery-hover-info">
                            <small>VER DETALLES</small>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* INTERFAZ EMERGENTE (MODAL REFORMADO CON CARRUSEL DE 3 IMÁGENES) */}
              {showModal && selectedProject && (
                <div className="modal fade show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 1050 }}>
                  <div className="modal-dialog modal-dialog-centered">
                    <div className="modal-content bg-dark text-white border border-danger rounded-0 shadow-lg">
                      
                      <div className="modal-header border-bottom border-danger border-opacity-50">
                        <h5 className="modal-title fw-black text-uppercase">
                          Detalles del <span className="text-danger">Proyecto</span>
                        </h5>
                        <button type="button" className="btn-close btn-close-white" onClick={() => setShowModal(false)}></button>
                      </div>

                      <div className="modal-body p-4">
                        
                        {/* NUEVO: PEQUEÑO CARRUSEL DE 3 IMÁGENES */}
                        <div id="carouselProjectDetails" className="carousel slide mb-3 border border-secondary" data-bs-ride="carousel" style={{ aspectRatio: '16/9' }}>
                          <div className="carousel-inner h-100">
                            {selectedProject.imagenes.map((imgUrl, idx) => (
                              <div key={idx} className={`carousel-item h-100 ${idx === 0 ? 'active' : ''}`}>
                                <img 
                                  src={imgUrl} 
                                  className="d-block w-100 h-100" 
                                  alt={`Slide ${idx + 1}`} 
                                  style={{ objectFit: 'cover' }}
                                />
                              </div>
                            ))}
                          </div>
                          
                          {/* Flecha Izquierda */}
                          <button className="carousel-control-prev" type="button" data-bs-target="#carouselProjectDetails" data-bs-slide="prev">
                            <span className="carousel-control-prev-icon" aria-hidden="true"></span>
                            <span className="visually-hidden">Anterior</span>
                          </button>
                          
                          {/* Flecha Derecha */}
                          <button className="carousel-control-next" type="button" data-bs-target="#carouselProjectDetails" data-bs-slide="next">
                            <span className="carousel-control-next-icon" aria-hidden="true"></span>
                            <span className="visually-hidden">Siguiente</span>
                          </button>
                        </div>

                        <h4 className="fw-bold text-uppercase tracking-wider mb-2 text-danger">{selectedProject.titulo}</h4>
                        <p className="text-muted small mb-0">{selectedProject.descripcion}</p>
                      </div>

                      <div className="modal-footer border-top border-danger border-opacity-25">
                        <button type="button" className="btn btn-danger rounded-0 fw-bold px-4" onClick={() => setShowModal(false)}>
                          CERRAR
                        </button>
                      </div>

                    </div>
                  </div>
                </div>
              )}
            </section>
          </>
        )}

      </main>

      <footer className="bg-black py-4 border-top border-danger border-opacity-25 text-center">
        <p className="small text-muted mb-0 tracking-widest">
          © 2026 <span className="bg-black py-4 border-top border-danger border-opacity-25 text-center">DMI</span> • HIGH PERFORMANCE SERVICE
        </p>
      </footer>

    </div>
  );
}

export default App;