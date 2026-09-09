import { rateLimit, RateLimitRequestHandler } from "express-rate-limit";

const standardHeaders = true;
const legacyHeaders = false;

const blocklistJson = (message: string) => ({
  status: 429,
  message,
});

// Requisitos (windowMs) en milisegundos: 15 minutos.
const WINDOW_MS = 15 * 60 * 1000;

// Limiter general de API: 300 requests / 15 minutos / IP.
export const generalLimiter: RateLimitRequestHandler = rateLimit({
  windowMs: WINDOW_MS,
  limit: 300,
  standardHeaders,
  legacyHeaders,
  message: blocklistJson("Demasiadas solicitudes. Intente nuevamente en unos minutos."),
});

// Limiter exclusivo de inicio de sesión: 10 intentos / 15 minutos / IP.
export const loginLimiter: RateLimitRequestHandler = rateLimit({
  windowMs: WINDOW_MS,
  limit: 10,
  standardHeaders,
  legacyHeaders,
  message: blocklistJson("Demasiados intentos de inicio de sesión. Intente nuevamente en unos minutos."),
});

// OCR público: 5 búsquedas / 15 minutos / IP. Costoso en CPU, límite conservador.
export const ocrPublicLimiter: RateLimitRequestHandler = rateLimit({
  windowMs: WINDOW_MS,
  limit: 5,
  standardHeaders,
  legacyHeaders,
  message: blocklistJson("Demasiadas búsquedas por imagen. Intente nuevamente en unos minutos."),
});

// OCR autenticado: 20 búsquedas / 15 minutos / usuario (identifica con req.user.userId,
// que se asigna tras authenticate; sin token se resuelve a "anonymous").
export const ocrAuthenticatedLimiter: RateLimitRequestHandler = rateLimit({
  windowMs: WINDOW_MS,
  limit: 20,
  standardHeaders,
  legacyHeaders,
  keyGenerator: (req) => {
    const userId = (req as any).user?.userId;
    return userId != null ? String(userId) : "anonymous";
  },
  message: blocklistJson("Demasiadas búsquedas por imagen. Intente nuevamente en unos minutos."),
});