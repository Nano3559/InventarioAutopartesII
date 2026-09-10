import { Request, Response, NextFunction } from "express";
import { logger } from "../utils/logger";

export const errorHandler = (err: any, req: Request, res: Response, _next: NextFunction) => {
  const status = statusFor(err);
  logger.error("Error no capturado", {
    method: req.method,
    path: req.originalUrl,
    status,
    message: err?.message,
    stack: err?.stack,
    code: err?.code,
  });

  if (err.code === "LIMIT_FILE_SIZE") {
    return res.status(400).json({ message: "El archivo excede el tamaño máximo permitido" });
  }

  if (err.code === "LIMIT_UNEXPECTED_FILE") {
    return res.status(400).json({ message: "Se recibió un archivo o campo inesperado en la petición" });
  }

  if (err.code === "INVALID_FILE_TYPE" || (err.message && err.message.includes("file type"))) {
    return res.status(400).json({ message: "Tipo de archivo no permitido" });
  }

  if (err.name === "SyntaxError" && "body" in err) {
    return res.status(400).json({ message: "JSON inválido en el cuerpo de la petición" });
  }

  if (err.name === "JsonWebTokenError") {
    return res.status(401).json({ message: "Token de autenticación inválido" });
  }

  if (err.name === "TokenExpiredError") {
    return res.status(401).json({ message: "Token de autenticación expirado" });
  }

  if (err.code === "P2025") {
    return res.status(404).json({ message: "Registro no encontrado" });
  }

  if (err.code === "P2002") {
    const field = err.meta?.target?.[0] || "campo";
    return res.status(400).json({ message: `Ya existe un registro con ese ${field}` });
  }

  if (err.code === "P2003") {
    return res.status(400).json({ message: "Referencia a un registro que no existe" });
  }

  if (err.code === "P2014") {
    return res.status(400).json({ message: "No se puede eliminar: tiene registros dependientes" });
  }

  res.status(500).json({ message: "Error interno del servidor" });
};

function statusFor(err: any): number {
  if (err?.code === "LIMIT_FILE_SIZE" || err?.code === "LIMIT_UNEXPECTED_FILE") return 400;
  if (err?.code === "INVALID_FILE_TYPE") return 400;
  if (err?.name === "SyntaxError" && "body" in err) return 400;
  if (err?.name === "JsonWebTokenError" || err?.name === "TokenExpiredError") return 401;
  if (err?.code === "P2025") return 404;
  if (err?.code === "P2002" || err?.code === "P2003" || err?.code === "P2014") return 400;
  return 500;
}
