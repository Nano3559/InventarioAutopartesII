import { Router, Request, Response } from "express";
import { body } from "express-validator";
import { authenticate, authorize } from "../../shared/middlewares/auth";
import { validate } from "../../shared/middlewares/validate";
import { demandQuery } from "./predictions.service";
import { scenarioQuery, createScenarioPreview, assertUniqueJsonKeys } from "./scenarios.service";

export function createPredictionsRouter(session = authenticate, query = demandQuery, scenarios = scenarioQuery, preview = createScenarioPreview(scenarios)) {
const router = Router();
router.use(session, authorize("ADMIN"));
function scenarioFailure(res: Response, error: unknown) {
  const code = error instanceof Error ? error.message : "MODEL_UNAVAILABLE";
  const status = ["SNAPSHOT_MISMATCH", "IDEMPOTENCY_CONFLICT"].includes(code) ? 409 : code === "SCENARIO_BUSY" ? 429 : ["INVALID_INPUT", "INVALID_HISTORY_WINDOW", "INCOHERENT_PRICES", "INVALID_QUOTE_TIME", "INVALID_QUANTITY", "INVALID_RESERVATION", "INVALID_ORDER_PLAN", "INVALID_SHIPMENT_PLAN"].includes(code) ? 400 : 503;
  return res.status(status).json({ code: status === 503 ? "MODEL_UNAVAILABLE" : code, message: status === 400 ? "Revisa cantidades, precios y fechas del escenario." : status === 409 ? "La referencia o el identificador de petición ya no coincide. Actualiza la consulta." : status === 429 ? "Hay varias comparaciones en curso. Intenta nuevamente." : "No se pudo cargar el modelo de escenarios. Intenta nuevamente." });
}
router.get("/scenarios/capabilities", async (_req, res) => {
  try { res.json(await scenarios("capabilities")); } catch (e) { scenarioFailure(res, e); }
});
router.get("/scenarios/snapshots/:id", async (req, res) => {
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(String(req.params.id))) return res.status(400).json({ code: "INVALID_INPUT" });
  try { res.json(await scenarios("snapshot", { baseSnapshotId: req.params.id })); } catch (e) { scenarioFailure(res, e); }
});
router.post("/scenarios/preview", [body().custom(value => value && typeof value === "object" && !Array.isArray(value) && !Object.prototype.hasOwnProperty.call(value, "action")).withMessage("Escenario inválido")], validate, async (req: Request, res: Response) => {
  try {
    if (typeof (req as any).scenarioRawJson === "string") assertUniqueJsonKeys((req as any).scenarioRawJson);
    res.json(await preview((req as any).user.userId, req.body));
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
