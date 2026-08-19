import { Request } from "express";

export interface AuthPayload {
  userId: number;
  email: string;
  role: string;
  locationId: number | null;
}

export interface AuthRequest extends Request {
  user?: AuthPayload;
}
