import { useState } from "react";
import '../styles/Catalogo.css';

function App() {

  const [search, setSearch] = useState("");
  const [cart, setCart] = useState([]);


  const addToCart = (product) => {
  setCart([...cart, product]);
};

  const products = [
    {
      id: 1,
      name: "Batería Vehículo",
      price: "$250.000",
      image: "https://picsum.photos/400/300?1"
    },
    {
      id: 2,
      name: "Pastillas de Freno",
      price: "$120.000",
      image: "https://picsum.photos/400/300?2"
    },
    {
      id: 3,
      name: "Radiador Completo",
      price: "$320.000",
      image: "https://picsum.photos/400/300?3"
    },
    {
      id: 4,
      name: "Kit de Frenos",
      price: "$450.000",
      image: "https://picsum.photos/400/300?4"
    },
    {
      id: 5,
      name: "Aceite Motor 5W-30",
      price: "$85.000",
      image: "https://picsum.photos/400/300?5"
    },
    {
      id: 6,
      name: "Filtro de Aire",
      price: "$65.000",
      image: "https://picsum.photos/400/300?6"
    }
  ];

  return (

    <div>

      {/* HEADER */}

      <header className="top-bar">

        <h1 className="logo">
          <span className="dim">DMI</span>
          {" "} - DISOL INJECTION MOTORS
        </h1>

        <button className="cart-btn">
          🛒 {cart.length}
        </button>

      </header>

      {/* DESTACADOS */}

      <section className="featured-section">

        <h2 className="section-title">
          Repuestos Destacados
        </h2>

        <div className="highlight-capsule">

          <div className="carousels-grid">

            <div className="carousel-card">
              <h3>Kit de Frenos</h3>

              <div className="carousel-wrapper">
                <img
                  src="https://picsum.photos/600/400?10"
                  alt=""
                />
              </div>

            </div>

            <div className="carousel-card">
              <h3>Aceites y Lubricantes</h3>

              <div className="carousel-wrapper">
                <img
                  src="https://picsum.photos/600/400?11"
                  alt=""
                />
              </div>

            </div>

            <div className="carousel-card">
              <h3>Filtros y Refrigeración</h3>

              <div className="carousel-wrapper">
                <img
                  src="https://picsum.photos/600/400?12"
                  alt=""
                />
              </div>

            </div>

          </div>

        </div>

      </section>

      {/* PRODUCTOS */}

      <section className="products">

        <h2 className="section-title">
          Catálogo de Productos
        </h2>

        {/* BUSCADOR */}

        <div className="search-container">

          <input
            type="text"
            placeholder="Buscar repuestos..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />

        </div>

        {/* GRID */}

        <div className="grid">

          {
            products

            .filter(product =>
              product.name
              .toLowerCase()
              .includes(search.toLowerCase())
            )

            .map(product => (

              <div
                className="product-card"
                key={product.id}
              >

                <img
                  src={product.image}
                  alt={product.name}
                />

                <div className="info">

                  <h3>{product.name}</h3>

                  <p className="price">
                    {product.price}
                  </p>
                      <button onClick={() => addToCart(product)}>
                        Agregar
                      </button>

                </div>

              </div>

            ))
          }

        </div>

      </section>

    </div>
  );
}

export default App;