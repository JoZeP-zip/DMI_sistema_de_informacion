import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import "../styles/Catalogo.css";
import Checkout from "./Checkout";


// =====================================================
// INVENTARIO DMI - 559 PRODUCTOS
// =====================================================


const cleanCatalogText = (value) =>
  typeof value === "string"
    ? value
        .replaceAll("\u00e1", "a")
        .replaceAll("\u00e9", "e")
        .replaceAll("\u00ed", "i")
        .replaceAll("\u00f3", "o")
        .replaceAll("\u00fa", "u")
        .replaceAll("\u00f1", "n")
    : value;

const DEFAULT_PRODUCT_IMAGE = "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop";

const getApiBaseUrl = () => {
  if (process.env.REACT_APP_API_URL) return process.env.REACT_APP_API_URL;

  const { protocol, hostname } = window.location;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  if (hostname.includes("app.github.dev")) {
    return `${protocol}//${hostname.replace(/-3000\.app\.github\.dev$/, "-8000.app.github.dev")}`;
  }

  return "";
};

const mapCatalogProduct = (product) => cleanProductText({
  id: product.id ?? product.id_original ?? product.idproductos ?? product.codigo,
  codigo: product.codigo ?? product.codigoproductos ?? "",
  nombre: product.nombre ?? product.descripcionproductos ?? "Producto sin nombre",
  precioCosto: Number(product.precioCosto ?? product.precio_costo ?? product.costo ?? 0),
  precioVenta: Number(product.precioVenta ?? product.precio_venta ?? product.precio ?? product.valor ?? 0),
  inventario: Number(product.inventario ?? product.cantidad ?? product.stock ?? 0),
  categoria: product.categoria ?? "General",
  departamento: product.departamento ?? "",
  image: String(product.image ?? product.imagen_url ?? product.imagen ?? "").trim() || DEFAULT_PRODUCT_IMAGE,
});

const emptyProductForm = () => ({
  codigo: "",
  nombre: "",
  precioCosto: "",
  precioVenta: "",
  inventario: "",
  categoria: "",
  departamento: "",
  image: ""
});

const cleanProductText = (product) => ({
  ...product,
  nombre: cleanCatalogText(product.nombre),
  categoria: cleanCatalogText(product.categoria),
  departamento: cleanCatalogText(product.departamento),
});

function Catalogo({ onNeedLogin } = {}) {



  const PRODUCTS_PER_PAGE = 25;
  const sessionDateKey = (localStorage.getItem("dmiSessionStartedAt") || new Date().toISOString()).slice(0, 10);
  const currentEmail = String(localStorage.getItem("email") || "invitado").toLowerCase();
  const cartStorageKey = `dmiPendingCart_${currentEmail}`;
  const cartSessionsKey = `dmiPendingCartSessions_${currentEmail}`;

  const [search, setSearch] = useState("");
  const [cart, setCart] = useState(() => {
    try {
      const savedCart = localStorage.getItem(cartStorageKey);
      return savedCart ? JSON.parse(savedCart) : [];
    } catch (error) {
      console.error("No se pudo cargar el carrito pendiente:", error);
      return [];
    }
  });
  const [showCart, setShowCart] = useState(false);
  const [showMisCompras, setShowMisCompras] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showLoginRequiredModal, setShowLoginRequiredModal] = useState(false);
  const [catalogMessage, setCatalogMessage] = useState(null);
  const [showCheckout, setShowCheckout] = useState(false);
  const [checkoutItems, setCheckoutItems] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("Todos");
  const [showCategories, setShowCategories] = useState(false);
  const [slide, setSlide] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const productsRef = useRef(null);

  const [products, setProducts] = useState(() => {
    try {
      const savedProducts = localStorage.getItem("catalogoProducts");
      const loadedProducts = savedProducts ? JSON.parse(savedProducts) : INVENTARIO;
      return loadedProducts.map(mapCatalogProduct);
    } catch (error) {
      console.error("No se pudo cargar el catalogo guardado:", error);
      return INVENTARIO.map(mapCatalogProduct);
    }
  });
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [showCreateProduct, setShowCreateProduct] = useState(false);
  const [createForm, setCreateForm] = useState(emptyProductForm());
  const [createError, setCreateError] = useState("");
  const currentRole = String(localStorage.getItem("role") || "").toLowerCase();
  const isAdmin = currentRole === "admin";
  const isLoggedIn = Boolean(localStorage.getItem("token"));

  useEffect(() => {
    let cancelled = false;

    const loadCatalogFromDatabase = async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/catalogo-productos`, {
          credentials: "include",
        });
        const data = await response.json();

        if (!response.ok || !Array.isArray(data)) return;

        const mappedProducts = data.map(mapCatalogProduct);
        if (!cancelled && mappedProducts.length) {
          setProducts(mappedProducts);
        }
      } catch (error) {
        console.error("No se pudo cargar el catalogo desde Supabase:", error);
      }
    };

    loadCatalogFromDatabase();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem("catalogoProducts", JSON.stringify(products));
  }, [products]);

  useEffect(() => {
    localStorage.setItem(cartStorageKey, JSON.stringify(cart));
    try {
      const savedSessions = JSON.parse(localStorage.getItem(cartSessionsKey) || "{}");
      if (cart.length) {
        savedSessions[sessionDateKey] = {
          fecha: sessionDateKey,
          items: cart,
          updatedAt: new Date().toISOString()
        };
      } else {
        delete savedSessions[sessionDateKey];
      }
      localStorage.setItem(cartSessionsKey, JSON.stringify(savedSessions));
    } catch (error) {
      console.error("No se pudo guardar el carrito por fecha:", error);
    }
  }, [cart, cartStorageKey, cartSessionsKey, sessionDateKey]);

  const carouselImages = [
    "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=1400&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1400&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?q=80&w=1400&auto=format&fit=crop"
  ];

  const nextSlide = () =>
    setSlide(slide === carouselImages.length - 1 ? 0 : slide + 1);

  const prevSlide = () =>
    setSlide(slide === 0 ? carouselImages.length - 1 : slide - 1);

  const categories = [
    "Todos",
    ...new Set(products.map(p => p.categoria))
  ].sort((a, b) => a === "Todos" ? -1 : b === "Todos" ? 1 : a.localeCompare(b));

  const goToProducts = () => {
    setTimeout(() => {
      productsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  };

  const normalizeSearchText = (value) =>
    String(value ?? "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]/g, "");

  // CARRITO
  const addToCart = (product) => {
    const existing = cart.find(item => item.id === product.id);
    if (existing) {
      setCart(cart.map(item =>
        item.id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, { ...product, quantity: 1 }]);
    }
  };

  const removeFromCart = (id) =>
    setCart(cart.filter(item => item.id !== id));

  const updateQuantity = (id, delta) => {
    setCart(cart.map(item =>
      item.id === id
        ? { ...item, quantity: Math.max(1, item.quantity + delta) }
        : item
    ));
  };

  const goToPayment = (product) => {
    if (!isLoggedIn) {
      addToCart(product);
      setSelectedProduct(null);
      setShowCart(false);
      setShowMisCompras(false);
      setShowConfirmModal(false);
      setShowLoginRequiredModal(true);
      return;
    }

    setSelectedProduct(null);
    setShowCart(false);
    setShowMisCompras(false);
    setCheckoutItems([{ ...product, quantity: 1 }]);
    setShowCheckout(true);
  };

  const goToPaymentCart = () => {
    if (!isLoggedIn) {
      setShowConfirmModal(false);
      setShowMisCompras(false);
      setShowCart(false);
      setShowLoginRequiredModal(true);
      return;
    }

    setShowConfirmModal(false);
    setShowMisCompras(false);
    setShowCart(false);
    setCheckoutItems(cart);
    setShowCheckout(true);
  };

  const confirmarIrAlLogin = () => {
    setShowLoginRequiredModal(false);
    if (onNeedLogin) onNeedLogin();
  };

  const totalProducts = cart.reduce((acc, item) => acc + item.quantity, 0);
  const totalPrice = cart.reduce((acc, item) => acc + item.precioVenta * item.quantity, 0);
  const checkoutTotal = checkoutItems.reduce((acc, item) => acc + item.precioVenta * item.quantity, 0);

  // EDICION
  const openEdit = (product) => {
    if (!isAdmin) return;
    setEditingId(product.id);
    setEditForm({ ...product });
  };

  const saveEdit = async () => {
    if (!isAdmin) return;

    const updatedProduct = cleanProductText({
      ...editForm,
      image: String(editForm.image || "").trim(),
      precioVenta: Number(editForm.precioVenta),
      precioCosto: Number(editForm.precioCosto),
      inventario: Number(editForm.inventario)
    });

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/catalogo-productos/${editingId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify(updatedProduct)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.detail || "No se pudo guardar el producto");
      }

      const savedProduct = mapCatalogProduct(data);

      setProducts(products.map(product =>
        product.id === editingId ? savedProduct : product
      ));
      setCart(cart.map(item =>
        item.id === editingId ? { ...savedProduct, quantity: item.quantity } : item
      ));
      setSelectedProduct(prev =>
        prev?.id === editingId ? savedProduct : prev
      );
      setEditingId(null);
      setCatalogMessage({
        type: "success",
        eyebrow: "Producto actualizado",
        title: "Producto guardado y actualizado correctamente",
        text: "La informacion del producto y la imagen quedaron guardadas en Supabase."
      });
    } catch (error) {
      setCatalogMessage({
        type: "error",
        eyebrow: "No se pudo guardar",
        title: "No se pudo actualizar el producto",
        text: error.message || "Revisa la informacion e intenta de nuevo."
      });
    }
  };

  const openCreateProduct = () => {
    if (!isAdmin) return;
    setCreateForm(emptyProductForm());
    setCreateError("");
    setShowCreateProduct(true);
  };

  const saveNewProduct = () => {
    if (!isAdmin) return;

    const nombre = String(createForm.nombre || "").trim();
    const codigo = String(createForm.codigo || "").trim();
    const categoria = String(createForm.categoria || "").trim();

    if (!nombre || !codigo || !categoria) {
      setCreateError("Completa nombre, codigo y categoria del producto.");
      return;
    }

    if (products.some((product) => String(product.codigo).toLowerCase() === codigo.toLowerCase())) {
      setCreateError("Ya existe un producto con ese codigo.");
      return;
    }

    const newProduct = cleanProductText({
      id: Math.max(0, ...products.map((product) => Number(product.id) || 0)) + 1,
      codigo,
      nombre,
      precioCosto: Number(createForm.precioCosto || 0),
      precioVenta: Number(createForm.precioVenta || 0),
      inventario: Number(createForm.inventario || 0),
      categoria,
      departamento: String(createForm.departamento || "General").trim() || "General",
      image: String(createForm.image || "").trim() || DEFAULT_PRODUCT_IMAGE
    });

    setProducts([newProduct, ...products]);
    setSelectedCategory(newProduct.categoria);
    setSearch("");
    setCurrentPage(1);
    setShowCreateProduct(false);
    setCreateForm(emptyProductForm());
    setCreateError("");
    setTimeout(() => productsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
  };



   

  // FILTRADO
  const normalizedSearch = normalizeSearchText(search);

  const filteredProducts = products
    .filter(p => selectedCategory === "Todos" ? true : p.categoria === selectedCategory)
    .filter(p => {
      if (!normalizedSearch) return true;
      const normalizedName = normalizeSearchText(p.nombre);
      const normalizedCode = normalizeSearchText(p.codigo);
      const normalizedCategory = normalizeSearchText(p.categoria);
      const normalizedDepartment = normalizeSearchText(p.departamento);
      return (
        normalizedName.includes(normalizedSearch) ||
        normalizedCode.includes(normalizedSearch) ||
        normalizedCategory.includes(normalizedSearch) ||
        normalizedDepartment.includes(normalizedSearch)
      );
    });

  const totalPages = Math.ceil(filteredProducts.length / PRODUCTS_PER_PAGE);
  const startIndex = (currentPage - 1) * PRODUCTS_PER_PAGE;
  const paginatedProducts = filteredProducts.slice(startIndex, startIndex + PRODUCTS_PER_PAGE);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, selectedCategory]);

  return (
    <div className={`main-container${showCart ? " cart-open" : ""}${showMisCompras ? " compras-open" : ""}`}>

      {/* HEADER FIJO */}
      <header className="top-bar">
        <div className="logo">
          <span className="dim">DMI</span>{" "}
        </div>
        <div className="header-right">
          {/* BOTON CATEGORIAS */}
          <div className="categories-container">
            <button
              className="categories-toggle"
              onClick={() => setShowCategories(!showCategories)}
            >
              Categorias
            </button>
            {showCategories && (
              <div className="categories-dropdown">
                {categories.map(category => (
                  <button
                    key={category}
                    className={selectedCategory === category ? "category-btn active" : "category-btn"}
                    onClick={() => {
                      setSelectedCategory(category);
                      setShowCategories(false);
                      goToProducts();
                    }}
                  >
                    {category}
                  </button>
                ))}
              </div>
            )}
          </div>

          {isAdmin && (
            <button
              className="admin-add-product-btn"
              onClick={openCreateProduct}
            >
              + Producto
            </button>
          )}

          <input
            type="text"
            placeholder="Buscar repuestos..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              goToProducts();
            }}
            className="header-search"
          />
          <button
            className="mis-compras-btn"
            onClick={() => {
              setShowMisCompras(!showMisCompras);
              setShowCart(false);
            }}
          >
            Tus Compras {totalProducts > 0 && `(${totalProducts})`}
          </button>
          <button
            className="cart-btn"
            aria-label="Carrito"
            onClick={() => {
              setShowCart(!showCart);
              setShowMisCompras(false);
            }}
          >
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M3 3h2l2.4 12.4a2 2 0 0 0 2 1.6h8.2a2 2 0 0 0 2-1.6L21 8H6"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="9.5" cy="20.5" r="1.5" />
              <circle cx="17.5" cy="20.5" r="1.5" />
            </svg>
            <span className="cart-count">{totalProducts}</span>
          </button>
        </div>
      </header>


      {/* CARRITO */}
      {showCart &&
        createPortal(
        <div className="cart-panel">
          <div className="cart-panel-header">
            <h2>Carrito</h2>
            <button
              className="cart-close-btn"
              aria-label="Cerrar carrito"
              onClick={() => setShowCart(false)}
            >
              ×
            </button>
          </div>
          {cart.length === 0 ? (
            <p>El carrito esta vacio</p>
          ) : (
            <>
              {cart.map(item => (
                <div className="cart-item" key={item.id}>
                  <img src={item.image || DEFAULT_PRODUCT_IMAGE} alt={item.nombre} />
                  <div className="cart-info">
                    <h4>{item.nombre}</h4>
                    <p>${item.precioVenta.toLocaleString()}</p>
                    <span>Cantidad: {item.quantity}</span>
                  </div>
                  <button className="remove-btn" onClick={() => removeFromCart(item.id)}>X</button>
                </div>
              ))}
              <div className="cart-total">
                <h3>Total:</h3>
                <p>${totalPrice.toLocaleString()}</p>
              </div>
              <button
                className="checkout-btn"
                onClick={() => {
                  setShowCart(false);
                  setShowMisCompras(true);
                }}
              >
                Ver Tus Compras - ${totalPrice.toLocaleString()}
              </button>
              <button
                className="keep-shopping-btn"
                onClick={() => setShowCart(false)}
              >
                Seguir comprando
              </button>
            </>
          )}
        </div>,
        document.body
      )}

      {/* PANEL TUS COMPRAS */}
      {showMisCompras &&
        createPortal(
        <div className="mis-compras-panel">
          <div className="mis-compras-header">
            <h2>
              Tus Compras
              <span className="mis-compras-sub">
                {cart.length} {cart.length === 1 ? "producto" : "productos"}
              </span>
            </h2>
            <button
              className="mis-compras-close"
              onClick={() => setShowMisCompras(false)}
            >
              X
            </button>
          </div>

          {cart.length === 0 ? (
            <p className="mis-compras-empty">No tienes productos agregados</p>
          ) : (
            <>
              <div className="mis-compras-list">
                {cart.map(item => (
                  <div className="mc-item" key={item.id}>
                    <img src={item.image || DEFAULT_PRODUCT_IMAGE} alt={item.nombre} />
                    <div className="mc-info">
                      <h4>{item.nombre}</h4>
                      <p className="mc-code">Cod: {item.codigo}</p>
                      <div className="mc-qty">
                        <button onClick={() => updateQuantity(item.id, -1)}>-</button>
                        <span>{item.quantity}</span>
                        <button onClick={() => updateQuantity(item.id, +1)}>+</button>
                      </div>
                    </div>
                    <div className="mc-price">
                      <span className="mc-unit">c/u ${item.precioVenta.toLocaleString()}</span>
                      <span className="mc-total">
                        ${(item.precioVenta * item.quantity).toLocaleString()}
                      </span>
                    </div>
                    <button
                      className="mc-remove"
                      onClick={() => removeFromCart(item.id)}
                    >
                      X
                    </button>
                  </div>
                ))}
              </div>

              <div className="mc-summary">
                <div className="mc-summary-row">
                  <span>Unidades</span>
                  <span>{totalProducts}</span>
                </div>
                <div className="mc-summary-row">
                  <span>Referencias</span>
                  <span>{cart.length}</span>
                </div>
              </div>

              <div className="mc-total-block">
                <h3>Total:</h3>
                <p>${totalPrice.toLocaleString()}</p>
              </div>

              <button
                className="mc-pay-btn"
                onClick={() => setShowConfirmModal(true)}
              >
                Realizar pago
              </button>

              <button
                className="mc-keep-btn"
                onClick={() => setShowMisCompras(false)}
              >
                Seguir comprando
              </button>
            </>
          )}
        </div>,
        document.body
      )}

      {catalogMessage &&
        createPortal(
          <div className="mc-modal-overlay">
            <div className="mc-modal">
              <p className="mc-modal-sub" style={{ textTransform: "uppercase", letterSpacing: "2px", color: catalogMessage.type === "success" ? "#7fffd4" : "#ff4057" }}>
                {catalogMessage.eyebrow}
              </p>
              <h2>{catalogMessage.title}</h2>
              <p className="mc-modal-sub">{catalogMessage.text}</p>
              <div className="mc-modal-btns">
                <button
                  type="button"
                  className="mc-modal-confirm"
                  onClick={() => setCatalogMessage(null)}
                >
                  Aceptar
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
      {/* MODAL CONFIRMACION - fuera del panel, al mismo nivel */}
      {showConfirmModal &&
        createPortal(
          <div className="mc-modal-overlay">
            <div className="mc-modal">
              <h2>Confirmar pedido</h2>
              <p className="mc-modal-sub">Revisa tu pedido antes de continuar</p>

              <div className="mc-modal-list">
                {cart.map(item => (
                  <div className="mc-modal-row" key={item.id}>
                    <span>{item.nombre} x {item.quantity}</span>
                    <span>${(item.precioVenta * item.quantity).toLocaleString()}</span>
                  </div>
                ))}
              </div>

              <div className="mc-modal-total">
                <span>Total a pagar</span>
                <span className="mc-modal-total-price">
                  ${totalPrice.toLocaleString()}
                </span>
              </div>

              <div className="mc-modal-btns">
                <button
                  className="mc-modal-confirm"
                  onClick={goToPaymentCart}
                >
                  Confirmar y pagar
                </button>
                <button
                  className="mc-modal-cancel"
                  onClick={() => setShowConfirmModal(false)}
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* MODAL ACCESO REQUERIDO - se muestra antes de mandar al login */}
      {showLoginRequiredModal &&
        createPortal(
          <div
            className="mc-modal-overlay"
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.75)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 9999,
            }}
          >
            <div
              style={{
                width: "min(480px, 92vw)",
                background: "#0a0a0c",
                border: "1px solid rgba(255,64,87,0.55)",
                boxShadow: "0 0 40px rgba(255,64,87,0.12)",
                borderRadius: 4,
                padding: "28px 30px",
                color: "#fff",
                fontFamily: "inherit",
              }}
            >
              <p
                style={{
                  color: "#ff4057",
                  letterSpacing: "2px",
                  fontSize: 12,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  margin: "0 0 10px",
                }}
              >
                Acceso requerido
              </p>
              <h2 style={{ margin: "0 0 14px", fontSize: 26 }}>
                Inicia sesion para comprar
              </h2>
              <p style={{ color: "#c9c9cf", margin: "0 0 24px", lineHeight: 1.5 }}>
                Para proteger tus datos y registrar tu pedido correctamente,
                primero debes iniciar sesion.
              </p>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={confirmarIrAlLogin}
                  style={{
                    flex: "1 1 160px",
                    background: "#e23345",
                    color: "#fff",
                    border: "none",
                    borderRadius: 4,
                    padding: "14px 18px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Ir al login
                </button>
                <button
                  type="button"
                  onClick={() => setShowLoginRequiredModal(false)}
                  style={{
                    flex: "1 1 160px",
                    background: "transparent",
                    color: "#fff",
                    border: "1px solid rgba(255,255,255,0.4)",
                    borderRadius: 4,
                    padding: "14px 18px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* MODAL NUEVO PRODUCTO */}
      {isAdmin && showCreateProduct &&
        createPortal(
          <div className="edit-product-overlay">
            <div className="edit-product-modal create-product-modal">
              <h2>NUEVO PRODUCTO</h2>
              {createError && <p className="create-product-error">{createError}</p>}
              {[
                { label: "Nombre", key: "nombre", type: "text" },
                { label: "Codigo", key: "codigo", type: "text" },
                { label: "Precio Venta", key: "precioVenta", type: "number" },
                { label: "Precio Costo", key: "precioCosto", type: "number" },
                { label: "Inventario", key: "inventario", type: "number" },
                { label: "Categoria", key: "categoria", type: "text" },
                { label: "Departamento", key: "departamento", type: "text" },
                { label: "URL Imagen", key: "image", type: "text" },
              ].map(({ label, key, type }) => (
                <div key={key} className="edit-product-field">
                  <label>{label.toUpperCase()}</label>
                  <input
                    type={type}
                    value={createForm[key] ?? ""}
                    onChange={e => setCreateForm({ ...createForm, [key]: e.target.value })}
                  />
                  {key === "image" && createForm.image && (
                    <img
                      className="edit-product-preview"
                      src={createForm.image || DEFAULT_PRODUCT_IMAGE}
                      alt="Vista previa"
                    />
                  )}
                </div>
              ))}
              <div className="edit-product-actions">
                <button className="edit-product-save" onClick={saveNewProduct}>GUARDAR PRODUCTO</button>
                <button className="edit-product-cancel" onClick={() => setShowCreateProduct(false)}>CANCELAR</button>
              </div>
            </div>
          </div>,
          document.body
        )}
      {/* MODAL EDICION */}
      {isAdmin && editingId &&
        createPortal(
          <div className="edit-product-overlay">
            <div className="edit-product-modal">
              <h2>
                EDITAR PRODUCTO
              </h2>
              {[
                { label: "Nombre",       key: "nombre" },
                { label: "Codigo",       key: "codigo" },
                { label: "Precio Venta", key: "precioVenta" },
                { label: "Precio Costo", key: "precioCosto" },
                { label: "Inventario",   key: "inventario" },
                { label: "Categoria",    key: "categoria" },
                { label: "Departamento", key: "departamento" },
                { label: "URL Imagen",   key: "image" },
              ].map(({ label, key }) => (
                <div key={key} className="edit-product-field">
                  <label>
                    {label.toUpperCase()}
                  </label>
                  <input
                    value={editForm[key] ?? ""}
                    onChange={e => setEditForm({ ...editForm, [key]: e.target.value })}
                  />
                  {key === "image" && editForm.image && (
                    <img
                      className="edit-product-preview"
                      src={editForm.image || DEFAULT_PRODUCT_IMAGE}
                      alt="Vista previa"
                    />
                  )}
                </div>
              ))}
              <div className="edit-product-actions">
                <button
                  className="edit-product-save"
                  onClick={saveEdit}
                >
                  GUARDAR
                </button>
                <button
                  className="edit-product-cancel"
                  onClick={() => setEditingId(null)}
                >
                  CANCELAR
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* CARRUSEL */}
      <section className="hero-section">
        <h2 className="section-title">Repuestos Destacados</h2>
        <div className="hero-carousel">
          <button className="hero-btn left" onClick={prevSlide}>{"<"}</button>
          <img src={carouselImages[slide]} alt="" className="hero-image" />
          <button className="hero-btn right" onClick={nextSlide}>{">"}</button>
        </div>
      </section>

      {/* PRODUCTOS */}
      <section className="products" ref={productsRef}>
        <h2 className="section-title">
          {selectedCategory === "Todos" ? "Catalogo de Productos" : selectedCategory}
        </h2>
        <p style={{
          textAlign: "center",
          color: "rgba(255,80,80,0.7)",
          fontSize: 13,
          marginBottom: 30,
          letterSpacing: 1
        }}>
          {filteredProducts.length} producto{filteredProducts.length !== 1 ? "s" : ""}
          {selectedCategory !== "Todos" ? ` en ${selectedCategory}` : " en total"}
        </p>

        <div className="grid">
          {paginatedProducts.map(product => (
            <div
              className="product-card"
              key={product.id}
              onClick={() => setSelectedProduct(product)}
              role="button"
              tabIndex="0"
              onKeyDown={(e) => { if (e.key === "Enter") setSelectedProduct(product); }}
            >
              <img src={product.image || DEFAULT_PRODUCT_IMAGE} alt={product.nombre} />
              <div className="info">
                <h3>{product.nombre}</h3>
                <p>Codigo: {product.codigo}</p>
                <p>Inventario: {product.inventario}</p>
                {product.departamento && product.departamento !== "-" && (
                  <p style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginTop: 4 }}>
                    {product.departamento}
                  </p>
                )}
                <p className="price">${product.precioVenta.toLocaleString()}</p>
                <div className="product-card-actions">
                  <button
                    className="cart-add-btn"
                    onClick={(e) => { e.stopPropagation(); addToCart(product); }}
                  >
                    Agregar
                  </button>
                  <button
                    className="buy-btn"
                    onClick={(e) => { e.stopPropagation(); goToPayment(product); }}
                  >
                    Comprar
                  </button>
                  {isAdmin && (
                    <button
                      className="edit-product-btn"
                      onClick={(e) => { e.stopPropagation(); openEdit(product); }}
                      title="Editar producto"
                    >
                      Editar
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredProducts.length > PRODUCTS_PER_PAGE && (
          <div className="pagination">
            <button
              className="pagination-btn"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(currentPage - 1)}
            >
              Anterior
            </button>
            <span className="pagination-info">
              Pagina {currentPage} de {totalPages}
            </span>
            <button
              className="pagination-btn"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(currentPage + 1)}
            >
              Siguiente
            </button>
          </div>
        )}
      </section>

      {/* MODAL DETALLE PRODUCTO */}
      {selectedProduct &&
        createPortal(
          <div
            className="product-detail-overlay"
            onClick={() => setSelectedProduct(null)}
          >
            <div
              className="product-detail-modal"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="product-detail-close"
                onClick={() => setSelectedProduct(null)}
              >
                X
              </button>
              <img
                src={selectedProduct.image || DEFAULT_PRODUCT_IMAGE}
                alt={selectedProduct.nombre}
                className="product-detail-image"
              />
              <div className="product-detail-info">
                <p className="product-detail-category">{selectedProduct.categoria}</p>
                <h2>{selectedProduct.nombre}</h2>
                <div className="product-detail-data">
                  <p><span>Codigo:</span> {selectedProduct.codigo}</p>
                  <p><span>Inventario:</span> {selectedProduct.inventario}</p>
                  <p><span>Departamento:</span> {selectedProduct.departamento || "Sin departamento"}</p>
                </div>
                <p className="product-detail-price">
                  $ {selectedProduct.precioVenta.toLocaleString()}
                </p>
                <div className="product-detail-actions">
                  <button
                    onClick={() => { addToCart(selectedProduct); setSelectedProduct(null); }}
                  >
                    Agregar
                  </button>
                  <button
                    className="buy-btn"
                    onClick={() => goToPayment(selectedProduct)}
                  >
                    Comprar ahora
                  </button>
                  {isAdmin && (
                    <button
                      onClick={() => { openEdit(selectedProduct); setSelectedProduct(null); }}
                    >
                      Editar
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>,
          document.body
        )}

      {showCheckout &&
        createPortal(
          <Checkout
            total={checkoutTotal}
            items={checkoutItems}
            onPaid={() => {
              const paidIds = new Set(checkoutItems.map((item) => item.id));
              setCart((currentCart) => currentCart.filter((item) => !paidIds.has(item.id)));
            }}
            onClose={() => {
              setShowCheckout(false);
              setCheckoutItems([]);
            }}
          />,
          document.body
        )}

    </div>
  );
}

export default Catalogo;