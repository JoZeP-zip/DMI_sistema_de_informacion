import React, { useEffect, useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min';
import './styles/App.css';

import RegistroVehiculo from './js/RegistrarUnidad.js';
import Contacto from './js/Contacto.js';
import AgendarCita from './js/AgendarCita.js';
import Catalogo from './js/Catalogo.js';
import DashboardAdmin from './js/DashboardAdmin.js';
import RegistroPrueba from './js/RegistroPrueba';



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

// Panel para el Usuario Común con Tabla de Gestión de Citas
const DashboardUsuario = ({ user }) => {
  const [citas, setCitas] = useState([
    { id: 1, fecha: '2026-06-25', hora: '09:00 AM', vehiculo: 'Porsche 911 GT3', servicio: 'Calibración de Inyección', estado: 'En Espera' },
    { id: 2, fecha: '2026-06-12', hora: '02:30 PM', vehiculo: 'Porsche 911 GT3', servicio: 'Escaneo OBD-II', estado: 'Completado' }
  ]);

  const handleCancelarCita = (id) => {
    if (window.confirm("⚠️ ¿Estás seguro de que deseas cancelar esta cita? Esta acción no se puede deshacer.")) {
      setCitas(citas.filter(cita => cita.id !== id));
      alert("Cita cancelada correctamente.");
    }
  };

  const handleEditarCita = (id) => {
    alert(`Estrategia de edición para la cita #${id}: Aquí podrás abrir un modal o redirigir al formulario.`);
  };

  return (
    <div>
      <h3 className="text-uppercase fw-black border-bottom border-danger pb-2 mb-4">
        Mi <span className="text-danger">Garaje y Citas</span>
      </h3>
      <p className="mb-4">Hola, <span className="text-danger fw-bold">{user.email}</span>. Desde aquí puedes gestionar los servicios programados para tu unidad.</p>
      
      <div className="table-responsive bg-black border border-secondary p-3">
        <h6 className="fw-bold text-uppercase tracking-widest text-muted mb-3">Historial de Citas Agendadas</h6>
        <table className="table table-dark table-hover align-middle mb-0">
          <thead>
            <tr className="text-muted small border-bottom border-danger">
              <th scope="col" className="py-3">FECHA</th>
              <th scope="col" className="py-3">HORA</th>
              <th scope="col" className="py-3">VEHÍCULO</th>
              <th scope="col" className="py-3">SERVICIO</th>
              <th scope="col" className="py-3">ESTADO</th>
              <th scope="col" className="py-3 text-center">ACCIONES</th>
            </tr>
          </thead>
          <tbody>
            {citas.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-center py-4 text-muted small">
                  No tienes citas registradas actualmente.
                </td>
              </tr>
            ) : (
              citas.map((cita) => (
                <tr key={cita.id} className="border-bottom border-secondary border-opacity-25">
                  <td className="fw-bold">{cita.fecha}</td>
                  <td>{cita.hora}</td>
                  <td><span className="text-danger">🚗</span> {cita.vehiculo}</td>
                  <td>{cita.servicio}</td>
                  <td>
                    <span className={`badge rounded-0 py-1 px-2 ${cita.estado === 'Completado' ? 'bg-secondary text-white' : 'bg-danger'}`}>
                      {cita.estado.toUpperCase()}
                    </span>
                  </td>
                  <td className="text-center">
                    <div className="d-flex justify-content-center gap-2">
                      <button 
                        className="btn btn-sm btn-outline-light rounded-0 fw-bold px-2 py-1" 
                        onClick={() => handleEditarCita(cita.id)}
                        disabled={cita.estado === 'Completado'}
                      >
                        ✏️ MODIFICAR
                      </button>
                      <button 
                        className="btn btn-sm btn-danger rounded-0 fw-bold px-2 py-1" 
                        onClick={() => handleCancelarCita(cita.id)}
                        disabled={cita.estado === 'Completado'}
                      >
                        🗑️ CANCELAR
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

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

  // Inicializar estado del usuario desde localStorage si existe
  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const email = localStorage.getItem("email");

    if (token && role && email) {
      setUser({ 
        email, 
        role: role.toLowerCase() 
      });
    }
  }, []);

  // CORREGIDO: Efecto de control de navegación estable y tolerante
  useEffect(() => {
    if (!user) {
      if (view === 'admin-dashboard' || view === 'user-dashboard') {
        setView('login');
      }
      return;
    }

    if (view === 'admin-dashboard' && user.role !== 'admin') {
      setView('login');
    }
    
    if (view === 'user-dashboard' && user.role !== 'usuario' && user.role !== 'cliente') {
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
        window.history.replaceState(null, '', '/');
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
      window.scrollTo({ top: 0, behavior: 'smooth' });
      window.history.replaceState(null, '', '/');
    }
  };

  // CORREGIDO: Normalización del rol antes de la asignación del estado
  const handleLoginSuccess = (userData) => {
    const normalizedUser = {
      ...userData,
      role: userData.role ? userData.role.toLowerCase() : 'usuario'
    };

    setUser(normalizedUser);

    if (normalizedUser.role === 'admin') {
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
                      
                      if (v === 'citas' && !user) {
                        alert("⚠️ Debes iniciar sesión para poder agendar una cita.");
                        setView('login');
                        setMenuOpen(false);
                        return;
                      }

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

              {user && user.role === 'admin' && (
                <li className="nav-item">
                  <button className="nav-link text-danger fw-black p-2 bg-transparent border-0" onClick={() => setView('admin-dashboard')}>
                    PANEL ADMIN
                  </button>
                </li>
              )}
              
              {user && (user.role === 'usuario' || user.role === 'cliente') && (
                <li className="nav-item">
                  <button className="nav-link text-danger fw-black p-2 bg-transparent border-0" onClick={() => setView('user-dashboard')}>
                    MI GARAJE
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

      {/* CONTENEDOR PRINCIPAL */}
      <main className="flex-grow-1">

        {view !== 'inicio' && (
          <section className="container py-5">
            <div className="row justify-content-center">
              <div className="col-12 col-xl-10 animate-slide-in">
                <div className="card bg-dark text-white border-danger border-opacity-50 shadow-lg p-4 p-md-5">

                  {view === 'citas' && <AgendarCita onNeedLogin={() => setView('login')} />}
                  {view === 'registro' && <RegistroVehiculo />}
                  {view === 'catalogo' && <Catalogo />}
                  {view === 'contacto' && <Contacto />}
                  
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

            {/* GALERÍA */}
            <section id="galeria" className="py-5 bg-black">
              <div className="container py-4">
                <h2 className="text-center mb-5 fw-black text-uppercase">
                  Proyectos <span className="text-danger">Elite</span>
                </h2>

                <div 
                  className="pe-2 custom-gallery-scroll" 
                  style={{ maxHeight: '460px', overflowY: 'auto', overflowX: 'hidden' }}
                >
                  <div className="row g-3">
                    {[
                      { 
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

              {/* MODAL CON CARRUSEL DE IMÁGENES */}
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
                          <button className="carousel-control-prev" type="button" data-bs-target="#carouselProjectDetails" data-bs-slide="prev">
                            <span className="carousel-control-prev-icon" aria-hidden="true"></span>
                            <span className="visually-hidden">Anterior</span>
                          </button>
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
          © 2026 • DMI • HIGH PERFORMANCE SERVICE
        </p>
      </footer>

    </div>
  );
}

export default App;