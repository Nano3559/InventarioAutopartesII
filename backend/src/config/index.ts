import dotenv from "dotenv";
dotenv.config();

const jwtSecret = process.env.JWT_SECRET;

const secretInseguro =
  !jwtSecret ||
  jwtSecret.trim() === "" ||
  jwtSecret === "secret-key" ||
  jwtSecret === "secret" ||
  jwtSecret.length < 16;

if (secretInseguro) {
  throw new Error(
    "JWT_SECRET no está configurado correctamente. Defina una variable de entorno JWT_SECRET segura (mínimo 16 caracteres) antes de iniciar la aplicación."
  );
}

export const config = {
  port: parseInt(process.env.PORT || "3000"),
  jwtSecret,
  databaseUrl: process.env.DATABASE_URL,
  frontendUrl: process.env.FRONTEND_URL || "http://localhost:5173",
  mobileUrl: process.env.MOBILE_URL || "http://localhost:19006",
};
