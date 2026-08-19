import dotenv from "dotenv";
dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || "3000"),
  jwtSecret: process.env.JWT_SECRET || "secret-key",
  databaseUrl: process.env.DATABASE_URL,
  frontendUrl: process.env.FRONTEND_URL || "http://localhost:5173",
  mobileUrl: process.env.MOBILE_URL || "http://localhost:19006",
};
