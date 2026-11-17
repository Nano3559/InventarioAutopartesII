import { Router, Request, Response, NextFunction } from "express";
import { body, validationResult } from "express-validator";
import { authenticate, authorize } from "../../shared/middlewares/auth";
import { validate } from "../../shared/middlewares/validate";
import { demandQuery } from "./predictions.service";
import { scenarioQuery, createScenarioPreview, assertUniqueJsonKeys, SCENARIO_CONTRACT,
  SCENARIO_DELIVERY_HEADER, SCENARIO_RUNTIME_REVISION_HEADER } from "./scenarios.service";

export function createPredictionsRouter(session = authenticate, query = demandQuery, scenarios = scenarioQuery, preview = createScenarioPreview(scenarios)) {
const router = Router();
// Reglas SC01-SC21 con enlace code->rule declarado en domain_rules del contrato.
// Solo se emiten issues con correspondencia comprobable; el resto queda vacío.
const SCENARIO_ISSUES: Record<string, { field: string; ruleId: string }> = {
  SNAPSHOT_MISMATCH: { field: "baseSnapshotId", ruleId: "SC01" },
  INVALID_HISTORY_WINDOW: { field: "changes.history", ruleId: "SC02" },
  INCOHERENT_PRICES: { field: "changes.prices", ruleId: "SC04" },
  INVALID_QUOTE_TIME: { field: "changes.quote", ruleId: "SC05" },
  INVALID_ORDER_PLAN: { field: "changes.orders", ruleId: "SC10" },
  INVALID_SHIPMENT_PLAN: { field: "changes.logistics", ruleId: "SC11" },
  IDEMPOTENCY_CONFLICT: { field: "clientRequestId", ruleId: "SC18" },
};
function scenarioError(res: Response, status: number, code: string, message: string) {
  const issue = SCENARIO_ISSUES[code];
  return res.status(status).json({ contractVersion: SCENARIO_CONTRACT, code, message, issues: issue ? [issue] : [] });
}
// Solo /scenarios adapta los errores de autenticación al contrato del módulo.
// /catalog, /demand y los demás módulos conservan su respuesta legada intacta.
router.use((req, res, next) => {
  if (!/^\/scenarios(?:\/|$)/i.test(req.path)) return next();
  const json = res.json.bind(res);
  res.json = (payload: unknown) => {
    if (![401, 403, 503].includes(res.statusCode)) return json(payload);
    // Preserve errors already classified by scenarioFailure (in particular
    // INCOMPATIBLE_ARTIFACT); only early authentication errors lack an envelope.
    if (payload && typeof payload === "object" && "contractVersion" in payload && payload.contractVersion === SCENARIO_CONTRACT) return json(payload);
    const message = payload && typeof payload === "object" && typeof (payload as { message?: unknown }).message === "string"
      ? (payload as { message: string }).message
      : res.statusCode === 401 ? "No autenticado" : res.statusCode === 403 ? "No tiene permisos para esta acción" : "No se pudo verificar la sesión. Intente nuevamente";
    const code = res.statusCode === 401 ? "SESSION_INVALID" : res.statusCode === 403 ? "ADMIN_REQUIRED" : "MODEL_UNAVAILABLE";
    return json({ contractVersion: SCENARIO_CONTRACT, code, message, issues: [] });
  };
  next();
});
router.use(session, authorize("ADMIN"));
function scenarioFailure(res: Response, error: unknown) {
  const raw = error instanceof Error ? error.message : "";
  const status = ["SNAPSHOT_MISMATCH", "IDEMPOTENCY_CONFLICT"].includes(raw) ? 409 : raw === "SCENARIO_BUSY" ? 429 : ["INVALID_INPUT", "INVALID_HISTORY_WINDOW", "INCOHERENT_PRICES", "INVALID_QUOTE_TIME", "INVALID_QUANTITY", "INVALID_RESERVATION", "INVALID_ORDER_PLAN", "INVALID_SHIPMENT_PLAN"].includes(raw) ? 400 : 503;
  // OBS-4: el 503 solo puede ser MODEL_UNAVAILABLE o INCOMPATIBLE_ARTIFACT; cualquier
  // otro código o mensaje interno queda sanitizado en MODEL_UNAVAILABLE.
  const code = status === 503 ? (["MODEL_UNAVAILABLE", "INCOMPATIBLE_ARTIFACT"].includes(raw) ? raw : "MODEL_UNAVAILABLE") : raw;
  const message = status === 400 ? "Revisa cantidades, precios y fechas del escenario." : status === 409 ? "La referencia o el identificador de petición ya no coincide. Actualiza la consulta." : status === 429 ? "Hay varias comparaciones en curso. Intenta nuevamente." : "No se pudo cargar el modelo de escenarios. Intenta nuevamente.";
  return scenarioError(res, status, code, message);
}
function scenarioValidate(req: Request, res: Response, next: NextFunction) {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    const messages = errors.array().map(e => e.msg);
    return scenarioError(res, 400, "INVALID_INPUT", messages.length === 1 ? messages[0] : messages.join(". "));
  }
  next();
}
router.get("/scenarios/capabilities", async (_req, res) => {
  try { res.json(await scenarios("capabilities")); } catch (e) { scenarioFailure(res, e); }
});
router.get("/scenarios/snapshots/:id", async (req, res) => {
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(String(req.params.id))) return scenarioError(res, 400, "INVALID_INPUT", "Revisa cantidades, precios y fechas del escenario.");
  try { res.json(await scenarios("snapshot", { baseSnapshotId: req.params.id })); } catch (e) { scenarioFailure(res, e); }
});
router.post("/scenarios/preview", [body().custom(value => value && typeof value === "object" && !Array.isArray(value) && !Object.prototype.hasOwnProperty.call(value, "action")).withMessage("Escenario inválido")], scenarioValidate, async (req: Request, res: Response) => {
  try {
    if (typeof (req as any).scenarioRawJson === "string") assertUniqueJsonKeys((req as any).scenarioRawJson);
    const response = await preview((req as any).user.userId, req.body, provenance => {
      res.set(SCENARIO_DELIVERY_HEADER, provenance.delivery);
      res.set(SCENARIO_RUNTIME_REVISION_HEADER, provenance.runtimeRevision ?? "unknown");
      res.append("Access-Control-Expose-Headers", [SCENARIO_DELIVERY_HEADER, SCENARIO_RUNTIME_REVISION_HEADER]);
    });
    res.json(response);
  } catch (e) { scenarioFailure(res, e); }
});
function failure(res: Response, error: unknown) {
  const code = error instanceof Error ? error.message : "DEMAND_UNAVAILABLE";
  if (["INVALID_INPUT", "UNKNOWN_ENTITY"].includes(code)) return res.status(400).json({ code, message: "Producto, tienda o solicitud fuera del catálogo aprobado." });
  if (code === "SNAPSHOT_MISMATCH") return res.status(409).json({ code, message: "El snapshot no corresponde al producto, tienda y mes seleccionados. Actualice la consulta." });
  if (code === "UNAVAILABLE_REQUIRED_FEATURE") return res.status(422).json({ code, message: "No existe un snapshot aprobado para ese mes. La reproducción V2 comprende abril a junio de 2026." });
  return res.status(503).json({ code: "DEMAND_UNAVAILABLE", message: "Referencia V2 no disponible. Revise el entorno y la integridad del artefacto fijado." });
}
router.get("/catalog", async (_req, res) => {
  try { res.json(await query({ action: "catalog" })); }
  catch (error) { failure(res, error); }
});
const validId = (value: unknown) => typeof value === "number" && Number.isInteger(value) && value > 0 && value <= 2147483647;
router.post("/demand", [
  body().custom(value => value && typeof value === "object" && !Array.isArray(value) &&
    Object.keys(value).every(k => ["productId", "locationId", "targetMonth", "historySnapshotId"].includes(k)) &&
    !(Object.prototype.hasOwnProperty.call(value, "historySnapshotId") && !Object.prototype.hasOwnProperty.call(value, "targetMonth"))).withMessage("Solicitud predictiva inválida. No envíe variables o targets."),
  body("productId").custom(validId).withMessage("Seleccione un producto válido"),
  body("locationId").custom(validId).withMessage("Seleccione una tienda válida"),
  body("targetMonth").optional().custom(value => typeof value === "string" && /^[1-9][0-9]{3}-(0[1-9]|1[0-2])$/.test(value)).withMessage("Mes objetivo inválido"),
  body("historySnapshotId").optional().custom(value => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value)).withMessage("Snapshot inválido"),
], validate, async (req: Request, res: Response) => {
  try { res.json(await query(req.body)); }
  catch (error) { failure(res, error); }
});
return router;
}
export default createPredictionsRouter();
