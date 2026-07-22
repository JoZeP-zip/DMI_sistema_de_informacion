import React, { useEffect, useMemo, useState } from 'react';
import { MiCuentaService } from '../services/api';
import { openInvoiceDocument } from './invoice';

const money = (value) => {
  const number = Number(value || 0);
  return number.toLocaleString('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  });
};

const clean = (value, fallback = 'Por definir') => {
  if (value === null || value === undefined || value === '') return fallback;
  return value;
};

const estadoClase = (estado = '') => String(estado).toLowerCase().replace(/[^a-z0-9_]/g, '-');

const estadoOrdenPasos = [
  { key: 'abierta', label: 'Orden' },
  { key: 'diagnostico', label: 'Diagnostico' },
  { key: 'cotizada', label: 'Cotizacion' },
  { key: 'en_reparacion', label: 'Reparacion' },
  { key: 'facturada', label: 'Factura' },
  { key: 'entregada', label: 'Entrega' },
];

const pasoIndexPorEstado = {
  abierta: 0,
  diagnostico: 1,
  cotizada: 2,
  aprobada: 2,
  en_reparacion: 3,
  finalizada: 3,
  facturada: 4,
  pagada: 4,
  entregada: 5,
};

const EmptyState = ({ icon = 'bi-info-circle', text }) => (
  <div className="user-empty-state">
    <i className={`bi ${icon}`} />
    <span>{text}</span>
  </div>
);

const Section = ({ title, icon, children, className = '' }) => (
  <article className={`user-account-card ${className}`}>
    <div className="user-account-card-head">
      <h3><i className={`bi ${icon}`} /> {title}</h3>
    </div>
    {children}
  </article>
);

const DetailModal = ({ title, children, onClose }) => {
  if (!title) return null;
  return (
    <div className="user-detail-overlay" role="dialog" aria-modal="true">
      <section className="user-detail-modal">
        <button type="button" className="user-detail-close" onClick={onClose} aria-label="Cerrar">
          <i className="bi bi-x-lg" />
        </button>
        <h2>{title}</h2>
        {children}
      </section>
    </div>
  );
};

const OrderSteps = ({ estado }) => {
  const current = pasoIndexPorEstado[String(estado || 'abierta').toLowerCase()] ?? 0;
  return (
    <div className="user-order-steps">
      {estadoOrdenPasos.map((paso, index) => (
        <span key={paso.key} className={index <= current ? 'done' : ''}>{paso.label}</span>
      ))}
    </div>
  );
};

export default function MiCuenta({ onAddVehicle, onScheduleAppointment }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [historialActivo, setHistorialActivo] = useState(null);
  const [ordenActiva, setOrdenActiva] = useState(null);
  const [vehiculoSeleccionadoId, setVehiculoSeleccionadoId] = useState('');

  useEffect(() => {
    let mounted = true;

    MiCuentaService.obtener()
      .then((response) => {
        if (!mounted) return;
        setData(response);
        setError('');
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || 'No se pudo cargar Mi Cuenta.');
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const resumen = data?.resumen || {};
  const usuario = data?.usuario || {};
  const nombre = usuario.nombre || localStorage.getItem('nombre') || 'cliente';
  const vehiculosCuenta = data?.vehiculos || [];

  useEffect(() => {
    if (!vehiculoSeleccionadoId && vehiculosCuenta.length) {
      setVehiculoSeleccionadoId(String(vehiculosCuenta[0].idvehiculo));
    }
  }, [vehiculoSeleccionadoId, vehiculosCuenta]);

  const vehiculoSeleccionado = useMemo(() => {
    if (!vehiculosCuenta.length) return null;
    return vehiculosCuenta.find((vehiculo) => String(vehiculo.idvehiculo) === String(vehiculoSeleccionadoId)) || vehiculosCuenta[0];
  }, [vehiculosCuenta, vehiculoSeleccionadoId]);

  const vehiculoIdActual = vehiculoSeleccionado?.idvehiculo;
  const ordenesVehiculo = useMemo(() => {
    if (!vehiculoIdActual) return data?.ordenes || [];
    return (data?.ordenes || []).filter((orden) => String(orden.vehiculo_id) === String(vehiculoIdActual));
  }, [data, vehiculoIdActual]);

  const ordenIdsVehiculo = useMemo(() => new Set(ordenesVehiculo.map((orden) => orden.idorden)), [ordenesVehiculo]);
  const citasVehiculo = useMemo(() => {
    if (!vehiculoIdActual) return data?.citas || [];
    return (data?.citas || []).filter((cita) => String(cita.idvehiculo || cita.vehiculos_idvehiculo) === String(vehiculoIdActual));
  }, [data, vehiculoIdActual]);
  const serviciosVehiculo = useMemo(() => (data?.servicios_orden || []).filter((item) => ordenIdsVehiculo.has(item.orden_id)), [data, ordenIdsVehiculo]);
  const repuestosVehiculo = useMemo(() => (data?.repuestos_orden || []).filter((item) => ordenIdsVehiculo.has(item.orden_id)), [data, ordenIdsVehiculo]);
  const facturasVehiculo = useMemo(() => (data?.facturas || []).filter((factura) => ordenIdsVehiculo.has(factura.orden_id)), [data, ordenIdsVehiculo]);
  const historialVehiculo = useMemo(() => {
    if (!vehiculoIdActual) return data?.historial || [];
    return (data?.historial || []).filter((evento) => String(evento.vehiculo_id) === String(vehiculoIdActual));
  }, [data, vehiculoIdActual]);

  const ordenesActivas = useMemo(() => {
    return ordenesVehiculo.filter((orden) => {
      const estado = String(orden.estado || '').toLowerCase();
      return !['entregada', 'cancelada'].includes(estado);
    });
  }, [ordenesVehiculo]);

  const serviciosPorOrden = (ordenId) => serviciosVehiculo.filter((item) => item.orden_id === ordenId);
  const repuestosPorOrden = (ordenId) => repuestosVehiculo.filter((item) => item.orden_id === ordenId);
  const facturaPorOrden = (ordenId) => facturasVehiculo.find((item) => item.orden_id === ordenId);
  const pagosPorFactura = (facturaId) => (data?.pagos_facturas || []).filter((item) => item.factura_id === facturaId);

  const abrirFactura = (factura) => {
    const servicios = serviciosPorOrden(factura.orden_id);
    const repuestos = repuestosPorOrden(factura.orden_id);
    const orden = ordenesVehiculo.find((item) => item.idorden === factura.orden_id);
    const pagos = pagosPorFactura(factura.idfactura);

    const items = [
      ...servicios.map((item) => ({
        description: item.descripcion || item.descripcionservicio || 'Servicio tecnico',
        code: item.codigoservicio || `ORD-${item.orden_id}`,
        quantity: Number(item.cantidad || 1),
        unitPrice: Number(item.valor_unitario || 0),
        total: Number(item.subtotal || 0),
      })),
      ...repuestos.map((item) => ({
        description: item.descripcion || item.descripcionproductos || 'Repuesto usado',
        code: item.codigoproductos || `REP-${item.iddetalle_repuesto}`,
        quantity: Number(item.cantidad || 1),
        unitPrice: Number(item.valor_unitario || 0),
        total: Number(item.subtotal || 0),
      })),
    ];

    openInvoiceDocument({
      type: 'SERVICIO',
      number: factura.codigo_factura,
      date: factura.fecha_factura || new Date().toLocaleString('es-CO'),
      logoUrl: `${window.location.origin}/assets/images/logoempresa.jpg`,
      customer: usuario,
      paymentMethod: pagos[0]?.metodo || 'Pendiente/registrado por taller',
      title: 'Factura de servicio',
      concept: orden?.motivo_ingreso || factura.codigo_orden || 'Mantenimiento o reparacion',
      service: orden,
      items: items.length ? items : [{
        description: factura.codigo_orden || 'Servicio tecnico automotriz',
        code: factura.codigo_factura,
        quantity: 1,
        unitPrice: Number(factura.total || 0),
        total: Number(factura.total || 0),
      }],
      subtotal: Number(factura.subtotal || factura.total || 0),
      total: Number(factura.total || 0),
    });
  };

  const abrirOrden = (orden) => {
    setOrdenActiva({
      orden,
      servicios: serviciosPorOrden(orden.idorden),
      repuestos: repuestosPorOrden(orden.idorden),
      factura: facturaPorOrden(orden.idorden),
    });
  };

  const verHistorial = (evento) => {
    const orden = ordenesVehiculo.find((item) => item.idorden === evento.orden_id);
    const servicios = serviciosPorOrden(evento.orden_id);
    const repuestos = repuestosPorOrden(evento.orden_id);
    const factura = facturasVehiculo.find((item) => item.idfactura === evento.factura_id || item.orden_id === evento.orden_id);
    setHistorialActivo({ evento, orden, servicios, repuestos, factura });
  };

  if (loading) {
    return (
      <main className="user-account-shell">
        <div className="user-account-loading">Cargando tu informacion...</div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="user-account-shell">
        <div className="user-account-error">{error}</div>
      </main>
    );
  }

  return (
    <main className="user-account-shell">
      <section className="user-account-hero">
        <div>
          <span>Centro del cliente</span>
          <h1>Mi <strong>Cuenta</strong></h1>
          <p>
            Hola, <b>{nombre}</b>. Aqui puedes ver tus vehiculos, citas,
            ordenes de trabajo, productos usados, facturas e historial.
          </p>
        </div>
        <div className="user-account-actions">
          <button type="button" onClick={onAddVehicle}>Agregar vehiculo</button>
          <button type="button" className="outline" onClick={onScheduleAppointment}>Agendar cita</button>
        </div>
      </section>

      <section className="user-account-summary">
        <article><span>Vehiculos</span><strong>{resumen.vehiculos || 0}</strong></article>
        <article><span>Citas activas</span><strong>{resumen.citas_activas || 0}</strong></article>
        <article><span>Ordenes activas</span><strong>{resumen.ordenes_activas || 0}</strong></article>
        <article><span>Facturas pendientes</span><strong>{resumen.facturas_pendientes || 0}</strong></article>
      </section>

      {ordenesActivas.length > 0 && (
        <section className="user-account-card wide user-current-work">
          <div className="user-account-card-head">
            <h3><i className="bi bi-activity" /> Estado actual del taller</h3>
          </div>
          <div className="user-current-work-grid">
            {ordenesActivas.slice(0, 3).map((orden) => (
              <article key={orden.idorden}>
                <strong>{orden.codigo_orden}</strong>
                <span>{clean(orden.marca, '')} {clean(orden.modelo, '')} - {clean(orden.placa, 'Sin placa')}</span>
                <div className="user-progress" aria-label={`Progreso ${orden.progreso || 0}%`}>
                  <span style={{ width: `${orden.progreso || 0}%` }} />
                </div>
                <small>{orden.progreso || 0}% completado | {clean(orden.estado_label, orden.estado)}</small>
                <OrderSteps estado={orden.estado} />
                <button type="button" onClick={() => abrirOrden(orden)}>Ver detalle</button>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="user-account-grid">
        <Section title="Vehiculos" icon="bi-car-front-fill">
          {vehiculosCuenta.length ? (
            <div className="user-vehicle-panel">
              <label>Elegir vehiculo</label>
              <select
                value={vehiculoSeleccionadoId}
                onChange={(event) => setVehiculoSeleccionadoId(event.target.value)}
              >
                {vehiculosCuenta.map((vehiculo) => (
                  <option key={vehiculo.idvehiculo} value={vehiculo.idvehiculo}>
                    {clean(vehiculo.placa, 'Sin placa')} - {clean(vehiculo.marca, '')} {clean(vehiculo.modelo, '')}
                  </option>
                ))}
              </select>

              {vehiculoSeleccionado && (
                <div className="user-account-item selected">
                  <strong>{clean(vehiculoSeleccionado.marca)} {clean(vehiculoSeleccionado.modelo, '')}</strong>
                  <span>Placa {clean(vehiculoSeleccionado.placa)} | Tipo {clean(vehiculoSeleccionado.tipo_vehiculo)}</span>
                  <small>Motor {clean(vehiculoSeleccionado.motor)} | Capacidad {clean(vehiculoSeleccionado.capacidad, 0)} | Km {clean(vehiculoSeleccionado.kilometraje_actual, 0)}</small>
                </div>
              )}

              <small className="user-vehicle-count">{vehiculosCuenta.length} de 10 vehiculos registrados</small>
            </div>
          ) : <EmptyState icon="bi-car-front" text="Aun no tienes vehiculos registrados." />}
        </Section>

        <Section title="Citas" icon="bi-calendar-check-fill">
          {citasVehiculo.length ? (
            <div className="user-account-list">
              {citasVehiculo.slice(0, 6).map((cita) => (
                <div className="user-account-item" key={cita.idcita}>
                  <strong>{clean(cita.motivo, 'Servicio agendado')}</strong>
                  <span>{clean(cita.fecha, '')} {clean(cita.hora, '')} | {clean(cita.vehiculo, 'Vehiculo')}</span>
                  <small className={`user-status ${estadoClase(cita.estado)}`}>{clean(cita.estado, 'pendiente')}</small>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="bi-calendar-x" text="No tienes citas registradas." />}
        </Section>
        <Section title="Repuestos usados" icon="bi-box-seam-fill">
          {repuestosVehiculo.length ? (
            <div className="user-account-list">
              {repuestosVehiculo.slice(0, 8).map((item) => (
                <div className="user-account-item" key={item.iddetalle_repuesto}>
                  <strong>{clean(item.descripcion)}</strong>
                  <span>Cantidad {clean(item.cantidad, 1)} | {money(item.subtotal)}</span>
                  <small>Orden #{item.orden_id}</small>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="bi-box" text="Todavia no hay repuestos usados en tus ordenes." />}
        </Section>

        <Section title="Facturas" icon="bi-receipt-cutoff">
          {facturasVehiculo.length ? (
            <div className="user-account-list">
              {facturasVehiculo.map((factura) => (
                <div className="user-account-item user-action-item" key={factura.idfactura}>
                  <strong>{factura.codigo_factura}</strong>
                  <span>{money(factura.total)} | Saldo {money(factura.saldo)}</span>
                  <small className={`user-status ${estadoClase(factura.estado)}`}>{clean(factura.estado)}</small>
                  <button type="button" onClick={() => abrirFactura(factura)}>Ver factura</button>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="bi-receipt" text="No tienes facturas generadas." />}
        </Section>

        <Section title="Historial" icon="bi-clock-history" className="wide">
          {historialVehiculo.length ? (
            <div className="user-history-list">
              {historialVehiculo.map((evento) => (
                <div className="user-history-item user-action-item" key={evento.idhistorial}>
                  <strong>{clean(evento.tipo_evento)}</strong>
                  <span>{clean(evento.fecha_evento, '')} | {clean(evento.placa, '')}</span>
                  <p>{clean(evento.descripcion, '')}</p>
                  <button type="button" onClick={() => verHistorial(evento)}>Ver historial</button>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="bi-clock" text="Aun no hay historial para tus vehiculos." />}
        </Section>
      </section>

      <DetailModal title={ordenActiva ? 'Detalle de orden' : ''} onClose={() => setOrdenActiva(null)}>
        {ordenActiva && (
          <div className="user-detail-content">
            <div className="user-detail-grid">
              <article><span>Orden</span><strong>{clean(ordenActiva.orden.codigo_orden)}</strong></article>
              <article><span>Estado</span><strong>{clean(ordenActiva.orden.estado_label, ordenActiva.orden.estado)}</strong></article>
              <article><span>Progreso</span><strong>{ordenActiva.orden.progreso || 0}%</strong></article>
              <article><span>Vehiculo</span><strong>{clean(ordenActiva.orden.marca, '')} {clean(ordenActiva.orden.modelo, '')}</strong></article>
              <article><span>Placa</span><strong>{clean(ordenActiva.orden.placa)}</strong></article>
              <article><span>Total</span><strong>{money(ordenActiva.orden.total_orden)}</strong></article>
            </div>
            <OrderSteps estado={ordenActiva.orden.estado} />
            <p className="user-detail-description">{clean(ordenActiva.orden.motivo_ingreso || ordenActiva.orden.observaciones_cliente, 'Sin descripcion registrada.')}</p>

            <h3>Servicios realizados</h3>
            {ordenActiva.servicios.length ? ordenActiva.servicios.map((item) => (
              <div className="user-detail-line" key={item.iddetalle_servicio}>
                <span>{clean(item.descripcion)} x {clean(item.cantidad, 1)}</span><strong>{money(item.subtotal)}</strong>
              </div>
            )) : <p className="user-muted">No hay servicios registrados para esta orden.</p>}

            <h3>Repuestos utilizados</h3>
            {ordenActiva.repuestos.length ? ordenActiva.repuestos.map((item) => (
              <div className="user-detail-line" key={item.iddetalle_repuesto}>
                <span>{clean(item.descripcion)} x {clean(item.cantidad, 1)}</span><strong>{money(item.subtotal)}</strong>
              </div>
            )) : <p className="user-muted">No hay repuestos registrados para esta orden.</p>}

            {ordenActiva.factura && (
              <div className="user-detail-footer">
                <button type="button" onClick={() => abrirFactura(ordenActiva.factura)}>Ver factura</button>
              </div>
            )}
          </div>
        )}
      </DetailModal>

      <DetailModal title={historialActivo ? 'Historial detallado' : ''} onClose={() => setHistorialActivo(null)}>
        {historialActivo && (
          <div className="user-detail-content">
            <div className="user-detail-grid">
              <article><span>Evento</span><strong>{clean(historialActivo.evento.tipo_evento)}</strong></article>
              <article><span>Fecha</span><strong>{clean(historialActivo.evento.fecha_evento)}</strong></article>
              <article><span>Vehiculo</span><strong>{clean(historialActivo.evento.marca, '')} {clean(historialActivo.evento.modelo, '')}</strong></article>
              <article><span>Placa</span><strong>{clean(historialActivo.evento.placa)}</strong></article>
              <article><span>Orden</span><strong>{clean(historialActivo.orden?.codigo_orden, `#${historialActivo.evento.orden_id}`)}</strong></article>
              <article><span>Costo</span><strong>{money(historialActivo.evento.costo_total || historialActivo.factura?.total)}</strong></article>
            </div>
            <p className="user-detail-description">{clean(historialActivo.evento.descripcion, 'Sin descripcion registrada.')}</p>

            <h3>Servicios realizados</h3>
            {historialActivo.servicios.length ? historialActivo.servicios.map((item) => (
              <div className="user-detail-line" key={item.iddetalle_servicio}>
                <span>{clean(item.descripcion)}</span><strong>{money(item.subtotal)}</strong>
              </div>
            )) : <p className="user-muted">No hay servicios registrados para esta orden.</p>}

            <h3>Repuestos utilizados</h3>
            {historialActivo.repuestos.length ? historialActivo.repuestos.map((item) => (
              <div className="user-detail-line" key={item.iddetalle_repuesto}>
                <span>{clean(item.descripcion)} x {clean(item.cantidad, 1)}</span><strong>{money(item.subtotal)}</strong>
              </div>
            )) : <p className="user-muted">No hay repuestos registrados para esta orden.</p>}

            {historialActivo.factura && (
              <div className="user-detail-footer">
                <button type="button" onClick={() => abrirFactura(historialActivo.factura)}>Ver factura</button>
              </div>
            )}
          </div>
        )}
      </DetailModal>
    </main>
  );
}

