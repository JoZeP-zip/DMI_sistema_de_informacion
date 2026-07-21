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

export default function MiCuenta({ onAddVehicle, onScheduleAppointment }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [historialActivo, setHistorialActivo] = useState(null);

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

  const ordenesActivas = useMemo(() => {
    return (data?.ordenes || []).filter((orden) => {
      const estado = String(orden.estado || '').toLowerCase();
      return !['entregada', 'cancelada'].includes(estado);
    });
  }, [data]);

  const abrirFactura = (factura) => {
    const servicios = (data?.servicios_orden || []).filter((item) => item.orden_id === factura.orden_id);
    const repuestos = (data?.repuestos_orden || []).filter((item) => item.orden_id === factura.orden_id);
    const orden = (data?.ordenes || []).find((item) => item.idorden === factura.orden_id);
    const pagos = (data?.pagos_facturas || []).filter((item) => item.factura_id === factura.idfactura);

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

  const verHistorial = (evento) => {
    const orden = (data?.ordenes || []).find((item) => item.idorden === evento.orden_id);
    const servicios = (data?.servicios_orden || []).filter((item) => item.orden_id === evento.orden_id);
    const repuestos = (data?.repuestos_orden || []).filter((item) => item.orden_id === evento.orden_id);
    const factura = (data?.facturas || []).find((item) => item.idfactura === evento.factura_id || item.orden_id === evento.orden_id);
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

      <section className="user-account-grid">
        <Section title="Vehiculos" icon="bi-car-front-fill">
          {(data?.vehiculos || []).length ? (
            <div className="user-account-list">
              {data.vehiculos.map((vehiculo) => (
                <div className="user-account-item" key={vehiculo.idvehiculo}>
                  <strong>{clean(vehiculo.marca)} {clean(vehiculo.modelo, '')}</strong>
                  <span>Placa {clean(vehiculo.placa)} | Tipo {clean(vehiculo.tipo_vehiculo)}</span>
                  <small>Motor {clean(vehiculo.motor)} | Capacidad {clean(vehiculo.capacidad, 0)} | Km {clean(vehiculo.kilometraje_actual, 0)}</small>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="bi-car-front" text="Aun no tienes vehiculos registrados." />}
        </Section>

        <Section title="Citas" icon="bi-calendar-check-fill">
          {(data?.citas || []).length ? (
            <div className="user-account-list">
              {data.citas.map((cita) => (
                <div className="user-account-item" key={cita.idcita}>
                  <strong>{clean(cita.motivo, 'Servicio agendado')}</strong>
                  <span>{clean(cita.fecha, '')} {clean(cita.hora, '')} | {clean(cita.vehiculo, 'Vehiculo')}</span>
                  <small className={`user-status ${estadoClase(cita.estado)}`}>{clean(cita.estado, 'pendiente')}</small>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="bi-calendar-x" text="No tienes citas registradas." />}
        </Section>

        <Section title="Estado del vehiculo" icon="bi-clipboard2-check-fill" className="wide">
          {ordenesActivas.length ? (
            <div className="user-order-list">
              {ordenesActivas.map((orden) => (
                <div className="user-order-card" key={orden.idorden}>
                  <div className="user-order-top">
                    <div>
                      <strong>{orden.codigo_orden}</strong>
                      <span>{clean(orden.marca, '')} {clean(orden.modelo, '')} - {clean(orden.placa, 'Sin placa')}</span>
                    </div>
                    <b>{clean(orden.estado_label, orden.estado)}</b>
                  </div>
                  <div className="user-progress" aria-label={`Progreso ${orden.progreso || 0}%`}>
                    <span style={{ width: `${orden.progreso || 0}%` }} />
                  </div>
                  <small>{orden.progreso || 0}% completado | {clean(orden.motivo_ingreso, 'Sin motivo registrado')}</small>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="bi-clipboard-x" text="No tienes ordenes de trabajo activas." />}
        </Section>

        <Section title="Repuestos usados" icon="bi-box-seam-fill">
          {(data?.repuestos_orden || []).length ? (
            <div className="user-account-list">
              {data.repuestos_orden.map((item) => (
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
          {(data?.facturas || []).length ? (
            <div className="user-account-list">
              {data.facturas.map((factura) => (
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
          {(data?.historial || []).length ? (
            <div className="user-history-list">
              {data.historial.map((evento) => (
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
          </div>
        )}
      </DetailModal>
    </main>
  );
}
