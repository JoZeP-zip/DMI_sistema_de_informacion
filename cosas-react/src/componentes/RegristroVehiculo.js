import React, { useState } from 'react';
import './RegistroVehiculo.css';


const RegistroVehiculo = () => {
  // Estados para controlar qué formulario se ve
  const [tab, setTab] = useState('login'); // login, registro, listado
  const [usuario, setUsuario] = useState(null); // Simula el {% if usuario %}

  // Datos de ejemplo para la tabla (Simula el {% for row in data %})
  const [vehiculos, setVehiculos] = useState([
    { id: 1, codigo: 'V001', desc: 'Turbo Intercooler', motor: '2.0L', asientos: '5', placa: 'ABC-123', capacidad: '500kg', modelo: '2024', marca: 'Subaru', tipo: 'Deportivo' }
  ]);

  // Tipos de vehículos (Simula el {% for tipo in tipos %})
  const tipos = [
    { id: 1, nombre: 'Deportivo' },
    { id: 2, nombre: 'Camioneta' },
    { id: 3, nombre: 'Utilitario' }
  ];

  const handleLogin = (e) => {
    e.preventDefault();
    setUsuario("Admin Disol"); // Ejemplo de inicio de sesión exitoso
    setTab('listado');
  };

  return (
    <div className="gestion-container" style={{ color: 'white', padding: '20px' }}>
      
      {/* MENSAJE DE BIENVENIDA */}
      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        {usuario ? (
          <h2 style={{ color: '#d4af37' }}>Bienvenido, {usuario}</h2>
        ) : (
          <h2 style={{ color: '#ff4d4d' }}>No has iniciado sesión</h2>
        )}
      </div>

      {/* BOTONES DE NAVEGACIÓN INTERNA */}
      <div className="cta-buttons" style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginBottom: '30px' }}>
        <button className="btn outline" onClick={() => setTab('login')}>Login</button>
        <button className="btn outline" onClick={() => setTab('registro')}>Nuevo Usuario</button>
        <button className="btn outline" onClick={() => setTab('vehiculo')}>Nuevo Vehículo</button>
        <button className="btn primary" onClick={() => setTab('listado')}>Ver Listado</button>
      </div>

      {/* FORMULARIO INICIAR SESIÓN */}
      {tab === 'login' && (
        <div className="contact-form">
          <h3>Iniciar Sesión</h3>
          <form onSubmit={handleLogin}>
            <input type="email" placeholder="Email" required />
            <input type="password" placeholder="Password" required />
            <button type="submit" className="btn primary">Entrar</button>
          </form>
        </div>
      )}

      {/* FORMULARIO REGISTRO USUARIO */}
      {tab === 'registro' && (
        <div className="contact-form">
          <h3>Registrar Usuario</h3>
          <form onSubmit={(e) => e.preventDefault()}>
            <input type="email" placeholder="Email" required />
            <input type="password" placeholder="Password" required />
            <input type="text" placeholder="Nombre" required />
            <input type="text" placeholder="Apellidos" required />
            <input type="number" placeholder="Documento" required />
            <input type="text" placeholder="Teléfono" required />
            <input type="text" placeholder="Nombre de Usuario" required />
            <button type="submit" className="btn primary">Registrarse</button>
          </form>
        </div>
      )}

      {/* FORMULARIO REGISTRO VEHÍCULO */}
      {tab === 'vehiculo' && (
        <div className="contact-form">
          <h3>Registro de Vehículo</h3>
          <form onSubmit={(e) => e.preventDefault()}>
            <input type="text" placeholder="Código vehículo" required />
            <input type="text" placeholder="Placa (Máx 10)" maxLength="10" required />
            <input type="text" placeholder="Marca" required />
            
            <select style={{ backgroundColor: '#1a1a1a', color: 'white', padding: '10px', marginBottom: '15px', border: '1px solid #333' }}>
              <option value="">Seleccione un tipo</option>
              {tipos.map(tipo => (
                <option key={tipo.id} value={tipo.id}>{tipo.nombre}</option>
              ))}
            </select>

            <input type="text" placeholder="Descripción" />
            <input type="text" placeholder="Motor" />
            <input type="text" placeholder="Cantidad asientos" />
            <input type="text" placeholder="Capacidad" />
            <input type="text" placeholder="Modelo" />
            <button type="submit" className="btn primary">Guardar Vehículo</button>
          </form>
        </div>
      )}

      {/* LISTADO DE VEHÍCULOS (TABLA) */}
      {tab === 'listado' && (
        <div style={{ overflowX: 'auto' }}>
          <h3 style={{ textAlign: 'center', marginBottom: '20px' }}>Listado de Vehículos</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #d4af37' }}>
            <thead style={{ backgroundColor: '#d4af37', color: 'black' }}>
              <tr>
                <th>Código</th><th>Placa</th><th>Marca</th><th>Modelo</th><th>Motor</th>
              </tr>
            </thead>
            <tbody>
              {vehiculos.map((v, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #333', textAlign: 'center' }}>
                  <td style={{ padding: '10px' }}>{v.codigo}</td>
                  <td>{v.placa}</td>
                  <td>{v.marca}</td>
                  <td>{v.modelo}</td>
                  <td>{v.motor}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};


export default RegistroVehiculo;