export const showDmiMessage = ({
  kicker = "Mensaje del sistema",
  title = "Aviso",
  message = "",
  confirmText = "Entendido",
  cancelText = null,
  details = null,
  productItems = null,
  onConfirm = null,
} = {}) => {
  if (typeof window === "undefined") return;

  window.dispatchEvent(new CustomEvent("dmi:message", {
    detail: {
      kicker,
      title,
      message,
      confirmText,
      cancelText,
      details,
      productItems,
      onConfirm,
    },
  }));
};

export const showDmiError = (title, message) => {
  showDmiMessage({
    kicker: "Atencion requerida",
    title,
    message,
    confirmText: "Entendido",
  });
};

export const showDmiSuccess = (title, message) => {
  showDmiMessage({
    kicker: "Proceso completado",
    title,
    message,
    confirmText: "Aceptar",
  });
};
