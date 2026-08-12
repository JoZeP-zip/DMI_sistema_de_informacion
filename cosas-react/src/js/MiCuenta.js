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
  const [cotizacionActiva, setCotizacionActiva] = useState(null);
  const [respondiendoCotizacion, setRespondiendoCotizacion] = useState(false);
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
  const vehiculosCuenta = useMemo(() => data?.vehiculos || [], [data]);

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
  const diagnosticosVehiculo = useMemo(() => (data?.diagnosticos_orden || []).filter((item) => ordenIdsVehiculo.has(item.orden_id)), [data, ordenIdsVehiculo]);
  const serviciosVehiculo = useMemo(() => (data?.servicios_orden || []).filter((item) => ordenIdsVehiculo.has(item.orden_id)), [data, ordenIdsVehiculo]);
  const repuestosVehiculo = useMemo(() => (data?.repuestos_orden || []).filter((item) => ordenIdsVehiculo.has(item.orden_id)), [data, ordenIdsVehiculo]);
  const facturasVehiculo = useMemo(() => (data?.facturas || []).filter((factura) => ordenIdsVehiculo.has(factura.orden_id)), [data, ordenIdsVehiculo]);
  const cotizacionesVehiculo = useMemo(() => (data?.cotizaciones || []).filter((cotizacion) => ordenIdsVehiculo.has(cotizacion.orden_id)), [data, ordenIdsVehiculo]);
  const historialVehiculo = useMemo(() => {
    if (!vehiculoIdActual) return data?.historial || [];
    return (data?.historial || []).filter((evento) => String(evento.vehiculo_id) === String(vehiculoIdActual));
  }, [data, vehiculoIdActual]);

  const citaProxima = useMemo(() => {
    const activas = citasVehiculo.filter((cita) => !['cancelada', 'cancelado', 'completada'].includes(String(cita.estado || '').toLowerCase()));
    return [...activas].sort((a, b) => `${a.fecha || ''} ${a.hora || ''}`.localeCompare(`${b.fecha || ''} ${b.hora || ''}`))[0];
  }, [citasVehiculo]);

  const cotizacionPendiente = useMemo(
    () => cotizacionesVehiculo.find((cotizacion) => String(cotizacion.estado || '').toLowerCase() === 'pendiente'),
    [cotizacionesVehiculo],
  );

  const ordenesActivas = useMemo(() => {
    return ordenesVehiculo.filter((orden) => {
      const estado = String(orden.estado || '').toLowerCase();
      return !['entregada', 'cancelada'].includes(estado);
    });
  }, [ordenesVehiculo]);

  const diagnosticosPorOrden = (ordenId) => diagnosticosVehiculo.filter((item) => item.orden_id === ordenId);
  const serviciosPorOrden = (ordenId) => serviciosVehiculo.filter((item) => item.orden_id === ordenId);
  const repuestosPorOrden = (ordenId) => repuestosVehiculo.filter((item) => item.orden_id === ordenId);
  const facturaPorOrden = (ordenId) => facturasVehiculo.find((item) => item.orden_id === ordenId);
  const pagosPorFactura = (facturaId) => (data?.pagos_facturas || []).filter((item) => item.factura_id === facturaId);
  const itemsPorCotizacion = (cotizacionId) => (data?.cotizacion_detalles || []).filter((item) => item.cotizacion_id === cotizacionId);

  const abrirCotizacion = (cotizacion) => setCotizacionActiva({
    ...cotizacion,
    items: itemsPorCotizacion(cotizacion.idcotizacion),
  });

  const responderCotizacion = async (respuesta) => {
    if (!cotizacionActiva || respondiendoCotizacion) return;
    const mensaje = respuesta === 'aceptada'
      ? '¿Deseas aceptar la cotizacion y autorizar la reparacion?'
      : '¿Deseas rechazar esta cotizacion? La reparacion no continuara.';
    if (!window.confirm(mensaje)) return;
    setRespondiendoCotizacion(true);
    try {
      await MiCuentaService.responderCotizacion(cotizacionActiva.idcotizacion, respuesta);
      setData((actual) => ({
        ...actual,
        cotizaciones: (actual?.cotizaciones || []).map((item) => item.idcotizacion === cotizacionActiva.idcotizacion ? { ...item, estado: respuesta === 'aceptada' ? 'aprobada' : 'rechazada', respuesta_cliente: respuesta } : item),
        ordenes: (actual?.ordenes || []).map((orden) => orden.idorden === cotizacionActiva.orden_id ? {
          ...orden,
          estado: respuesta === 'aceptada' ? 'aprobada' : 'cancelada',
          estado_label: respuesta === 'aceptada' ? 'Cotizacion aprobada' : 'Cotizacion rechazada',
        } : orden),
      }));
      setCotizacionActiva(null);
    } catch (err) {
      setError(err.message || 'No se pudo registrar la respuesta a la cotizacion.');
    } finally {
      setRespondiendoCotizacion(false);
    }
  };

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
      diagnosticos: diagnosticosPorOrden(orden.idorden),
      servicios: serviciosPorOrden(orden.idorden),
      repuestos: repuestosPorOrden(orden.idorden),
      factura: facturaPorOrden(orden.idorden),
    });
  };

  const verHistorial = (evento) => {
    const orden = ordenesVehiculo.find((item) => item.idorden === evento.orden_id);
    const diagnosticos = diagnosticosPorOrden(evento.orden_id);
    const servicios = serviciosPorOrden(evento.orden_id);
    const repuestos = repuestosPorOrden(evento.orden_id);
    const factura = facturasVehiculo.find((item) => item.idfactura === evento.factura_id || item.orden_id === evento.orden_id);
    setHistorialActivo({ evento, orden, diagnosticos, servicios, repuestos, factura, eventos: historialVehiculo });
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

      <section className="user-priority-grid">
        <article className="user-priority-card user-vehicle-focus">
          <div className="user-priority-head"><span><i className="bi bi-car-front-fill" /> Mi vehiculo</span><button type="button" onClick={onAddVehicle}><i className="bi bi-plus-lg" /> Agregar</button></div>
          {vehiculosCuenta.length ? <>
            <select aria-label="Elegir vehiculo" value={vehiculoSeleccionadoId} onChange={(event) => setVehiculoSeleccionadoId(event.target.value)}>
              {vehiculosCuenta.map((vehiculo) => <option key={vehiculo.idvehiculo} value={vehiculo.idvehiculo}>{clean(vehiculo.placa, 'Sin placa')} · {clean(vehiculo.marca, '')} {clean(vehiculo.modelo, '')}</option>)}
            </select>
            {vehiculoSeleccionado && <div className="user-vehicle-feature">
              <div className="user-vehicle-icon"><i className="bi bi-car-front-fill" /></div>
              <div><strong>{clean(vehiculoSeleccionado.marca)} {clean(vehiculoSeleccionado.modelo, '')}</strong><span className="user-vehicle-plate">{clean(vehiculoSeleccionado.placa)}</span><small>{clean(vehiculoSeleccionado.tipo_vehiculo)} · {clean(vehiculoSeleccionado.kilometraje_actual, 0)} km</small></div>
            </div>}
          </> : <EmptyState icon="bi-car-front" text="Aun no tienes vehiculos registrados." />}
        </article>

        <article className="user-priority-card user-appointment-focus">
          <div className="user-priority-head"><span><i className="bi bi-calendar2-check-fill" /> Proxima cita</span><button type="button" onClick={onScheduleAppointment}><i className="bi bi-calendar-plus" /> Agendar</button></div>
          {citaProxima ? <div className="user-appointment-feature"><time>{clean(citaProxima.fecha, 'Fecha pendiente')}<b>{clean(citaProxima.hora, 'Hora por confirmar')}</b></time><div><strong>{clean(citaProxima.motivo, 'Servicio agendado')}</strong><span>{clean(citaProxima.vehiculo, 'Tu vehiculo')}</span><small className={`user-status ${estadoClase(citaProxima.estado)}`}>{clean(citaProxima.estado, 'pendiente')}</small></div></div> : <EmptyState icon="bi-calendar-x" text="No tienes citas activas." />}
        </article>

        <article className="user-priority-card user-quote-focus">
          <div className="user-priority-head"><span><i className="bi bi-file-earmark-text-fill" /> Cotizacion</span><i className="bi bi-shield-check" /></div>
          {cotizacionPendiente ? <div className="user-quote-feature"><strong>{cotizacionPendiente.codigo_cotizacion}</strong><span>Tu taller espera tu respuesta</span><b>{money(cotizacionPendiente.total)}</b><button type="button" onClick={() => abrirCotizacion(cotizacionPendiente)}>Revisar cotizacion <i className="bi bi-arrow-right" /></button></div> : <EmptyState icon="bi-file-earmark-check" text={cotizacionesVehiculo.length ? 'No tienes cotizaciones pendientes.' : 'No tienes cotizaciones enviadas.'} />}
        </article>
      </section>

      <section className="user-account-card wide user-quotes-priority">
        <div className="user-account-card-head"><h3><i className="bi bi-file-earmark-text" /> Mis cotizaciones</h3></div>
        {cotizacionesVehiculo.length ? <div className="user-account-list">{cotizacionesVehiculo.map((cotizacion) => <div className="user-account-item user-action-item" key={cotizacion.idcotizacion}><strong>{cotizacion.codigo_cotizacion}</strong><span>{money(cotizacion.total)} | Orden {cotizacion.codigo_orden || `#${cotizacion.orden_id}`}</span><small className={`user-status ${estadoClase(cotizacion.estado)}`}>{clean(cotizacion.estado)}</small><button type="button" onClick={() => abrirCotizacion(cotizacion)}>Ver cotizacion</button></div>)}</div> : <EmptyState icon="bi-file-earmark" text="No tienes cotizaciones enviadas." />}
      </section>

      <section className="user-account-grid">
        <Section title="Servicios realizados" icon="bi-tools">
          {serviciosVehiculo.length ? (
            <div className="user-account-list">
              {serviciosVehiculo.slice(0, 8).map((item) => (
                <div className="user-account-item user-service-item" key={item.iddetalle_servicio}>
                  <strong>{clean(item.descripcion || item.descripcionservicio, 'Servicio tecnico')}</strong>
                  <span>Cantidad {clean(item.cantidad, 1)} | {money(item.subtotal)}</span>
                  <small>Orden #{item.orden_id}</small>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="bi-tools" text="Todavia no hay servicios realizados en tus ordenes." />}
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

        {ordenesActivas.length > 0 && (
          <section className="user-account-card wide user-current-work">
            <div className="user-account-card-head"><h3><i className="bi bi-activity" /> Estado actual del taller</h3></div>
            <div className="user-current-work-grid">
              {ordenesActivas.slice(0, 3).map((orden) => (
                <article key={orden.idorden}>
                  <strong>{orden.codigo_orden}</strong>
                  <span>{clean(orden.marca, '')} {clean(orden.modelo, '')} - {clean(orden.placa, 'Sin placa')}</span>
                  <div className="user-progress" aria-label={`Progreso ${orden.progreso || 0}%`}><span style={{ width: `${orden.progreso || 0}%` }} /></div>
                  <small>{orden.progreso || 0}% completado | {clean(orden.estado_label, orden.estado)}</small>
                  <OrderSteps estado={orden.estado} />
                  <button type="button" onClick={() => abrirOrden(orden)}>Ver detalle</button>
                </article>
              ))}
            </div>
          </section>
        )}

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
              {historialVehiculo.slice(0, 1).map((evento) => (
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

      <DetailModal title={cotizacionActiva ? 'Cotizacion realizada' : ''} onClose={() => setCotizacionActiva(null)}>
        {cotizacionActiva && (
          <div className="user-detail-content">
            <div className="user-detail-grid">
              <article><span>Cotizacion</span><strong>{cotizacionActiva.codigo_cotizacion}</strong></article>
              <article><span>Estado</span><strong>{clean(cotizacionActiva.estado)}</strong></article>
              <article><span>Orden</span><strong>{clean(cotizacionActiva.codigo_orden, `#${cotizacionActiva.orden_id}`)}</strong></article>
              <article><span>Total</span><strong>{money(cotizacionActiva.total)}</strong></article>
            </div>
            <h3>Diagnostico y trabajos propuestos</h3>
            {cotizacionActiva.items.length ? cotizacionActiva.items.map((item) => (
              <div className="user-detail-line" key={item.iddetalle_cotizacion}>
                <span>{clean(item.descripcion)} x {clean(item.cantidad, 1)}</span><strong>{money(item.subtotal)}</strong>
              </div>
            )) : <p className="user-muted">No hay items registrados.</p>}
            {cotizacionActiva.estado === 'pendiente' && (
              <div className="user-quote-actions">
                <button type="button" className="outline" onClick={() => setCotizacionActiva(null)}>Pendiente</button>
                <button type="button" className="danger" disabled={respondiendoCotizacion} onClick={() => responderCotizacion('rechazada')}>No continuar</button>
                <button type="button" disabled={respondiendoCotizacion} onClick={() => responderCotizacion('aceptada')}>Aceptar y continuar</button>
              </div>
            )}
          </div>
        )}
      </DetailModal>

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
            <h3>Diagnosticos registrados</h3>
            {ordenActiva.diagnosticos.length ? ordenActiva.diagnosticos.map((item) => (
              <div className="user-detail-note" key={item.iddiagnostico}>
                <strong>{clean(item.diagnostico_tecnico, 'Diagnostico tecnico')}</strong>
                <span>{clean(item.recomendacion, 'Sin recomendacion registrada.')}</span>
              </div>
            )) : <p className="user-muted">No hay diagnosticos registrados para esta orden.</p>}

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
            <h3>Diagnosticos registrados</h3>
            {historialActivo.diagnosticos.length ? historialActivo.diagnosticos.map((item) => (
              <div className="user-detail-note" key={item.iddiagnostico}>
                <strong>{clean(item.diagnostico_tecnico, 'Diagnostico tecnico')}</strong>
                <span>{clean(item.recomendacion, 'Sin recomendacion registrada.')}</span>
              </div>
            )) : <p className="user-muted">No hay diagnosticos registrados para esta orden.</p>}

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
            <h3>Todos los movimientos de este vehiculo</h3>
            <div className="user-history-modal-list">
              {(historialActivo.eventos || []).map((item) => (
                <div className="user-history-modal-item" key={item.idhistorial}>
                  <strong>{clean(item.tipo_evento)}</strong>
                  <span>{clean(item.fecha_evento, '')}</span>
                  <p>{clean(item.descripcion, '')}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </DetailModal>
    </main>
  );
}
