import React from 'react';
import './Catalogo.css';

const Catalogo = () => {
  // Datos de ejemplo para el catálogo
  const productos = [
    {
      id: 1,
      nombre: "Scanner Profesional",
      categoria: "Diagnóstico",
      precio: "$150.000",
      imagen: "https://via.placeholder.com/200x150",
      descripcion: "Lectura de códigos de error y flujo de datos en tiempo real."
    },
    {
      id: 2,
      nombre: "Limpieza de Inyectores",
      categoria: "Mantenimiento",
      precio: "$45.000",
      imagen: "https://via.placeholder.com/200x150",
      descripcion: "Servicio por ultrasonido para optimizar el consumo de combustible."
    },
    {
      id: 3,
      nombre: "Reprogramación ECU",
      categoria: "Potencia",
      precio: "$250.000",
      imagen: "https://via.placeholder.com/200x150",
      descripcion: "Aumento de HP y torque mediante software especializado."
    },
    {
      id: 4,
      nombre: "Kit Filtros de Alto Flujo",
      categoria: "Performance",
      precio: "$85.000",
      imagen: "https://via.placeholder.com/200x150",
      descripcion: "Mejora la entrada de aire para una mejor respuesta del motor."
    }
  ];

  return (
    <div className="catalogo-container">
      <header className="catalogo-header">
        <h2>Catálogo de Servicios y Productos</h2>
        <p>Todo lo que tu vehículo necesita para rendir al máximo</p>
      </header>

      <div className="productos-grid">
        {productos.map((prod) => (
          <div key={prod.id} className="producto-card">
            <div className="producto-imagen">
              <img src={prod.imagen} alt={prod.nombre} />
              <span className="categoria-tag">{prod.categoria}</span>
            </div>
            <div className="producto-info">
              <h3>{prod.nombre}</h3>
              <p>{prod.descripcion}</p>
              <div className="producto-footer">
                <span className="precio">{prod.precio}</span>
                <button className="btn-comprar">Consultar</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Catalogo;