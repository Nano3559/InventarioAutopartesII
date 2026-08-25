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
  if (!Number.isInteger(id) || id < 1) throw new Error("ID inválido");
  return id;
};

export const parsePositiveInt = (value: any, fieldName: string): number => {
  const num = Number(value);
  if (!Number.isInteger(num) || num < 1) throw new Error(`${fieldName} debe ser un número entero positivo`);
  return num;
};

export const parsePositiveDecimal = (value: any, fieldName: string): number => {
  const num = Number(value);
  if (isNaN(num) || num < 0) throw new Error(`${fieldName} debe ser un número positivo`);
  return num;
};

export const parseString = (value: any, fieldName: string, opts?: { required?: boolean; max?: number }): string | null => {
  if (value === undefined || value === null || value === "") {
    if (opts?.required) throw new Error(`${fieldName} es obligatorio`);
    return null;
  }
  if (typeof value !== "string") throw new Error(`${fieldName} debe ser texto`);
  const trimmed = value.trim();
  if (opts?.required && trimmed.length === 0) throw new Error(`${fieldName} es obligatorio`);
  if (opts?.max && trimmed.length > opts.max) throw new Error(`${fieldName} no puede exceder ${opts.max} caracteres`);
  return trimmed;
};
