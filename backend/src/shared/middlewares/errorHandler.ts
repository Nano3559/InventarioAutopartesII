import { Request, Response, NextFunction } from "express";

export const errorHandler = (err: any, _req: Request, res: Response, _next: NextFunction) => {
  console.error("Error no capturado:", err);

  if (err.code === "LIMIT_FILE_SIZE") {
    return res.status(400).json({ message: "El archivo excede el tamaño máximo permitido" });
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
