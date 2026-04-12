import React, { useEffect, useState } from 'react';
import './App.css'; // Aquí pondremos todos los estilos

function App() {
  const [menuOpen, setMenuOpen] = useState(false);

  // Animación de contadores (stats)
  useEffect(() => {
    const counters = document.querySelectorAll('.number');
    
    counters.forEach(counter => {
      const target = parseInt(counter.getAttribute('data-target'));
      const increment = target / 100;
      let count = 0;

      const updateCount = () => {
        count += increment;
        if (count < target) {
          counter.textContent = Math.ceil(count);
          setTimeout(updateCount, 20);
        } else {
          counter.textContent = target;
        }
      };

      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          updateCount();
          observer.disconnect();
        }
      }, { threshold: 0.5 });

      observer.observe(counter);
    });
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    alert('¡Solicitud enviada! Nos contactaremos pronto por WhatsApp.');
    // Aquí luego puedes conectar con un backend o WhatsApp API
  };

  return (
    <>
      {/* NAVEGACIÓN */}
      <nav className="main-nav">
        <div className="nav-container">
          <a href="#" className="logo">Disol<span>Motors</span></a>
          
          <ul className={`nav-links ${menuOpen ? 'active' : ''}`}>
            <li><a href="#inicio" onClick={() => setMenuOpen(false)}>Inicio</a></li>
            <li><a href="#servicios" onClick={() => setMenuOpen(false)}>Servicios</a></li>
            <li><a href="#galeria" onClick={() => setMenuOpen(false)}>Galería</a></li>
            <li><a href="#contacto" onClick={() => setMenuOpen(false)}>Contacto</a></li>
          </ul>

          <div className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? '✕' : '☰'}
          </div>
        </div>
      </nav>

      {/* HERO */}
      <header id="inicio" className="hero">
        <div className="overlay"></div>
        <div className="hero-content">
          <h1>Disol<span>Motors Injection</span></h1>
          <p className="slogan">Rendimiento que se siente • Potencia que se ve</p>
          
          <div className="cta-buttons">
            <a href="#servicios" className="btn primary">Ver Servicios</a>
            <a href="#contacto" className="btn outline">Solicitar Turno</a>
          </div>
        </div>
        <div className="scroll-indicator">↓</div>
      </header>

      {/* SERVICIOS */}
      <section id="servicios" className="section servicios">
        <div className="section-title">
          <h2>Nuestros Servicios</h2>
          <div className="title-underline"></div>
        </div>

        <div className="cards-grid">
          <div className="service-card">
            <div className="icon">⚙️</div>
            <h3>Mecánica General</h3>
            <p>Cambio de aceite, filtros, correas, distribución, embrague, suspensión, frenos y más.</p>
          </div>

          <div className="service-card highlight">
            <div className="icon">🔥</div>
            <h3>Preparación y Tuning</h3>
            <p>Reprogramación ECU, admisión, escape, turbo, intercooler, stage 1-3, dyno.</p>
          </div>

          <div className="service-card">
            <div className="icon">🛠️</div>
            <h3>Diagnóstico Electrónico</h3>
            <p>Scanner profesional, lectura y borrado de códigos, adaptación, codificación.</p>
          </div>

          <div className="service-card">
            <div className="icon">⚡</div>
            <h3>Electricidad y Electrónica</h3>
            <p>Centralitas, sensores, alternadores, arranques, cableado, xenon/led.</p>
          </div>

          <div className="service-card">
            <div className="icon">❄️</div>
            <h3>Aire Acondicionado</h3>
            <p>Recarga, reparación fugas, cambio compresor, limpieza circuito.</p>
          </div>

          <div className="service-card">
            <div className="icon">🛡️</div>
            <h3>Revisión Pre-Compra</h3>
            <p>Diagnóstico completo 120+ puntos antes de comprar tu próximo auto.</p>
          </div>
        </div>
      </section>

      {/* ESTADÍSTICAS */}
      <section className="stats">
        <div className="stats-grid">
          <div className="stat-item">
            <span className="number" data-target="18">0</span>
            <p>Años de experiencia</p>
          </div>
          <div className="stat-item">
            <span className="number" data-target="3740">0</span>
            <p>Vehículos atendidos</p>
          </div>
          <div className="stat-item">
            <span className="number" data-target="96">0</span>
            <p>% satisfacción</p>
          </div>
          <div className="stat-item">
            <span className="number" data-target="240">0</span>
            <p>Proyectos tuning</p>
          </div>
        </div>
      </section>

      {/* GALERÍA */}
      <section id="galeria" className="section galeria">
        <div className="section-title">
          <h2>Trabajos Realizados</h2>
          <div className="title-underline"></div>
        </div>
        <div className="gallery-grid">
          <div className="gallery-item item-1"></div>
          <div className="gallery-item item-2"></div>
          <div className="gallery-item item-3"></div>
          <div className="gallery-item item-4"></div>
          <div className="gallery-item item-5"></div>
          <div className="gallery-item item-6"></div>
        </div>
      </section>

      {/* CONTACTO */}
      <section id="contacto" className="section contacto">
        <div className="section-title light">
          <h2>¿Listo para potenciar tu auto?</h2>
          <div className="title-underline"></div>
        </div>

        <div className="contact-container">
          <form className="contact-form" onSubmit={handleSubmit}>
            <input type="text" placeholder="Nombre completo" required />
            <input type="tel" placeholder="Teléfono / WhatsApp" required />
            <input type="email" placeholder="Email" required />
            <select required>
              <option value="" disabled selected>Servicio de interés</option>
              <option>Mecánica general</option>
              <option>Service completo</option>
              <option>Reprogramación / Tuning</option>
              <option>Diagnóstico</option>
              <option>Revisión pre-compra</option>
              <option>Otro</option>
            </select>
            <textarea placeholder="Cuéntanos qué necesita tu vehículo..." rows="5" required></textarea>
            <button type="submit" className="btn primary large">
              Solicitar Turno Ahora
            </button>
          </form>

          <div className="contact-info">
            <h3>Disol Motors Injection</h3>
            <p><strong>Dirección:</strong> Av. Siempre Viva 7423, Galpón 12</p>
            <p><strong>WhatsApp:</strong> +54 9 11 5555-4321</p>
            <p><strong>Horario:</strong> Lunes a Viernes 9:00 - 19:00 | Sábados 9:00 - 14:00</p>
            <p><strong>Email:</strong> info@disolmotors.com</p>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <div className="footer-content">
          <p>© 2025–2026 Disol Motors Injection • Todos los derechos reservados</p>
          <div className="social-links">
            <a href="#">Instagram</a> • <a href="#">Facebook</a> • <a href="#">WhatsApp</a>
          </div>
        </div>
      </footer>
    </>
  );
}

export default App;