import { errorDominio } from "../utils/errorDominio";
import { MAX_QUANTITY, MAX_MONEY } from "../utils/pricing";
import { Request, Response, NextFunction } from "express";
import { validationResult } from "express-validator";

export const validate = (req: Request, res: Response, next: NextFunction) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    const messages = errors.array().map((e) => e.msg);
    return res.status(400).json({ message: messages.length === 1 ? messages[0] : messages });
  }
  next();
};

export const parseId = (value: string) => {
  const id = Number(value);
  if (!Number.isInteger(id) || id < 1 || id > MAX_QUANTITY) throw errorDominio("ID inválido");
  return id;
};

export const parsePositiveInt = (value: any, fieldName: string): number => {
  const num = Number(value);
  if (typeof value === "boolean" || !Number.isInteger(num) || num < 1 || num > MAX_QUANTITY) throw errorDominio(`${fieldName} debe ser un número entero positivo`);
  return num;
};

export const parsePositiveDecimal = (value: any, fieldName: string): number => {
  const num = Number(value);
  if (typeof value === "boolean" || value === null || value === "" || !Number.isFinite(num) || num < 0 || num > MAX_MONEY) throw errorDominio(`${fieldName} debe ser un número positivo`);
  return num;
};

export const parseString = (value: any, fieldName: string, opts?: { required?: boolean; max?: number }): string | null => {
  if (value === undefined || value === null || value === "") {
    if (opts?.required) throw errorDominio(`${fieldName} es obligatorio`);
    return null;
  }
  if (typeof value !== "string") throw errorDominio(`${fieldName} debe ser texto`);
  const trimmed = value.trim();
  if (opts?.required && trimmed.length === 0) throw errorDominio(`${fieldName} es obligatorio`);
  if (opts?.max && trimmed.length > opts.max) throw errorDominio(`${fieldName} no puede exceder ${opts.max} caracteres`);
  return trimmed;
};
