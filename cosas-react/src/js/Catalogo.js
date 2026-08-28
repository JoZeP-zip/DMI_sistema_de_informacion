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

const DEFAULT_PRODUCT_IMAGE =
  "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop";

const getApiBaseUrl = () => {
  if (process.env.REACT_APP_API_URL) return process.env.REACT_APP_API_URL;

  const { protocol, hostname } = window.location;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  if (hostname.includes("app.github.dev")) {
    return `${protocol}//${hostname.replace(
      /-3000\.app\.github\.dev$/,
      "-8000.app.github.dev"
    )}`;
  }

  return "";
};

const mapCatalogProduct = (product) =>
  cleanProductText({
    id:
      product.id ??
      product.id_original ??
      product.idproductos ??
      product.codigo,

    codigo: product.codigo ?? product.codigoproductos ?? "",

    nombre:
      product.nombre ??
      product.descripcionproductos ??
      "Producto sin nombre",

    precioCosto: Number(
      product.precioCosto ??
      product.precio_costo ??
      product.costo ??
      0
    ),

    precioVenta: Number(
      product.precioVenta ??
      product.precio_venta ??
      product.precio ??
      product.valor ??
      0
    ),

    inventario: Number(
      product.inventario ??
      product.cantidad ??
      product.stock ??
      0
    ),

    categoria: product.categoria ?? "General",

    departamento: product.departamento ?? "",

    image:
      String(
        product.image ??
        product.imagen_url ??
        product.imagen ??
        ""
      ).trim() || DEFAULT_PRODUCT_IMAGE,
  });

const emptyProductForm = () => ({
  codigo: "",
  nombre: "",
  precioCosto: "",
  precioVenta: "",
  inventario: "",
  categoria: "",
  departamento: "",
  image: "",
});

const cleanProductText = (product) => ({
  ...product,
  nombre: cleanCatalogText(product.nombre),
  categoria: cleanCatalogText(product.categoria),
  departamento: cleanCatalogText(product.departamento),
});

function Catalogo({ onNeedLogin } = {}) {
  const PRODUCTS_PER_PAGE = 25;

  const sessionDateKey = (
    localStorage.getItem("dmiSessionStartedAt") ||
    new Date().toISOString()
  ).slice(0, 10);

  const currentEmail = String(
    localStorage.getItem("email") || "invitado"
  ).toLowerCase();

  const cartStorageKey = `dmiPendingCart_${currentEmail}`;
  const cartSessionsKey = `dmiPendingCartSessions_${currentEmail}`;

  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

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
  const [showLoginRequiredModal, setShowLoginRequiredModal] =
    useState(false);

  const [catalogMessage, setCatalogMessage] = useState(null);

  const [showCheckout, setShowCheckout] = useState(false);
  const [checkoutItems, setCheckoutItems] = useState([]);

  const [selectedCategory, setSelectedCategory] =
    useState("Todos");

  const [showCategories, setShowCategories] =
    useState(false);

  const [slide, setSlide] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  const [selectedProduct, setSelectedProduct] =
    useState(null);

  const productsRef = useRef(null);

  const [products, setProducts] = useState(() => {
    try {
      const savedProducts =
        localStorage.getItem("catalogoProducts");

      if (savedProducts) {
        const loadedProducts =
          JSON.parse(savedProducts);

        if (Array.isArray(loadedProducts)) {
          return loadedProducts.map(mapCatalogProduct);
        }
      }

      return [];
    } catch (error) {
      console.error(
        "No se pudo cargar el catalogo guardado:",
        error
      );
      return [];
    }
  });

  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});

  const [showCreateProduct, setShowCreateProduct] =
    useState(false);

  const [createForm, setCreateForm] =
    useState(emptyProductForm());

  const [createError, setCreateError] = useState("");

  const currentRole = String(
    localStorage.getItem("role") || ""
  ).toLowerCase();

  const isAdmin = currentRole === "admin";

  const isLoggedIn = Boolean(
    localStorage.getItem("token")
  );

  // =====================================================
  // CARGAR PRODUCTOS DESDE SUPABASE
  // =====================================================

  useEffect(() => {
    let cancelled = false;

    const loadCatalogFromDatabase = async () => {
      try {
        const response = await fetch(
          `${getApiBaseUrl()}/api/catalogo-productos`,
          {
            credentials: "include",
          }
        );

        const data = await response.json();

        if (!response.ok || !Array.isArray(data)) {
          return;
        }

        const mappedProducts =
          data.map(mapCatalogProduct);

        if (!cancelled && mappedProducts.length) {
          setProducts(mappedProducts);
        }
      } catch (error) {
        console.error(
          "No se pudo cargar el catalogo desde Supabase:",
          error
        );
      }
    };

    loadCatalogFromDatabase();

    return () => {
      cancelled = true;
    };
  }, []);

  // GUARDAR PRODUCTOS LOCALMENTE COMO RESPALDO
  useEffect(() => {
    localStorage.setItem(
      "catalogoProducts",
      JSON.stringify(products)
    );
  }, [products]);

  // GUARDAR CARRITO
  useEffect(() => {
    localStorage.setItem(
      cartStorageKey,
      JSON.stringify(cart)
    );

    try {
      const savedSessions = JSON.parse(
        localStorage.getItem(cartSessionsKey) || "{}"
      );

      if (cart.length) {
        savedSessions[sessionDateKey] = {
          fecha: sessionDateKey,
          items: cart,
          updatedAt: new Date().toISOString(),
        };
      } else {
        delete savedSessions[sessionDateKey];
      }

      localStorage.setItem(
        cartSessionsKey,
        JSON.stringify(savedSessions)
      );
    } catch (error) {
      console.error(
        "No se pudo guardar el carrito por fecha:",
        error
      );
    }
  }, [
    cart,
    cartStorageKey,
    cartSessionsKey,
    sessionDateKey,
  ]);

  const carouselImages = [
    "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=1400&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1400&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?q=80&w=1400&auto=format&fit=crop",
  ];

  const nextSlide = () =>
    setSlide(
      slide === carouselImages.length - 1
        ? 0
        : slide + 1
    );

  const prevSlide = () =>
    setSlide(
      slide === 0
        ? carouselImages.length - 1
        : slide - 1
    );
  const normalizeSearchText = (value) =>
    String(value ?? "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]/g, "");

  // BUSQUEDA (solo al presionar Enter)
  const runSearch = () => {
    setSearch(searchInput);
    goToProducts();
  };

  const handleSearchKeyDown = (e) => {
    if (e.key === "Enter") {
      runSearch();
    }
  };

  // CARRITO
  const addToCart = (product) => {
    const existing = cart.find(item => item.id === product.id);

    if (existing) {
      setCart(cart.map(item =>
        item.id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));

      setCatalogMessage({
        type: "success",
        eyebrow: "Carrito actualizado",
        title: "Producto agregado al carrito",
        text: `${product.nombre} fue agregado nuevamente. La cantidad del producto ahora es ${existing.quantity + 1}.`
      });
    } else {
      setCart([...cart, { ...product, quantity: 1 }]);

      setCatalogMessage({
        type: "success",
        eyebrow: "Producto agregado",
        title: "Producto agregado al carrito",
        text: `${product.nombre} fue agregado correctamente a tu carrito.`
      });
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

  const totalProducts = cart.reduce(
    (acc, item) => acc + item.quantity,
    0
  );

  const totalPrice = cart.reduce(
    (acc, item) => acc + item.precioVenta * item.quantity,
    0
  );

  const checkoutTotal = checkoutItems.reduce(
    (acc, item) => acc + item.precioVenta * item.quantity,
    0
  );
  // =====================================================
  // CATEGORÍAS
  // =====================================================

  const categories = [
    "Todos",
    ...new Set(
      products
        .map((p) => p.categoria)
        .filter(Boolean)
    ),
  ].sort((a, b) =>
    a === "Todos"
      ? -1
      : b === "Todos"
        ? 1
        : a.localeCompare(b)
  );

  const goToProducts = () => {
    setTimeout(() => {
      productsRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 100);
  };

  // =====================================================
  // EDICIÓN DE PRODUCTOS
  // =====================================================

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
      inventario: Number(editForm.inventario),
    });

    try {
      const response = await fetch(
        `${getApiBaseUrl()}/api/catalogo-productos/${editingId}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify(updatedProduct),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            data.detail ||
            "No se pudo guardar el producto"
        );
      }

      const savedProduct = mapCatalogProduct(data);

      setProducts(
        products.map((product) =>
          product.id === editingId
            ? savedProduct
            : product
        )
      );

      setCart(
        cart.map((item) =>
          item.id === editingId
            ? {
                ...savedProduct,
                quantity: item.quantity,
              }
            : item
        )
      );

      setSelectedProduct((prev) =>
        prev?.id === editingId
          ? savedProduct
          : prev
      );

      setEditingId(null);

      setCatalogMessage({
        type: "success",
        eyebrow: "Producto actualizado",
        title: "Producto guardado correctamente",
        text:
          "La información del producto y la imagen quedaron guardadas correctamente.",
      });
    } catch (error) {
      setCatalogMessage({
        type: "error",
        eyebrow: "No se pudo guardar",
        title: "No se pudo actualizar el producto",
        text:
          error.message ||
          "Revisa la información e intenta de nuevo.",
      });
    }
  };

  // =====================================================
  // CREAR NUEVO PRODUCTO
  // =====================================================

  const openCreateProduct = () => {
    if (!isAdmin) return;

    setCreateForm(emptyProductForm());
    setCreateError("");
    setShowCreateProduct(true);
  };

  const saveNewProduct = () => {
    if (!isAdmin) return;

    const nombre = String(
      createForm.nombre || ""
    ).trim();

    const codigo = String(
      createForm.codigo || ""
    ).trim();

    const categoria = String(
      createForm.categoria || ""
    ).trim();

    if (!nombre || !codigo || !categoria) {
      setCreateError(
        "Completa nombre, código y categoría del producto."
      );
      return;
    }

    const codigoExiste = products.some(
      (product) =>
        String(product.codigo).toLowerCase() ===
        codigo.toLowerCase()
    );

    if (codigoExiste) {
      setCreateError(
        "Ya existe un producto con ese código."
      );
      return;
    }

    const newProduct = cleanProductText({
      id:
        Math.max(
          0,
          ...products.map(
            (product) =>
              Number(product.id) || 0
          )
        ) + 1,

      codigo,
      nombre,

      precioCosto: Number(
        createForm.precioCosto || 0
      ),

      precioVenta: Number(
        createForm.precioVenta || 0
      ),

      inventario: Number(
        createForm.inventario || 0
      ),

      categoria,

      departamento:
        String(
          createForm.departamento || "General"
        ).trim() || "General",

      image:
        String(createForm.image || "").trim() ||
        DEFAULT_PRODUCT_IMAGE,
    });

    setProducts([
      newProduct,
      ...products,
    ]);

    setSelectedCategory(newProduct.categoria);
    setSearch("");
    setSearchInput("");
    setCurrentPage(1);

    setShowCreateProduct(false);
    setCreateForm(emptyProductForm());
    setCreateError("");

    setTimeout(() => {
      productsRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 100);
  };

  // =====================================================
  // FILTRADO Y BÚSQUEDA
  // =====================================================

  const normalizedSearch =
    normalizeSearchText(search);

  const filteredProducts = products
    .filter((product) =>
      selectedCategory === "Todos"
        ? true
        : product.categoria === selectedCategory
    )
    .filter((product) => {
      if (!normalizedSearch) return true;

      const normalizedName =
        normalizeSearchText(product.nombre);

      const normalizedCode =
        normalizeSearchText(product.codigo);

      const normalizedCategory =
        normalizeSearchText(product.categoria);

      const normalizedDepartment =
        normalizeSearchText(product.departamento);

      return (
        normalizedName.includes(normalizedSearch) ||
        normalizedCode.includes(normalizedSearch) ||
        normalizedCategory.includes(normalizedSearch) ||
        normalizedDepartment.includes(normalizedSearch)
      );
    });

  const totalPages = Math.max(
    1,
    Math.ceil(
      filteredProducts.length / PRODUCTS_PER_PAGE
    )
  );

  const startIndex =
    (currentPage - 1) * PRODUCTS_PER_PAGE;

  const paginatedProducts =
    filteredProducts.slice(
      startIndex,
      startIndex + PRODUCTS_PER_PAGE
    );

  useEffect(() => {
    setCurrentPage(1);
  }, [search, selectedCategory]);

  return (
    <div
      className={`main-container${
        showCart ? " cart-open" : ""
      }${
        showMisCompras ? " compras-open" : ""
      }`}
    >
      {/* HEADER FIJO */}
      <header className="top-bar">
        <div className="logo">
          <span className="dim">DMI</span>{" "}
        </div>

        <div className="header-right">

          {/* BOTÓN CATEGORÍAS */}
          <div className="categories-container">
            <button
              className="categories-toggle"
              onClick={() => setShowCategories(!showCategories)}
            >
              Categorías
            </button>

            {showCategories && (
              <div className="categories-dropdown">
                {categories.map(category => (
                  <button
                    key={category}
                    className={
                      selectedCategory === category
                        ? "category-btn active"
                        : "category-btn"
                    }
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
            placeholder="Buscar repuestos... (Enter para buscar)"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={handleSearchKeyDown}
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
            <svg
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M3 3h2l2.4 12.4a2 2 0 0 0 2 1.6h8.2a2 2 0 0 0 2-1.6L21 8H6"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="9.5" cy="20.5" r="1.5" />
              <circle cx="17.5" cy="20.5" r="1.5" />
            </svg>

            <span className="cart-count">
              {totalProducts}
            </span>
          </button>
        </div>
      </header>

      {/* CARRITO */}
      {showCart &&
        createPortal(
          <div
            className="dmi-cart-overlay"
            role="dialog"
            style={{
              position: "fixed",
              inset: 0,
              width: "100vw",
              height: "100vh",
              zIndex: 999999,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "30px",
              boxSizing: "border-box",
              background: "rgba(0,0,0,0.82)",
              backdropFilter: "blur(8px)",
              WebkitBackdropFilter: "blur(8px)"
            }}
            aria-modal="true"
            aria-labelledby="cart-modal-title"
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                setShowCart(false);
              }
            }}
          >
            <style>{`
              .dmi-cart-overlay{
                position:fixed!important;
                inset:0!important;
                width:100vw!important;
                height:100vh!important;
                z-index:999999!important;
                display:flex!important;
                align-items:center!important;
                justify-content:center!important;
                padding:24px!important;
                box-sizing:border-box!important;
                background:rgba(0,0,0,.86)!important;
                backdrop-filter:blur(10px)!important;
                -webkit-backdrop-filter:blur(10px)!important;
                font-family:"Roboto Condensed",Arial,sans-serif!important;
              }
              .dmi-cart-panel{
                position:relative!important;
                width:min(760px,92vw)!important;
                max-width:760px!important;
                max-height:88vh!important;
                margin:0 auto!important;
                padding:0!important;
                overflow:hidden!important;
                display:flex!important;
                flex-direction:column!important;
                background:
                  radial-gradient(circle at 50% 0%,rgba(239,49,84,.14),transparent 38%),
                  linear-gradient(145deg,#16070b 0%,#08090b 58%,#130509 100%)!important;
                border:1px solid #ef3154!important;
                border-radius:12px!important;
                color:#fff!important;
                box-shadow:0 30px 100px rgba(0,0,0,.95),0 0 55px rgba(239,49,84,.28)!important;
              }
              .dmi-cart-panel:before{
                content:""!important;
                position:absolute!important;
                top:0!important;
                left:0!important;
                right:0!important;
                height:3px!important;
                background:linear-gradient(90deg,transparent,#ef3154,transparent)!important;
                box-shadow:0 0 18px rgba(239,49,84,.8)!important;
                z-index:5!important;
              }
              .dmi-cart-header{
                display:flex!important;
                align-items:center!important;
                justify-content:space-between!important;
                gap:20px!important;
                padding:26px 30px 22px!important;
                border-bottom:1px solid rgba(239,49,84,.28)!important;
                background:rgba(0,0,0,.25)!important;
              }
              .dmi-cart-kicker{
                display:block!important;
                margin:0 0 7px!important;
                color:#ef3154!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:10px!important;
                font-weight:700!important;
                letter-spacing:3px!important;
                text-transform:uppercase!important;
              }
              .dmi-cart-heading h2{
                margin:0!important;
                color:#fff!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:28px!important;
                line-height:1.15!important;
                text-shadow:0 0 18px rgba(239,49,84,.2)!important;
              }
              .dmi-cart-subtitle{
                margin:7px 0 0!important;
                color:#aaa4a8!important;
                font-size:14px!important;
              }
              .dmi-cart-close{
                width:42px!important;
                height:42px!important;
                min-width:42px!important;
                border:1px solid #ef3154!important;
                border-radius:50%!important;
                background:rgba(0,0,0,.45)!important;
                color:#fff!important;
                font-size:22px!important;
                line-height:1!important;
                cursor:pointer!important;
              }
              .dmi-cart-close:hover{
                background:#ef3154!important;
                box-shadow:0 0 22px rgba(239,49,84,.45)!important;
              }
              .dmi-cart-empty{
                padding:54px 38px 42px!important;
                text-align:center!important;
              }
              .dmi-cart-empty-icon{
                width:64px!important;
                height:64px!important;
                margin:0 auto 18px!important;
                display:grid!important;
                place-items:center!important;
                border:1px solid rgba(239,49,84,.55)!important;
                border-radius:50%!important;
                background:rgba(239,49,84,.08)!important;
                font-size:28px!important;
                box-shadow:0 0 25px rgba(239,49,84,.12)!important;
              }
              .dmi-cart-empty h3{
                margin:0 0 10px!important;
                color:#fff!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:23px!important;
              }
              .dmi-cart-empty p{
                margin:0 auto 25px!important;
                max-width:460px!important;
                color:#aaa4a8!important;
                font-size:15px!important;
                line-height:1.5!important;
              }
              .dmi-cart-items{
                max-height:390px!important;
                overflow-y:auto!important;
                padding:20px 24px 8px!important;
                display:flex!important;
                flex-direction:column!important;
                gap:12px!important;
                scrollbar-width:thin!important;
                scrollbar-color:#ef3154 rgba(255,255,255,.04)!important;
              }
              .dmi-cart-item{
                display:grid!important;
                grid-template-columns:96px minmax(0,1fr) 38px!important;
                gap:17px!important;
                align-items:center!important;
                min-height:128px!important;
                padding:13px!important;
                background:linear-gradient(135deg,rgba(239,49,84,.08),rgba(0,0,0,.32))!important;
                border:1px solid rgba(239,49,84,.22)!important;
                border-radius:8px!important;
              }
              .dmi-cart-image-wrap{
                width:96px!important;
                height:96px!important;
                overflow:hidden!important;
                border:1px solid rgba(239,49,84,.35)!important;
                border-radius:6px!important;
                background:#050505!important;
              }
              .dmi-cart-image-wrap img{
                width:100%!important;
                height:100%!important;
                object-fit:cover!important;
                display:block!important;
              }
              .dmi-cart-info{min-width:0!important;}
              .dmi-cart-label{
                display:block!important;
                margin-bottom:5px!important;
                color:#ef3154!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:9px!important;
                font-weight:700!important;
                letter-spacing:1.5px!important;
              }
              .dmi-cart-info h4{
                margin:0 0 5px!important;
                color:#fff!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:14px!important;
                line-height:1.35!important;
                overflow:hidden!important;
                display:-webkit-box!important;
                -webkit-line-clamp:2!important;
                -webkit-box-orient:vertical!important;
              }
              .dmi-cart-code{
                margin:0!important;
                color:#ef3154!important;
                font-size:13px!important;
              }
              .dmi-cart-bottom{
                display:flex!important;
                align-items:center!important;
                justify-content:space-between!important;
                gap:15px!important;
                margin-top:12px!important;
              }
              .dmi-cart-quantity{
                display:flex!important;
                align-items:center!important;
                height:34px!important;
                border:1px solid rgba(239,49,84,.5)!important;
                border-radius:5px!important;
                overflow:hidden!important;
                background:#080808!important;
              }
              .dmi-cart-quantity button{
                width:34px!important;
                height:34px!important;
                border:0!important;
                background:transparent!important;
                color:#fff!important;
                font-size:19px!important;
                cursor:pointer!important;
              }
              .dmi-cart-quantity button:hover{background:rgba(239,49,84,.22)!important;}
              .dmi-cart-quantity span{
                width:32px!important;
                text-align:center!important;
                color:#fff!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:12px!important;
              }
              .dmi-cart-price{
                display:flex!important;
                flex-direction:column!important;
                align-items:flex-end!important;
                gap:3px!important;
              }
              .dmi-cart-price span{
                color:#8f898d!important;
                font-size:10px!important;
                text-transform:uppercase!important;
                letter-spacing:1px!important;
              }
              .dmi-cart-price strong{
                color:#ff405d!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:15px!important;
                white-space:nowrap!important;
              }
              .dmi-cart-item .remove-btn{
                width:38px!important;
                height:38px!important;
                min-width:38px!important;
                border:1px solid #ef3154!important;
                border-radius:5px!important;
                background:rgba(239,49,84,.08)!important;
                color:#ef3154!important;
                font-size:18px!important;
                cursor:pointer!important;
              }
              .dmi-cart-item .remove-btn:hover{background:#ef3154!important;color:#fff!important;}
              .dmi-cart-summary{
                margin:0 24px!important;
                padding:14px 0!important;
                border-top:1px solid rgba(255,255,255,.10)!important;
              }
              .dmi-cart-summary-line{
                display:flex!important;
                align-items:center!important;
                justify-content:space-between!important;
                padding:5px 0!important;
                color:#aaa4a8!important;
                font-size:14px!important;
              }
              .dmi-cart-summary-line strong{color:#fff!important;}
              .dmi-cart-summary-line.cart-total{
                margin-top:5px!important;
                padding-top:12px!important;
                border-top:1px solid rgba(239,49,84,.22)!important;
                color:#fff!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:15px!important;
              }
              .dmi-cart-summary-line.cart-total strong{
                color:#ff405d!important;
                font-size:20px!important;
              }
              .dmi-cart-actions{
                display:grid!important;
                grid-template-columns:1.35fr .65fr!important;
                gap:10px!important;
                padding:12px 24px 22px!important;
              }
              .dmi-cart-actions .checkout-btn{
                min-height:52px!important;
                border:0!important;
                border-radius:5px!important;
                background:linear-gradient(135deg,#ef3154,#d91535)!important;
                color:#fff!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:11px!important;
                font-weight:700!important;
                text-transform:uppercase!important;
                cursor:pointer!important;
                box-shadow:0 0 22px rgba(239,49,84,.18)!important;
              }
              .dmi-cart-actions .checkout-btn span{margin-left:8px!important;}
              .dmi-cart-actions .keep-shopping-btn{
                min-height:52px!important;
                border:1px solid #ef3154!important;
                border-radius:5px!important;
                background:transparent!important;
                color:#fff!important;
                font-family:"Orbitron",Arial,sans-serif!important;
                font-size:10px!important;
                font-weight:700!important;
                text-transform:uppercase!important;
                cursor:pointer!important;
              }
              @media(max-width:700px){
                .dmi-cart-overlay{padding:12px!important;}
                .dmi-cart-panel{width:96vw!important;max-height:94vh!important;}
                .dmi-cart-header{padding:20px!important;}
                .dmi-cart-items{padding:14px!important;max-height:50vh!important;}
                .dmi-cart-item{grid-template-columns:72px minmax(0,1fr) 34px!important;gap:11px!important;padding:10px!important;}
                .dmi-cart-image-wrap{width:72px!important;height:72px!important;}
                .dmi-cart-info h4{font-size:11px!important;}
                .dmi-cart-bottom{flex-direction:column!important;align-items:flex-start!important;gap:7px!important;}
                .dmi-cart-price{align-items:flex-start!important;}
                .dmi-cart-summary{margin:0 14px!important;}
                .dmi-cart-actions{grid-template-columns:1fr!important;padding:10px 14px 16px!important;}
              }
            `}</style>

            <div
              className="dmi-cart-panel"
              style={{
                position: "relative",
                top: "auto",
                right: "auto",
                bottom: "auto",
                left: "auto",
                width: "min(850px, 90vw)",
                maxWidth: "850px",
                maxHeight: "88vh",
                margin: "0 auto",
                padding: 0,
                boxSizing: "border-box",
                overflow: "hidden",
                display: "flex",
                flexDirection: "column",
                background: "linear-gradient(145deg,#18070c 0%,#09090b 55%,#130509 100%)",
                border: "1px solid #ef3154",
                borderRadius: "10px",
                color: "#fff",
                boxShadow: "0 30px 100px rgba(0,0,0,.9),0 0 70px rgba(239,49,84,.25)"
              }}
            >
              <div className="dmi-cart-header">
                <div className="dmi-cart-heading">
                  <span className="dmi-cart-kicker">
                    Pedido DMI
                  </span>
                  <h2 id="cart-modal-title">Mi carrito</h2>
                  <p className="dmi-cart-subtitle">
                    {totalProducts}{" "}
                    {totalProducts === 1 ? "unidad" : "unidades"} ·{" "}
                    {cart.length}{" "}
                    {cart.length === 1 ? "referencia" : "referencias"}
                  </p>
                </div>

                <button
                  className="dmi-cart-close"
                  aria-label="Cerrar carrito"
                  onClick={() => setShowCart(false)}
                >
                  ×
                </button>
              </div>

              {cart.length === 0 ? (
                <div className="dmi-cart-empty">
                  <div className="dmi-cart-empty-icon">🛒</div>
                  <h3>Tu carrito está vacío</h3>
                  <p>
                    Agrega repuestos desde el catálogo para verlos aquí.
                  </p>
                  <button
                    className="keep-shopping-btn"
                    onClick={() => setShowCart(false)}
                  >
                    Explorar catálogo
                  </button>
                </div>
              ) : (
                <>
                  <div className="dmi-cart-items">
                    {cart.map(item => (
                      <div
                        className="dmi-cart-item"
                        key={item.id}
                      >
                        <div className="dmi-cart-image-wrap">
                          <img
                            src={
                              item.image ||
                              DEFAULT_PRODUCT_IMAGE
                            }
                            alt={item.nombre}
                          />
                        </div>

                        <div className="dmi-cart-info">
                          <span className="dmi-cart-label">
                            REPUESTO DMI
                          </span>
                          <h4>{item.nombre}</h4>
                          <p className="dmi-cart-code">
                            Código: {item.codigo || "Sin código"}
                          </p>

                          <div className="dmi-cart-bottom">
                            <div className="dmi-cart-quantity">
                              <button
                                type="button"
                                aria-label={`Disminuir cantidad de ${item.nombre}`}
                                onClick={() =>
                                  updateQuantity(item.id, -1)
                                }
                              >
                                −
                              </button>
                              <span>{item.quantity}</span>
                              <button
                                type="button"
                                aria-label={`Aumentar cantidad de ${item.nombre}`}
                                onClick={() =>
                                  updateQuantity(item.id, 1)
                                }
                              >
                                +
                              </button>
                            </div>

                            <div className="dmi-cart-price">
                              <span>Subtotal</span>
                              <strong>
                                $
                                {(
                                  item.precioVenta * item.quantity
                                ).toLocaleString()}
                              </strong>
                            </div>
                          </div>
                        </div>

                        <button
                          type="button"
                          className="remove-btn"
                          aria-label={`Eliminar ${item.nombre}`}
                          title="Eliminar producto"
                          onClick={() =>
                            removeFromCart(item.id)
                          }
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="dmi-cart-summary">
                    <div className="dmi-cart-summary-line">
                      <span>Productos</span>
                      <strong>{totalProducts}</strong>
                    </div>

                    <div className="dmi-cart-summary-line cart-total">
                      <span>Total del pedido</span>
                      <strong>
                        ${totalPrice.toLocaleString()}
                      </strong>
                    </div>
                  </div>

                  <div className="dmi-cart-actions">
                    <button
                      className="checkout-btn"
                      onClick={() => {
                        setShowCart(false);
                        setShowMisCompras(true);
                      }}
                    >
                      Ver tus compras
                      <span>
                        ${totalPrice.toLocaleString()}
                      </span>
                    </button>

                    <button
                      className="keep-shopping-btn"
                      onClick={() => setShowCart(false)}
                    >
                      Seguir comprando
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>,
          document.body
        )}

      {/* PANEL TUS COMPRAS - MODAL CENTRADO */}
      {showMisCompras &&
        createPortal(
          <div
            className="dmi-compras-overlay"
            role="dialog"
            aria-modal="true"
            aria-labelledby="mis-compras-title"
            style={{
              position: "fixed",
              inset: 0,
              width: "100vw",
              height: "100vh",
              zIndex: 999998,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "30px",
              boxSizing: "border-box",
              background: "rgba(0,0,0,0.84)",
              backdropFilter: "blur(9px)",
              WebkitBackdropFilter: "blur(9px)"
            }}
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                setShowMisCompras(false);
              }
            }}
          >
            <style>{`
              .dmi-compras-overlay {
                font-family: "Orbitron", sans-serif;
              }

              .dmi-compras-panel {
                width: min(900px, 92vw);
                max-width: 900px;
                max-height: 88vh;
                max-height: 88dvh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-sizing: border-box;
                position: relative;
                background:
                  radial-gradient(circle at 50% 0%, rgba(239,49,84,.12), transparent 38%),
                  linear-gradient(145deg, #17070b 0%, #08090b 58%, #120509 100%);
                border: 1px solid rgba(239,49,84,.85);
                border-radius: 12px;
                color: #fff;
                box-shadow:
                  0 0 0 1px rgba(239,49,84,.08),
                  0 0 70px rgba(239,49,84,.25),
                  0 30px 100px rgba(0,0,0,.9);
                animation: dmiComprasIn .22s ease-out;
              }

              .dmi-compras-panel::before {
                content: "";
                position: absolute;
                left: 0;
                right: 0;
                top: 0;
                height: 3px;
                background: linear-gradient(90deg, transparent, #ef3154, transparent);
                box-shadow: 0 0 20px rgba(239,49,84,.8);
              }

              .dmi-compras-header {
                min-height: 105px;
                padding: 25px 30px;
                box-sizing: border-box;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 20px;
                flex-shrink: 0;
                border-bottom: 1px solid rgba(255,255,255,.10);
                background: rgba(0,0,0,.20);
              }

              .dmi-compras-heading {
                min-width: 0;
              }

              .dmi-compras-kicker {
                display: block;
                margin: 0 0 7px;
                color: #ef3154;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 3px;
                text-transform: uppercase;
              }

              .dmi-compras-heading h2 {
                margin: 0;
                color: #fff;
                font-size: clamp(1.45rem, 3vw, 2rem);
                line-height: 1.15;
              }

              .dmi-compras-subtitle {
                margin: 7px 0 0;
                color: rgba(255,255,255,.55);
                font-family: "Roboto Condensed", sans-serif;
                font-size: 13px;
              }

              .dmi-compras-close {
                width: 44px;
                height: 44px;
                min-width: 44px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid #ef3154;
                border-radius: 50%;
                background: rgba(0,0,0,.35);
                color: #fff;
                font-family: "Orbitron", sans-serif;
                font-size: 17px;
                cursor: pointer;
                transition: .2s ease;
              }

              .dmi-compras-close:hover {
                background: #ef3154;
                transform: rotate(90deg);
                box-shadow: 0 0 25px rgba(239,49,84,.4);
              }

              .dmi-compras-list {
                padding: 20px 30px 10px;
                max-height: 390px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 12px;
                box-sizing: border-box;
                scrollbar-width: thin;
                scrollbar-color: #ef3154 rgba(255,255,255,.05);
              }

              .dmi-compras-item {
                min-height: 125px;
                padding: 13px;
                display: grid;
                grid-template-columns: 92px minmax(0,1fr) 125px 42px;
                align-items: center;
                gap: 17px;
                box-sizing: border-box;
                background: rgba(0,0,0,.34);
                border: 1px solid rgba(239,49,84,.22);
                border-radius: 7px;
                transition: .2s ease;
              }

              .dmi-compras-item:hover {
                border-color: rgba(239,49,84,.60);
                background: rgba(239,49,84,.06);
              }

              .dmi-compras-item img {
                width: 92px;
                height: 92px;
                object-fit: cover;
                display: block;
                border: 1px solid rgba(239,49,84,.30);
                border-radius: 5px;
                background: #050505;
              }

              .dmi-compras-info {
                min-width: 0;
              }

              .dmi-compras-info h4 {
                margin: 0 0 6px;
                color: #fff;
                font-size: 13px;
                line-height: 1.4;
                overflow: hidden;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                line-clamp: 2;
                -webkit-box-orient: vertical;
              }

              .dmi-compras-code {
                margin: 0 0 12px;
                color: #ef3154;
                font-family: "Roboto Condensed", sans-serif;
                font-size: 12px;
              }

              .dmi-compras-qty {
                width: 105px;
                height: 34px;
                display: inline-flex;
                align-items: center;
                border: 1px solid rgba(239,49,84,.48);
                border-radius: 4px;
                overflow: hidden;
                background: rgba(0,0,0,.45);
              }

              .dmi-compras-qty button {
                width: 34px;
                height: 34px;
                min-width: 34px;
                padding: 0;
                border: 0;
                background: transparent;
                color: #fff;
                font-size: 17px;
                cursor: pointer;
              }

              .dmi-compras-qty button:hover {
                background: rgba(239,49,84,.20);
                color: #ff4964;
              }

              .dmi-compras-qty span {
                width: 37px;
                text-align: center;
                color: #fff;
                font-size: 12px;
              }

              .dmi-compras-price {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 6px;
              }

              .dmi-compras-unit {
                color: rgba(255,255,255,.42);
                font-family: "Roboto Condensed", sans-serif;
                font-size: 10px;
              }

              .dmi-compras-total {
                color: #ff405d;
                font-size: 15px;
                font-weight: 700;
                white-space: nowrap;
              }

              .dmi-compras-remove {
                width: 38px;
                height: 38px;
                min-width: 38px;
                padding: 0;
                border: 1px solid rgba(239,49,84,.65);
                border-radius: 4px;
                background: rgba(239,49,84,.08);
                color: #ef3154;
                cursor: pointer;
                font-family: "Orbitron", sans-serif;
              }

              .dmi-compras-remove:hover {
                background: #ef3154;
                color: #fff;
              }

              .dmi-compras-summary {
                margin: 0 30px;
                padding: 14px 0;
                border-top: 1px solid rgba(255,255,255,.10);
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
              }

              .dmi-compras-summary-row {
                display: flex;
                justify-content: space-between;
                gap: 15px;
                padding: 8px 12px;
                background: rgba(255,255,255,.025);
                border: 1px solid rgba(255,255,255,.06);
                color: rgba(255,255,255,.58);
                font-family: "Roboto Condensed", sans-serif;
                font-size: 12px;
              }

              .dmi-compras-summary-row strong {
                color: #fff;
              }

              .dmi-compras-total {
                margin: 0 30px;
                padding: 15px 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid rgba(239,49,84,.25);
                border-bottom: 1px solid rgba(239,49,84,.12);
              }

              .dmi-compras-total span:first-child {
                color: #fff;
                font-size: 14px;
              }

              .dmi-compras-total-price {
                color: #ff405d;
                font-size: 22px;
                font-weight: 700;
              }

              .dmi-compras-actions {
                padding: 16px 30px 24px;
                display: grid;
                grid-template-columns: 1.45fr .75fr;
                gap: 12px;
                box-sizing: border-box;
              }

              .dmi-compras-pay,
              .dmi-compras-keep {
                min-height: 55px;
                border-radius: 4px;
                font-family: "Orbitron", sans-serif;
                font-size: 11px;
                font-weight: 700;
                cursor: pointer;
                text-transform: uppercase;
              }

              .dmi-compras-pay {
                border: 1px solid #ef3154;
                background: linear-gradient(135deg, #ef3154, #d91535);
                color: #fff;
                box-shadow: 0 0 25px rgba(239,49,84,.15);
              }

              .dmi-compras-pay:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 30px rgba(239,49,84,.28);
              }

              .dmi-compras-keep {
                border: 1px solid rgba(239,49,84,.60);
                background: transparent;
                color: #fff;
              }

              .dmi-compras-keep:hover {
                background: rgba(239,49,84,.10);
              }

              .dmi-compras-empty {
                min-height: 300px;
                padding: 35px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: rgba(255,255,255,.55);
                text-align: center;
              }

              @keyframes dmiComprasIn {
                from {
                  opacity: 0;
                  transform: translateY(12px) scale(.97);
                }
                to {
                  opacity: 1;
                  transform: translateY(0) scale(1);
                }
              }

              @media (max-width: 700px) {
                .dmi-compras-overlay {
                  padding: 12px !important;
                }

                .dmi-compras-panel {
                  width: 96vw;
                  max-height: 94vh;
                  max-height: 94dvh;
                }

                .dmi-compras-header {
                  padding: 20px;
                }

                .dmi-compras-list {
                  padding: 15px;
                }

                .dmi-compras-item {
                  grid-template-columns: 70px minmax(0,1fr) 38px;
                  gap: 11px;
                }

                .dmi-compras-item img {
                  width: 70px;
                  height: 70px;
                }

                .dmi-compras-price {
                  grid-column: 2;
                  align-items: flex-start;
                }

                .dmi-compras-remove {
                  grid-column: 3;
                  grid-row: 1;
                }

                .dmi-compras-summary {
                  margin: 0 15px;
                  grid-template-columns: 1fr;
                  gap: 7px;
                }

                .dmi-compras-total {
                  margin: 0 15px;
                }

                .dmi-compras-actions {
                  padding: 12px 15px 18px;
                  grid-template-columns: 1fr;
                }
              }
            `}</style>

            <div className="dmi-compras-panel">
              <div className="dmi-compras-header">
                <div className="dmi-compras-heading">
                  <span className="dmi-compras-kicker">
                    PEDIDO DMI
                  </span>

                  <h2 id="mis-compras-title">
                    Tus Compras
                  </h2>

                  <p className="dmi-compras-subtitle">
                    {cart.length}{" "}
                    {cart.length === 1
                      ? "producto"
                      : "productos"}{" "}
                    · {totalProducts} unidades
                  </p>
                </div>

                <button
                  className="dmi-compras-close"
                  onClick={() =>
                    setShowMisCompras(false)
                  }
                  aria-label="Cerrar tus compras"
                >
                  X
                </button>
              </div>

              {cart.length === 0 ? (
                <div className="dmi-compras-empty">
                  No tienes productos agregados
                </div>
              ) : (
                <>
                  <div className="dmi-compras-list">
                    {cart.map(item => (
                      <div
                        className="dmi-compras-item"
                        key={item.id}
                      >
                        <img
                          src={
                            item.image ||
                            DEFAULT_PRODUCT_IMAGE
                          }
                          alt={item.nombre}
                        />

                        <div className="dmi-compras-info">
                          <h4>{item.nombre}</h4>

                          <p className="dmi-compras-code">
                            Código: {item.codigo}
                          </p>

                          <div className="dmi-compras-qty">
                            <button
                              onClick={() =>
                                updateQuantity(
                                  item.id,
                                  -1
                                )
                              }
                              aria-label="Disminuir cantidad"
                            >
                              −
                            </button>

                            <span>
                              {item.quantity}
                            </span>

                            <button
                              onClick={() =>
                                updateQuantity(
                                  item.id,
                                  +1
                                )
                              }
                              aria-label="Aumentar cantidad"
                            >
                              +
                            </button>
                          </div>
                        </div>

                        <div className="dmi-compras-price">
                          <span className="dmi-compras-unit">
                            C/U $
                            {item.precioVenta.toLocaleString()}
                          </span>

                          <span className="dmi-compras-total">
                            $
                            {(
                              item.precioVenta *
                              item.quantity
                            ).toLocaleString()}
                          </span>
                        </div>

                        <button
                          className="dmi-compras-remove"
                          onClick={() =>
                            removeFromCart(item.id)
                          }
                          aria-label={`Eliminar ${item.nombre}`}
                        >
                          X
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="dmi-compras-summary">
                    <div className="dmi-compras-summary-row">
                      <span>Unidades</span>
                      <strong>{totalProducts}</strong>
                    </div>

                    <div className="dmi-compras-summary-row">
                      <span>Referencias</span>
                      <strong>{cart.length}</strong>
                    </div>
                  </div>

                  <div className="dmi-compras-total">
                    <span>Total del pedido</span>

                    <span className="dmi-compras-total-price">
                      ${totalPrice.toLocaleString()}
                    </span>
                  </div>

                  <div className="dmi-compras-actions">
                    <button
                      className="dmi-compras-pay"
                      onClick={() =>
                        setShowConfirmModal(true)
                      }
                    >
                      Realizar pago
                    </button>

                    <button
                      className="dmi-compras-keep"
                      onClick={() =>
                        setShowMisCompras(false)
                      }
                    >
                      Seguir comprando
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>,
          document.body
        )}

      
      {catalogMessage &&
        createPortal(
          <div className="mc-modal-overlay">
            <div className="mc-modal">
              <p
                className="mc-modal-sub"
                style={{
                  textTransform: "uppercase",
                  letterSpacing: "2px",
                  color:
                    catalogMessage.type === "success"
                      ? "#7fffd4"
                      : "#ff4057",
                }}
              >
                {catalogMessage.eyebrow}
              </p>

              <h2>{catalogMessage.title}</h2>

              <p className="mc-modal-sub">
                {catalogMessage.text}
              </p>

              <div className="mc-modal-btns">
                <button
                  type="button"
                  className="mc-modal-confirm"
                  onClick={() =>
                    setCatalogMessage(null)
                  }
                >
                  Aceptar
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* MODAL CONFIRMACIÓN DEL PEDIDO */}
      {showConfirmModal &&
        createPortal(
          <div className="mc-modal-overlay">
            <div className="mc-modal">
              <h2>Confirmar pedido</h2>

              <p className="mc-modal-sub">
                Revisa tu pedido antes de continuar
              </p>

              <div className="mc-modal-list">
                {cart.map(item => (
                  <div
                    className="mc-modal-row"
                    key={item.id}
                  >
                    <span>
                      {item.nombre} x {item.quantity}
                    </span>

                    <span>
                      $
                      {(
                        item.precioVenta *
                        item.quantity
                      ).toLocaleString()}
                    </span>
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
                  onClick={() =>
                    setShowConfirmModal(false)
                  }
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* MODAL ACCESO REQUERIDO */}
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
                border:
                  "1px solid rgba(255,64,87,0.55)",
                boxShadow:
                  "0 0 40px rgba(255,64,87,0.12)",
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

              <h2
                style={{
                  margin: "0 0 14px",
                  fontSize: 26,
                }}
              >
                Inicia sesión para comprar
              </h2>

              <p
                style={{
                  color: "#c9c9cf",
                  margin: "0 0 24px",
                  lineHeight: 1.5,
                }}
              >
                Para proteger tus datos y registrar tu pedido
                correctamente, primero debes iniciar sesión.
              </p>

              <div
                style={{
                  display: "flex",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
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
                  onClick={() =>
                    setShowLoginRequiredModal(false)
                  }
                  style={{
                    flex: "1 1 160px",
                    background: "transparent",
                    color: "#fff",
                    border:
                      "1px solid rgba(255,255,255,0.4)",
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
      {isAdmin &&
        showCreateProduct &&
        createPortal(
          <div className="edit-product-overlay">
            <div className="edit-product-modal create-product-modal">
              <h2>NUEVO PRODUCTO</h2>

              {createError && (
                <p className="create-product-error">
                  {createError}
                </p>
              )}

              {[
                {
                  label: "Nombre",
                  key: "nombre",
                  type: "text",
                },
                {
                  label: "Código",
                  key: "codigo",
                  type: "text",
                },
                {
                  label: "Precio Venta",
                  key: "precioVenta",
                  type: "number",
                },
                {
                  label: "Precio Costo",
                  key: "precioCosto",
                  type: "number",
                },
                {
                  label: "Inventario",
                  key: "inventario",
                  type: "number",
                },
                {
                  label: "Categoría",
                  key: "categoria",
                  type: "text",
                },
                {
                  label: "Departamento",
                  key: "departamento",
                  type: "text",
                },
                {
                  label: "URL Imagen",
                  key: "image",
                  type: "text",
                },
              ].map(({ label, key, type }) => (
                <div
                  key={key}
                  className="edit-product-field"
                >
                  <label>{label.toUpperCase()}</label>

                  <input
                    type={type}
                    value={createForm[key] ?? ""}
                    onChange={e =>
                      setCreateForm({
                        ...createForm,
                        [key]: e.target.value,
                      })
                    }
                  />

                  {key === "image" &&
                    createForm.image && (
                      <img
                        className="edit-product-preview"
                        src={
                          createForm.image ||
                          DEFAULT_PRODUCT_IMAGE
                        }
                        alt="Vista previa"
                      />
                    )}
                </div>
              ))}

              <div className="edit-product-actions">
                <button
                  className="edit-product-save"
                  onClick={saveNewProduct}
                >
                  GUARDAR PRODUCTO
                </button>

                <button
                  className="edit-product-cancel"
                  onClick={() =>
                    setShowCreateProduct(false)
                  }
                >
                  CANCELAR
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* MODAL EDICIÓN */}
      {isAdmin && editingId &&
        createPortal(
          <div className="edit-product-overlay">
            <div className="edit-product-modal">
              <h2>EDITAR PRODUCTO</h2>

              {[
                { label: "Nombre", key: "nombre" },
                { label: "Codigo", key: "codigo" },
                { label: "Precio Venta", key: "precioVenta" },
                { label: "Precio Costo", key: "precioCosto" },
                { label: "Inventario", key: "inventario" },
                { label: "Categoria", key: "categoria" },
                { label: "Departamento", key: "departamento" },
                { label: "URL Imagen", key: "image" },
              ].map(({ label, key }) => (
                <div
                  key={key}
                  className="edit-product-field"
                >
                  <label>{label.toUpperCase()}</label>

                  <input
                    value={editForm[key] ?? ""}
                    onChange={e =>
                      setEditForm({
                        ...editForm,
                        [key]: e.target.value,
                      })
                    }
                  />

                  {key === "image" && editForm.image && (
                    <img
                      className="edit-product-preview"
                      src={
                        editForm.image ||
                        DEFAULT_PRODUCT_IMAGE
                      }
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
        <span className="catalog-section-kicker">
          Selección DMI / Destacados
        </span>

        <h2 className="section-title catalog-future-title">
          Repuestos Destacados
        </h2>

        <div className="hero-carousel">
          <button
            className="hero-btn left"
            onClick={prevSlide}
          >
            {"<"}
          </button>

          <img
            src={carouselImages[slide]}
            alt=""
            className="hero-image"
          />

          <button
            className="hero-btn right"
            onClick={nextSlide}
          >
            {">"}
          </button>
        </div>
      </section>

      {/* PRODUCTOS */}
      <section
        className="products"
        ref={productsRef}
      >
        <span className="catalog-section-kicker">
          Inventario digital / DMI
        </span>

        <h2 className="section-title catalog-future-title">
          {selectedCategory === "Todos"
            ? isAdmin
              ? "Catalogo de Productos"
              : "Inventario DMI"
            : selectedCategory}
        </h2>

        <p
          className="catalog-product-count"
          style={{
            textAlign: "center",
            color: "rgba(255,80,80,0.7)",
            fontSize: 13,
            marginBottom: 30,
            letterSpacing: 1,
          }}
        >
          {filteredProducts.length} producto
          {filteredProducts.length !== 1 ? "s" : ""}
          {selectedCategory !== "Todos"
            ? ` en ${selectedCategory}`
            : " en total"}
        </p>

        <div className="grid">
          {paginatedProducts.map(product => (
            <div
              className="product-card"
              key={product.id}
              onClick={() =>
                setSelectedProduct(product)
              }
              role="button"
              tabIndex="0"
              onKeyDown={e => {
                if (e.key === "Enter") {
                  setSelectedProduct(product);
                }
              }}
            >
              <img
                src={
                  product.image ||
                  DEFAULT_PRODUCT_IMAGE
                }
                alt={product.nombre}
              />

              <div className="info">
                <h3>{product.nombre}</h3>

                <p>Codigo: {product.codigo}</p>

                <p>
                  {isAdmin
                    ? `Inventario: ${product.inventario}`
                    : "Inventario DMI"}
                </p>

                {product.departamento &&
                  product.departamento !== "-" && (
                    <p
                      style={{
                        fontSize: 11,
                        color:
                          "rgba(255,255,255,0.4)",
                        marginTop: 4,
                      }}
                    >
                      {product.departamento}
                    </p>
                  )}

                <p className="price">
                  ${product.precioVenta.toLocaleString()}
                </p>

                <div className="product-card-actions">
                  <button
                    className="cart-add-btn"
                    onClick={e => {
                      e.stopPropagation();
                      addToCart(product);
                    }}
                  >
                    Agregar
                  </button>

                  <button
                    className="buy-btn"
                    onClick={e => {
                      e.stopPropagation();
                      goToPayment(product);
                    }}
                  >
                    Comprar
                  </button>

                  {isAdmin && (
                    <button
                      className="edit-product-btn"
                      onClick={e => {
                        e.stopPropagation();
                        openEdit(product);
                      }}
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

        {/* PAGINACIÓN */}
        {filteredProducts.length > PRODUCTS_PER_PAGE && (
          <div className="pagination">
            <button
              className="pagination-btn"
              disabled={currentPage === 1}
              onClick={() =>
                setCurrentPage(currentPage - 1)
              }
            >
              Anterior
            </button>

            <span className="pagination-info">
              Pagina {currentPage} de {totalPages}
            </span>

            <button
              className="pagination-btn"
              disabled={currentPage === totalPages}
              onClick={() =>
                setCurrentPage(currentPage + 1)
              }
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
              onClick={e => e.stopPropagation()}
            >
              <button
                className="product-detail-close"
                onClick={() =>
                  setSelectedProduct(null)
                }
              >
                X
              </button>

              <img
                src={
                  selectedProduct.image ||
                  DEFAULT_PRODUCT_IMAGE
                }
                alt={selectedProduct.nombre}
                className="product-detail-image"
              />

              <div className="product-detail-info">
                <p className="product-detail-category">
                  {selectedProduct.categoria}
                </p>

                <h2>{selectedProduct.nombre}</h2>

                <div className="product-detail-data">
                  <p>
                    <span>Codigo:</span>{" "}
                    {selectedProduct.codigo}
                  </p>

                  <p>
                    <span>
                      {isAdmin
                        ? "Inventario:"
                        : "Disponibilidad:"}
                    </span>{" "}
                    {isAdmin
                      ? selectedProduct.inventario
                      : "Inventario DMI"}
                  </p>

                  <p>
                    <span>Departamento:</span>{" "}
                    {selectedProduct.departamento ||
                      "Sin departamento"}
                  </p>
                </div>

                <p className="product-detail-price">
                  ${" "}
                  {selectedProduct.precioVenta.toLocaleString()}
                </p>

                <div className="product-detail-actions">
                  <button
                    onClick={() => {
                      addToCart(selectedProduct);
                      setSelectedProduct(null);
                    }}
                  >
                    Agregar
                  </button>

                  <button
                    className="buy-btn"
                    onClick={() =>
                      goToPayment(selectedProduct)
                    }
                  >
                    Comprar ahora
                  </button>

                  {isAdmin && (
                    <button
                      onClick={() => {
                        openEdit(selectedProduct);
                        setSelectedProduct(null);
                      }}
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

      {/* CHECKOUT */}
      {showCheckout &&
        createPortal(
          <Checkout
            total={checkoutTotal}
            items={checkoutItems}
            onPaid={() => {
              const paidIds = new Set(
                checkoutItems.map(item => item.id)
              );

              setCart(currentCart =>
                currentCart.filter(
                  item => !paidIds.has(item.id)
                )
              );
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