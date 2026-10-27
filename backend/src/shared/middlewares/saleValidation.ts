import { body } from "express-validator";
import { validate } from "./validate";
import { MAX_QUANTITY, MAX_MONEY } from "../utils/pricing";

/** Validación compartida de las dos entradas de venta. El servidor calcula importes. */
export const saleValidation = [
  body("items").isArray({ min: 1, max: 1000 }).withMessage("Debe enviar entre 1 y 1000 ítems"),
  body("items.*.productId").isInt({ min: 1, max: MAX_QUANTITY }).withMessage("Producto inválido"),
  body("items.*.quantity").isInt({ min: 1, max: MAX_QUANTITY }).withMessage("Cantidad inválida"),
  body("items.*.priceMode").optional().isIn(["POR_MENOR", "POR_MAYOR"]).withMessage("Seleccione POR MENOR o POR MAYOR"),
  body("items.*.priceTier").optional().isIn(["PRICE1"]).withMessage("El segundo nivel es legacy. Seleccione POR MENOR o POR MAYOR"),
  body("payments").isArray({ min: 1, max: 100 }).withMessage("Debe registrar al menos un pago"),
  body("payments.*.method").isIn(["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"]).withMessage((value) => `Método de pago inválido: ${String(value).slice(0, 120)}`),
  body("payments.*.amount").isFloat({ min: 0, max: MAX_MONEY }).withMessage("Monto de pago inválido"),
  body("locationId").optional().isInt({ min: 1, max: MAX_QUANTITY }).withMessage("Ubicación inválida"),
  body("customerId").optional({ nullable: true }).isInt({ min: 1, max: MAX_QUANTITY }).withMessage("Cliente inválido"),
  ...["seller", "paraQuien", "lugarEntrega", "datosFactura", "formaPago", "clienteName", "customerData.name", "customerData.nit", "customerData.phone"].map((field) => body(field).optional({ nullable: true }).isString().withMessage(`Campo ${field} debe ser texto`).bail().isLength({ max: field === "lugarEntrega" || field === "datosFactura" ? 200 : field === "formaPago" ? 20 : 120 }).withMessage(`Campo ${field} no puede superar ${field === "lugarEntrega" || field === "datosFactura" ? 200 : field === "formaPago" ? 20 : 120} caracteres`)),
  body("formaPago").optional({ nullable: true, checkFalsy: true }).isIn(["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"]).withMessage((value) => `Método de pago inválido: ${String(value).slice(0, 120)}`),
  validate,
];
