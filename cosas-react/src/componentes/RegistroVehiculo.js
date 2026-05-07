import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import './RegistroVehiculo.css';

const RegistrarVehiculos = () => {

  // =========================
  // STATES
  // =========================
  const [vehiculos, setVehiculos] = useState([]);
  const [editIndex, setEditIndex] = useState(null);

  const [formData, setFormData] = useState({
    codigo: "",
    placa: "",
    marca: "",
    modelo: "",
    motor: ""
  });

  const [busqueda, setBusqueda] = useState("");

  // =========================
  // CARGAR LOCALSTORAGE
  // =========================
  useEffect(() => {
    const data = JSON.parse(localStorage.getItem("vehiculos")) || [];
    setVehiculos(data);
  }, []);

  // =========================
  // GUARDAR LOCALSTORAGE
  // =========================
  useEffect(() => {
    localStorage.setItem("vehiculos", JSON.stringify(vehiculos));
  }, [vehiculos]);

  // =========================
  // HANDLE INPUTS
  // =========================
  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData({
      ...formData,
      [name]: value
    });
  };

  // =========================
  // GUARDAR VEHICULO
  // =========================
  const handleSubmit = (e) => {
    e.preventDefault();

    if (
      !formData.codigo.trim() ||
      !formData.placa.trim() ||
      !formData.marca.trim()
    ) {
      alert("Completa Código, Placa y Marca");
      return;
    }

    const nuevoVehiculo = {
      codigo: formData.codigo.trim(),
      placa: formData.placa.trim().toUpperCase(),
      marca: formData.marca.trim(),
      modelo: formData.modelo.trim(),
      motor: formData.motor.trim()
    };

    // EDITAR
    if (editIndex !== null) {

      const copia = [...vehiculos];
      copia[editIndex] = nuevoVehiculo;

      setVehiculos(copia);
      setEditIndex(null);

    } else {

      // NUEVO
      setVehiculos([...vehiculos, nuevoVehiculo]);
    }

    // LIMPIAR
    setFormData({
      codigo: "",
      placa: "",
      marca: "",
      modelo: "",
      motor: ""
    });
  };

  // =========================
  // EDITAR
  // =========================
  const editarVehiculo = (index) => {

    const v = vehiculos[index];

    setFormData({
      codigo: v.codigo,
      placa: v.placa,
      marca: v.marca,
      modelo: v.modelo,
      motor: v.motor
    });

    setEditIndex(index);
  };

  // =========================
  // ELIMINAR
  // =========================
  const eliminarVehiculo = (index) => {

    const confirmar = window.confirm(
      "¿Seguro que deseas eliminar este vehículo?"
    );

    if (!confirmar) return;

    const copia = [...vehiculos];
    copia.splice(index, 1);

    setVehiculos(copia);
  };

  // =========================
  // BUSQUEDA
  // =========================
  const vehiculosFiltrados = vehiculos.filter((v) =>
    v.codigo.toLowerCase().includes(busqueda.toLowerCase()) ||
    v.placa.toLowerCase().includes(busqueda.toLowerCase()) ||
    v.marca.toLowerCase().includes(busqueda.toLowerCase())
  );

  return (

    <motion.div
      className="Rvehiculo"

      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}

      transition={{ duration: 0.6 }}
    >

      {/* TITULO */}

      <motion.h1
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        REGISTRO DE <span>VEHÍCULOS</span>
      </motion.h1>

      {/* ========================= */}
      {/* FORMULARIO */}
      {/* ========================= */}

      <motion.form
        onSubmit={handleSubmit}

        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}

        transition={{ delay: 0.2 }}
      >

        <fieldset>

          <label>
            Código

            <motion.input
              whileFocus={{ scale: 1.02 }}

              type="text"
              name="codigo"
              placeholder="Ej: VH-001"

              value={formData.codigo}
              onChange={handleChange}
            />
          </label>

          <label>
            Placa

            <motion.input
              whileFocus={{ scale: 1.02 }}

              type="text"
              name="placa"
              placeholder="ABC-123"

              value={formData.placa}
              onChange={handleChange}
            />
          </label>

          <label>
            Marca

            <motion.input
              whileFocus={{ scale: 1.02 }}

              type="text"
              name="marca"
              placeholder="Toyota"

              value={formData.marca}
              onChange={handleChange}
            />
          </label>

          <label>
            Modelo

            <motion.input
              whileFocus={{ scale: 1.02 }}

              type="text"
              name="modelo"
              placeholder="Corolla"

              value={formData.modelo}
              onChange={handleChange}
            />
          </label>

          <label>
            Motor

            <motion.input
              whileFocus={{ scale: 1.02 }}

              type="text"
              name="motor"
              placeholder="2.0 Turbo"

              value={formData.motor}
              onChange={handleChange}
            />
          </label>

        </fieldset>

        {/* BOTON */}

        <motion.input

          whileHover={{
            scale: 1.03,
            boxShadow: "0px 0px 20px rgb(255,0,0)"
          }}

          whileTap={{ scale: 0.95 }}

          type="submit"

          value={
            editIndex !== null
              ? "ACTUALIZAR VEHÍCULO"
              : "GUARDAR VEHÍCULO"
          }
        />

      </motion.form>

      {/* ========================= */}
      {/* BUSCADOR */}
      {/* ========================= */}

      <motion.div

        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}

        transition={{ delay: 0.4 }}

        style={{ marginTop: "30px" }}
      >

        <input
          type="text"
          placeholder="Buscar vehículo..."

          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
        />

      </motion.div>

      {/* ========================= */}
      {/* TABLA */}
      {/* ========================= */}

      <motion.table
        className="tabla-vehiculos"

        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}

        transition={{ delay: 0.5 }}
      >

        <thead>

          <tr>
            <th>Código</th>
            <th>Placa</th>
            <th>Marca</th>
            <th>Modelo</th>
            <th>Motor</th>
            <th>Acciones</th>
          </tr>

        </thead>

        <tbody>

          <AnimatePresence>

            {vehiculosFiltrados.length === 0 ? (

              <tr>
                <td
                  colSpan="6"
                  style={{
                    textAlign: "center",
                    padding: "30px"
                  }}
                >
                  No hay vehículos registrados
                </td>
              </tr>

            ) : (

              vehiculosFiltrados.map((v, index) => (

                <motion.tr
                  key={index}

                  initial={{
                    opacity: 0,
                    x: -50
                  }}

                  animate={{
                    opacity: 1,
                    x: 0
                  }}

                  exit={{
                    opacity: 0,
                    x: 50
                  }}

                  transition={{
                    duration: 0.3
                  }}
                >

                  <td>{v.codigo}</td>
                  <td>{v.placa}</td>
                  <td>{v.marca}</td>
                  <td>{v.modelo || "-"}</td>
                  <td>{v.motor || "-"}</td>

                  <td
                    style={{
                      display: "flex",
                      justifyContent: "center",
                      gap: "10px"
                    }}
                  >

                    {/* EDITAR */}

                    <motion.button

                      whileHover={{
                        scale: 1.1
                      }}

                      whileTap={{
                        scale: 0.9
                      }}

                      type="button"
                      className="btn-editar"

                      onClick={() => editarVehiculo(index)}
                    >
                      ✏️
                    </motion.button>

                    {/* ELIMINAR */}

                    <motion.button

                      whileHover={{
                        scale: 1.1,
                        backgroundColor: "#ff0000"
                      }}

                      whileTap={{
                        scale: 0.9
                      }}

                      type="button"
                      className="btn-eliminar"

                      onClick={() => eliminarVehiculo(index)}
                    >
                      🗑
                    </motion.button>

                  </td>

                </motion.tr>

              ))
            )}

          </AnimatePresence>

        </tbody>

      </motion.table>

    </motion.div>
  );
};

export default RegistrarVehiculos;