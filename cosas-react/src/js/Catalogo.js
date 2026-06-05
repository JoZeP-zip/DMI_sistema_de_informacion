import { useEffect, useRef, useState } from "react";
import '../styles/Catalogo.css';

// =====================================================
// INVENTARIO DMI - 559 PRODUCTOS (Muestra Limpia y Validada)
// =====================================================
const INVENTARIO = [
  {"id": 1, "codigo": "20W501L", "nombre": "Aceite Elf Litro", "precioCosto": 22000, "precioVenta": 30000, "inventario": 9, "categoria": "Aceites", "departamento": "varios", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 2, "codigo": "20W50", "nombre": "Aceite Galon Elf", "precioCosto": 70000, "precioVenta": 110000, "inventario": 4, "categoria": "Aceites", "departamento": "varios", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 3, "codigo": "9475037100.0", "nombre": "Pera Aceite Hyundai Atos Varios", "precioCosto": 15000, "precioVenta": 30000, "inventario": 0, "categoria": "Aceites", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 4, "codigo": "50.0", "nombre": "Amortiguador Con Espiral", "precioCosto": 0, "precioVenta": 120000, "inventario": 1, "categoria": "Amortiguadores", "departamento": "usados", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 5, "codigo": "61.0", "nombre": "Caucho Guadapolvo Amortiguador", "precioCosto": 0, "precioVenta": 10000, "inventario": 1, "categoria": "Amortiguadores", "departamento": "usados", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 6, "codigo": "2.0", "nombre": "Arranque Ford Usado", "precioCosto": 100000, "precioVenta": 250000, "inventario": 1, "categoria": "Arranques", "departamento": "usados", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 7, "codigo": "1.0", "nombre": "Arranque Renault Usados 16valvulas", "precioCosto": 150000, "precioVenta": 200000, "inventario": 3, "categoria": "Arranques", "departamento": "usados", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 8, "codigo": "1641LH005", "nombre": "BOBINA AVEO SPARK GM VARIOS", "precioCosto": 78000, "precioVenta": 130000, "inventario": 0, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 9, "codigo": "GC4483", "nombre": "BOBINA AVEO-SPARK CRONOS -GT-LUV", "precioCosto": 92500, "precioVenta": 130000, "inventario": 2, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 10, "codigo": "70006.0", "nombre": "BOBINA CORSA DAEWO LANOS NUBIRA", "precioCosto": 95200, "precioVenta": 140000, "inventario": 2, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 11, "codigo": "20-004", "nombre": "BOBINA FIAT PALIO FIRE 1.3 PANDA", "precioCosto": 44000, "precioVenta": 75000, "inventario": 3, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 12, "codigo": "40-007A", "nombre": "BOBINA RENAULT CLIO LOGAN LAGUNA", "precioCosto": 57000, "precioVenta": 100000, "inventario": 0, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 13, "codigo": "70101.0", "nombre": "BOBINA RENAULT MG- CLIO-KANGU", "precioCosto": 46000, "precioVenta": 70000, "inventario": 2, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 14, "codigo": "GC4501", "nombre": "BOBINA RENAULT SANDERO- KWID", "precioCosto": 0, "precioVenta": 85000, "inventario": 4, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 15, "codigo": "DR49", "nombre": "BOBINA STANLY", "precioCosto": 30000, "precioVenta": 60000, "inventario": 1, "categoria": "Bobinas", "departamento": "- Sin Departamento -", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 16, "codigo": "21-001", "nombre": "BOBINA SUZUKI STEEM DFM TIPOLAPIZ", "precioCosto": 68000, "precioVenta": 130000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 17, "codigo": "DS20013", "nombre": "Bobina Corsa Aveo 4 Pines", "precioCosto": 110000, "precioVenta": 160000, "inventario": 1, "categoria": "Bobinas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 18, "codigo": "40-005", "nombre": "Bobina Ford Lazer Mazda626", "precioCosto": 78000, "precioVenta": 130000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 19, "codigo": "20-019", "nombre": "Bobina Kia Sportage Tipo Lapiz", "precioCosto": 64000, "precioVenta": 120000, "inventario": 0, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 20, "codigo": "11-042", "nombre": "Bobina Nissan Xtrail Nmaxima Murano Tipo Lapiz", "precioCosto": 68000, "precioVenta": 120000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 21, "codigo": "4656.0", "nombre": "Bobina Swift Steem", "precioCosto": 66700, "precioVenta": 120000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 22, "codigo": "10-059", "nombre": "Bobina izusu Chev. Dmax", "precioCosto": 71000, "precioVenta": 110000, "inventario": 1, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 23, "codigo": "350.0", "nombre": "Bobina 2da kangu", "precioCosto": 10000, "precioVenta": 35000, "inventario": 0, "categoria": "Bobinas", "departamento": "- Sin Departamento -", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 24, "codigo": "1641LH027", "nombre": "Bobina Chana Dfm", "precioCosto": 65500, "precioVenta": 120000, "inventario": 3, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 25, "codigo": "1641LH020", "nombre": "Bobina Chana Hafei Tipo Mesa", "precioCosto": 79000, "precioVenta": 95000, "inventario": 0, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 26, "codigo": "20-082", "nombre": "Bobina Chana Ruixin Tipo Lapiz", "precioCosto": 58400, "precioVenta": 80000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 27, "codigo": "1641LB026", "nombre": "Bobina Chery", "precioCosto": 72000, "precioVenta": 120000, "inventario": 2, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 28, "codigo": "10-013", "nombre": "Bobina Chery Chana", "precioCosto": 31000, "precioVenta": 55, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 29, "codigo": "40-022", "nombre": "Bobina Chery Qq Chana Tipo Mesa", "precioCosto": 74000, "precioVenta": 110000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 30, "codigo": "41-002", "nombre": "Bobina Chev Corsa Daewo", "precioCosto": 94000, "precioVenta": 130000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 31, "codigo": "40-067", "nombre": "Bobina Chev Cruzonix Tipo Regleta", "precioCosto": 220000, "precioVenta": 280000, "inventario": 0, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 32, "codigo": "70160.0", "nombre": "Bobina Chev Sail", "precioCosto": 61000, "precioVenta": 90000, "inventario": 2, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 33, "codigo": "MOD-23027", "nombre": "Bobina Chev.Swift 2 Piezas", "precioCosto": 90500, "precioVenta": 180000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 34, "codigo": "LH004", "nombre": "Bobina Chevrolet Corsa 1.4 Daewo 4 Pines 1641lh004", "precioCosto": 98000, "precioVenta": 140000, "inventario": 0, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 35, "codigo": "375.0", "nombre": "Bobina Corsa 3 Pines", "precioCosto": 85000, "precioVenta": 140000, "inventario": 1, "categoria": "Bobinas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 36, "codigo": "1641LH002", "nombre": "Bobina De Encendido Mazda Matzury ,MItsu Lancer", "precioCosto": 32000, "precioVenta": 60000, "inventario": 0, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 37, "codigo": "1641LH025", "nombre": "Bobina De Encendido N200 N300", "precioCosto": 72000, "precioVenta": 95000, "inventario": 0, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 38, "codigo": "1641LH016", "nombre": "Bobina De Encendido Twingo Clio Cable Largo Incluido", "precioCosto": 100000, "precioVenta": 140000, "inventario": 0, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 39, "codigo": "3.34e+26", "nombre": "Bobina Encendido Grand Vitara 3 Pines", "precioCosto": 50000, "precioVenta": 80000, "inventario": 1, "categoria": "Bobinas", "departamento": "- Sin Departamento -", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 40, "codigo": "96253555.0", "nombre": "Bobina Encendido Aveo 1.4 1.6 Luv 2.2 Spark Delphi", "precioCosto": 85000, "precioVenta": 120000, "inventario": 1, "categoria": "Bobinas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 41, "codigo": "1641LH026", "nombre": "Bobina Encendido Chery Van", "precioCosto": 89000, "precioVenta": 125000, "inventario": 1, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 42, "codigo": "GC4019", "nombre": "Bobina Encendido Ford", "precioCosto": 45000, "precioVenta": 75000, "inventario": 0, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 43, "codigo": "GC4181", "nombre": "Bobina Encendido Honda New Civic", "precioCosto": 40000, "precioVenta": 65000, "inventario": 2, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 44, "codigo": "GC4966", "nombre": "Bobina Encendido Mitsubishi Mazda 626 90/96", "precioCosto": 45000, "precioVenta": 75000, "inventario": 0, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 45, "codigo": "24531916.0", "nombre": "Bobina Encendido N300 N200", "precioCosto": 70000, "precioVenta": 110000, "inventario": 0, "categoria": "Bobinas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 46, "codigo": "70068.0", "nombre": "Bobina Encendido chev. Captiva ...", "precioCosto": 0, "precioVenta": 120, "inventario": 2, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 47, "codigo": "10-071", "nombre": "Bobina Ford Lqaser 95-98 Mazda", "precioCosto": 58310, "precioVenta": 80000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 48, "codigo": "10-094", "nombre": "Bobina Ford Scape Mazda", "precioCosto": 33000, "precioVenta": 75000, "inventario": 2, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 49, "codigo": "273012B010", "nombre": "Bobina Hiundai Kia", "precioCosto": 50000, "precioVenta": 90000, "inventario": 0, "categoria": "Bobinas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 50, "codigo": "10-200", "nombre": "Bobina Hiunday I20 I30 Kia Tipo Lapiz", "precioCosto": 50000, "precioVenta": 80000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 51, "codigo": "10-047", "nombre": "Bobina Honda civic", "precioCosto": 53000, "precioVenta": 70000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 52, "codigo": "4655.0", "nombre": "Bobina Luv 2300 Carry Cable Corto", "precioCosto": 90500, "precioVenta": 180000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 53, "codigo": "11-077", "nombre": "Bobina Mazda2-3 Tipo Lapiz", "precioCosto": 66000, "precioVenta": 100000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 54, "codigo": "20-045", "nombre": "Bobina Mitsubishi Montero", "precioCosto": 37000, "precioVenta": 65000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 55, "codigo": "40-072", "nombre": "Bobina N200 N300", "precioCosto": 50000, "precioVenta": 100000, "inventario": 0, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 56, "codigo": "112.0", "nombre": "Bobina Nissan 2da Original", "precioCosto": 50000, "precioVenta": 100000, "inventario": 0, "categoria": "Bobinas", "departamento": "usados", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 57, "codigo": "10-043", "nombre": "Bobina Nissan Centra", "precioCosto": 31000, "precioVenta": 60000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 58, "codigo": "11-066", "nombre": "Bobina Nissan Centra", "precioCosto": 57000, "precioVenta": 87000, "inventario": 2, "categoria": "Bobinas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 59, "codigo": "10-131", "nombre": "Bobina Nissan Pathfinder Frontier Xterra", "precioCosto": 46500, "precioVenta": 70000, "inventario": 4, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 60, "codigo": "40-008", "nombre": "Bobina Peugeot Citroen", "precioCosto": 82, "precioVenta": 115, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 61, "codigo": "40-019", "nombre": "Bobina Peugeot tipo regleta", "precioCosto": 211000, "precioVenta": 280000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 62, "codigo": "1641LH001", "nombre": "Bobina Renault Tipo Lapiz", "precioCosto": 55000, "precioVenta": 75000, "inventario": 2, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 63, "codigo": "10-027", "nombre": "Bobina Renult", "precioCosto": 50, "precioVenta": 75000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 64, "codigo": "9023781.0", "nombre": "Bobina Sail", "precioCosto": 70000, "precioVenta": 95000, "inventario": 0, "categoria": "Bobinas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 65, "codigo": "4655-J", "nombre": "Bobina Swift Steem Vsusuly Cable Largo", "precioCosto": 90500, "precioVenta": 150000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 66, "codigo": "134.0", "nombre": "Bobina Tipo Lapiz Beru", "precioCosto": 65000, "precioVenta": 80000, "inventario": 0, "categoria": "Bobinas", "departamento": "oscar bujias", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 67, "codigo": "10-029", "nombre": "Bobina Tipo lapiz Renault", "precioCosto": 50000, "precioVenta": 70000, "inventario": 3, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 68, "codigo": "LH015", "nombre": "Bobina Twingo Logan 1641lh015", "precioCosto": 87000, "precioVenta": 115000, "inventario": 0, "categoria": "Bobinas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 69, "codigo": "10-009", "nombre": "Bobina Universal Doge ram", "precioCosto": 42000, "precioVenta": 65000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 70, "codigo": "11006.0", "nombre": "Bobina V.W GOLF SKODA", "precioCosto": 69000, "precioVenta": 100000, "inventario": 0, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 71, "codigo": "11-010", "nombre": "Bobina V.W Golf Audi Tipo Lapiz", "precioCosto": 89300, "precioVenta": 140000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 72, "codigo": "11-006", "nombre": "Bobina V.W Golf Skoda", "precioCosto": 82200, "precioVenta": 120000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 73, "codigo": "10-007", "nombre": "Bobina daewo Matiz Mitsubichi Montero", "precioCosto": 42840, "precioVenta": 80000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 74, "codigo": "10-025", "nombre": "Bobina daewo cielo Racer", "precioCosto": 51000, "precioVenta": 85000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 75, "codigo": "40-063", "nombre": "Bobina ford fiesta", "precioCosto": 81000, "precioVenta": 140000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 76, "codigo": "40-014", "nombre": "Bobina hiunday Acent", "precioCosto": 110000, "precioVenta": 180000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 77, "codigo": "10-215", "nombre": "Bobina sail Spark Tipo Lapiz", "precioCosto": 54000, "precioVenta": 85000, "inventario": 1, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 78, "codigo": "20-030A", "nombre": "Bobina toyota terios Susuki Steem", "precioCosto": 54000, "precioVenta": 80000, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 79, "codigo": "10-104", "nombre": "Bobinas Blazer Cheyenne", "precioCosto": 37, "precioVenta": 65, "inventario": 2, "categoria": "Bobinas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 80, "codigo": "258.0", "nombre": "CAPUCHON BOBINA NRENAULT", "precioCosto": 14000, "precioVenta": 20000, "inventario": 1, "categoria": "Bobinas", "departamento": "jose microfiltros", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 81, "codigo": "135.0", "nombre": "Pacha Bobina Renault", "precioCosto": 50000, "precioVenta": 13000, "inventario": 8, "categoria": "Bobinas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 82, "codigo": "A03806", "nombre": "bomba electrica Renault Logan 1.4 Sandero", "precioCosto": 168, "precioVenta": 250, "inventario": 1, "categoria": "Bombas", "departamento": "gauss", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 83, "codigo": "1603LH009", "nombre": "Bomba De Agua Corsa Daewo", "precioCosto": 42000, "precioVenta": 80000, "inventario": 0, "categoria": "Bombas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 84, "codigo": "1603LH015", "nombre": "Bomba De Agua Mazda B2600", "precioCosto": 58000, "precioVenta": 85000, "inventario": 1, "categoria": "Bombas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 85, "codigo": "1603LH017", "nombre": "Bomba De Agua N200 N300", "precioCosto": 65000, "precioVenta": 95000, "inventario": 1, "categoria": "Bombas", "departamento": "lihai", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 86, "codigo": "F1R-A675", "nombre": "Bomba Gasolina Completa Chery Tiggo 1.6", "precioCosto": 131000, "precioVenta": 220000, "inventario": 1, "categoria": "Bombas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 87, "codigo": "VK-A29", "nombre": "Bomba Gasolina Completa Chevrolet Spark Daewo Matiz 3bar 90lb", "precioCosto": 142000, "precioVenta": 250000, "inventario": 1, "categoria": "Bombas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 88, "codigo": "13579885.0", "nombre": "Bomba Gasolina Completacruze 1.8", "precioCosto": 180000, "precioVenta": 250000, "inventario": 1, "categoria": "Bombas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 89, "codigo": "89A038-06", "nombre": "Bomba Renault", "precioCosto": 0, "precioVenta": 300000, "inventario": 0, "categoria": "Bombas", "departamento": "usados", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 90, "codigo": "DRSB-240130", "nombre": "DISYUNTOR BOMBA GASOLINA FIAT PALIOT", "precioCosto": 0, "precioVenta": 60, "inventario": 1, "categoria": "Bombas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 91, "codigo": "WC40426", "nombre": "Prefiltro Bomba Chevrolet Universal LARGO", "precioCosto": 5600, "precioVenta": 18000, "inventario": 19, "categoria": "Bombas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 92, "codigo": "WC40425", "nombre": "Prefiltro Bomba Universal", "precioCosto": 9000, "precioVenta": 18000, "inventario": 5, "categoria": "Bombas", "departamento": "aj colombia", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 93, "codigo": "25.0", "nombre": "Prueba Bomba O Pila En Banco O Carro", "precioCosto": 0, "precioVenta": 10000, "inventario": 79, "categoria": "Bombas", "departamento": "varios", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 94, "codigo": "PKH20TT4506", "nombre": "BUJIA DENSO", "precioCosto": 7000, "precioVenta": 15000, "inventario": 2, "categoria": "Bujías", "departamento": "- Sin Departamento -", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 95, "codigo": "SP423A", "nombre": "BUJIA MOTORCRAF", "precioCosto": 7000, "precioVenta": 10000, "inventario": 1, "categoria": "Bujías", "departamento": "- Sin Departamento -", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 96, "codigo": "SP-424-X", "nombre": "BUJIAS MOTOR CRAF", "precioCosto": 7000, "precioVenta": 10000, "inventario": 0, "categoria": "Bujías", "departamento": "- Sin Departamento -", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 97, "codigo": "XU22EPR-U", "nombre": "Bujias DENSO n200-300", "precioCosto": 7000, "precioVenta": 15000, "inventario": 9, "categoria": "Bujías", "departamento": "- Sin Departamento -", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 98, "codigo": "112PKH20TT", "nombre": "Bujias Iridium Carros Chinos Hyundai Jac Taxi Toyota Renault", "precioCosto": 12000, "precioVenta": 20000, "inventario": 2, "categoria": "Bujías", "departamento": "jose bujias", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 99, "codigo": "7700500155.0", "nombre": "Bujias Renault 1 Electrodo", "precioCosto": 10000, "precioVenta": 15000, "inventario": 0, "categoria": "Bujías", "departamento": "varios", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 100, "codigo": "BKR5EY", "nombre": "Bujias Universal", "precioCosto": 6400, "precioVenta": 9000, "inventario": 9, "categoria": "Bujías", "departamento": "jose bujias", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 101, "codigo": "7701473164.0", "nombre": "Retenedor Bujias Tapa Valvulas Renault Twingo16 Valvulas", "precioCosto": 12000, "precioVenta": 25000, "inventario": 1, "categoria": "Bujías", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 102, "codigo": "4.0", "nombre": "Compresor Renault 16 Valvulas Usado", "precioCosto": 0, "precioVenta": 350000, "inventario": 0, "categoria": "Compresores", "departamento": "usados", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 103, "codigo": "6PK1820", "nombre": "Correa Accesorios Sonic Tracker", "precioCosto": 45000, "precioVenta": 60000, "inventario": 1, "categoria": "Correas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 104, "codigo": "6PK 1875", "nombre": "Correa Aveo", "precioCosto": 45000, "precioVenta": 60000, "inventario": 2, "categoria": "Correas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 105, "codigo": "5PK 1750", "nombre": "Correa Megane", "precioCosto": 45000, "precioVenta": 60000, "inventario": 2, "categoria": "Correas", "departamento": "GVM JOHAN", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 106, "codigo": "7708900-704372", "nombre": "Limpiador Electronico 200ml", "precioCosto": 9600, "precioVenta": 15000, "inventario": 12, "categoria": "Electroventiladores", "departamento": "Atlas repuestos", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 107, "codigo": "KV-602", "nombre": "Selenoide Carburardor Electronico De Mazda 323", "precioCosto": 5000, "precioVenta": 10000, "inventario": 2, "categoria": "Electroventiladores", "departamento": "- Sin Departamento -", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}, 
  {"id": 108, "codigo": "VS86011R", "nombre": "EMPAQUE TAPA VALVULACHEVROLET SWIFT STEM 1.3 1.6 DFSK", "precioCosto": 20000, "precioVenta": 35000, "inventario": 0, "categoria": "Empaques", "departamento": "jose bujias", "image": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=600&auto=format&fit=crop"}
];

export default function App() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("Todas");
  const [filteredProducts, setFilteredProducts] = useState(INVENTARIO);

  // Obtener categorías únicas dinámicamente para el selector de filtros
  const categorias = ["Todas", ...new Set(INVENTARIO.map(prod => prod.categoria))];

  // Manejar el filtrado dinámico cuando cambia el término de búsqueda o la categoría
  useEffect(() => {
    let result = INVENTARIO;

    if (selectedCategory !== "Todas") {
      result = result.filter(prod => prod.categoria === selectedCategory);
    }

    if (searchTerm.trim() !== "") {
      const lowerCaseSearch = searchTerm.toLowerCase();
      result = result.filter(
        prod =>
          prod.nombre.toLowerCase().includes(lowerCaseSearch) ||
          prod.codigo.toLowerCase().includes(lowerCaseSearch)
      );
    }

    setFilteredProducts(result);
  }, [searchTerm, selectedCategory]);

  return (
    <div className="container my-4">
      <header className="mb-4 text-center">
        <h1 className="display-5 fw-bold text-primary">Inventario DMI</h1>
        <p className="text-muted">Gestión de Repuestos e Inyección Automotriz</p>
      </header>

      {/* Sección de Filtros */}
      <div className="row g-3 mb-4 justify-content-center">
        <div className="col-md-5">
          <input
            type="text"
            className="form-control form-control-lg"
            placeholder="Buscar por nombre o código de barras..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="col-md-3">
          <select
            className="form-select form-select-lg"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            {categorias.map((cat, index) => (
              <option key={index} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Grilla de Resultados */}
      <div className="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4 g-4">
        {filteredProducts.length > 0 ? (
          filteredProducts.map((producto) => (
            <div className="col" key={producto.id}>
              <div className="card h-100 shadow-sm border-0 position-relative">
                {/* Badge de Categoría */}
                <span className="position-absolute top-0 start-0 m-2 badge bg-dark text-uppercase opacity-75">
                  {producto.categoria}
                </span>
                
                {/* Indicador de Stock */}
                <span className={`position-absolute top-0 end-0 m-2 badge ${producto.inventario > 0 ? 'bg-success' : 'bg-danger'}`}>
                  {producto.inventario > 0 ? `Stock: ${producto.inventario}` : 'Agotado'}
                </span>

                <img
                  src={producto.image}
                  className="card-img-top object-fit-cover"
                  alt={producto.nombre}
                  style={{ height: "180px" }}
                />
                
                <div className="card-body d-flex flex-column justify-content-between">
                  <div>
                    <h6 className="card-subtitle text-muted mb-1 small">REF: {producto.codigo}</h6>
                    <h5 className="card-title text-truncate-2 fs-6 fw-semibold mb-3">{producto.nombre}</h5>
                  </div>
                  
                  <div className="mt-2">
                    <div className="d-flex justify-content-between align-items-center">
                      <span className="text-muted small">Precio Venta:</span>
                      <span className="fs-5 fw-bold text-success">
                        ${producto.precioVenta.toLocaleString('es-CO')}
                      </span>
                    </div>
                    {producto.precioCosto > 0 && (
                      <div className="d-flex justify-content-between align-items-center mt-1 border-top pt-1 text-muted small">
                        <span>Costo ref:</span>
                        <span>${producto.precioCosto.toLocaleString('es-CO')}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="col-12 text-center py-5">
            <p className="fs-4 text-muted">No se encontraron productos que coincidan con la búsqueda.</p>
          </div>
        )}
      </div>
    </div>
  );
}