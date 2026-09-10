export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(value: unknown): boolean {
  return typeof value === "string" && value.length <= 200 && value.length > 0 && EMAIL_REGEX.test(value);
}