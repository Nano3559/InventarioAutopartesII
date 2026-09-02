import dotenv from "dotenv";
dotenv.config();

const jwtSecret = process.env.JWT_SECRET;

if (!jwtSecret || jwtSecret === "secret-key") {
  if (process.env.NODE_ENV === "production") {
    throw new Error("JWT_SECRET no configurado correctamente. Defina un secreto propio en producción.");
  }
  console.warn("[config] ¡ADVERTENCIA! JWT_SECRET no definido; usando secreto por defecto (solo desarrollo).");
}

export const config = {
  port: parseInt(process.env.PORT || "3000"),
  jwtSecret: jwtSecret || "secret-key",
  databaseUrl: process.env.DATABASE_URL,
  frontendUrl: process.env.FRONTEND_URL || "http://localhost:5173",
  mobileUrl: process.env.MOBILE_URL || "http://localhost:19006",
};
