// src/js/RegistroPrueba.js
import React, { useState } from "react";
import { AuthService } from "../services/api"; // Ruta corregida hacia tu carpeta services

export default function RegistroPrueba() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    nombre: "",
    apellidos: "",
    documento: "",
    tipodedocumento: "CC",
    fechadenacimiento: "",
    telefono: "",
    usuarionombre: "",
  });

  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState({ texto: "", tipo: "" });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMensaje({ texto: "", tipo: "" });

    try {
      // Llama a tu api.js
      const resultado = await AuthService.registro(formData);
      
      setMensaje({ 
        texto: resultado.message || "¡Usuario registrado con éxito en Supabase!", 
        tipo: "success" 
      });
      
      setFormData({
        email: "", password: "", nombre: "", apellidos: "",
        documento: "", tipodedocumento: "CC", fechadenacimiento: "",
        telefono: "", usuarionombre: ""
      });
    } catch (error) {
      setMensaje({ 
        texto: `Error: ${error.message}`, 
        tipo: "error" 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "450px", margin: "40px auto", padding: "20px", border: "1px solid #333", borderRadius: "8px", background: "#1e1e1e", color: "#fff", fontFamily: "sans-serif" }}>
      <h3 style={{ marginTop: 0 }}>Prueba de Conexión: React ➡️ FastAPI ➡️ Supabase</h3>
      
      {mensaje.texto && (
        <div style={{ 
          padding: "10px", 
          marginBottom: "15px", 
          backgroundColor: mensaje.tipo === "success" ? "#1e4620" : "#5c1d1d",
          color: "#fff",
          borderRadius: "4px",
          fontSize: "14px"
        }}>
          {mensaje.texto}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <input style={{ padding: "8px" }} type="text" name="usuarionombre" placeholder="Username (ej: test_user)" value={formData.usuarionombre} onChange={handleChange} required />
        <input style={{ padding: "8px" }} type="text" name="nombre" placeholder="Nombre" value={formData.nombre} onChange={handleChange} required />
        <input style={{ padding: "8px" }} type="text" name="apellidos" placeholder="Apellidos" value={formData.apellidos} onChange={handleChange} required />
        <input style={{ padding: "8px" }} type="email" name="email" placeholder="Correo" value={formData.email} onChange={handleChange} required />
        <input style={{ padding: "8px" }} type="password" name="password" placeholder="Contraseña (mín. 6 caracteres)" value={formData.password} onChange={handleChange} required />
        
        <div style={{ display: "flex", gap: "10px" }}>
          <select name="tipodedocumento" value={formData.tipodedocumento} onChange={handleChange} style={{ width: "30%", padding: "8px" }}>
            <option value="CC">CC</option>
            <option value="CE">CE</option>
          </select>
          <input style={{ padding: "8px", width: "70%" }} type="text" name="documento" placeholder="Documento" value={formData.documento} onChange={handleChange} required />
        </div>

        <label style={{ fontSize: "12px", color: "#aaa" }}>Fecha de Nacimiento:</label>
        <input style={{ padding: "8px" }} type="date" name="fechadenacimiento" value={formData.fechadenacimiento} onChange={handleChange} required />
        <input style={{ padding: "8px" }} type="tel" name="telefono" placeholder="Teléfono" value={formData.telefono} onChange={handleChange} required />

        <button type="submit" disabled={loading} style={{ padding: "10px", backgroundColor: "#007bff", color: "white", border: "none", borderRadius: "4px", cursor: "pointer", fontWeight: "bold" }}>
          {loading ? "Registrando en BD..." : "Enviar Datos a Supabase"}
        </button>
      </form>
    </div>
  );
}