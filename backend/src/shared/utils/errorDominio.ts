/**
 * Error de dominio: un rechazo esperado de la petición, no un fallo del sistema.
 *
 * El mensaje es seguro para mostrar al cliente porque lo escribió el propio código de
 * negocio, no una librería. Todo lo que NO se construya con esta clase se considera un
 * error interno y se responde 500 con un mensaje genérico, para no filtrar detalles de
 * Prisma, del sistema de archivos o de la estructura interna.
 *
 * Antes, `sales` y `wholesale` respondían 400 con `error.message` para CUALQUIER error,
 * así que un `TypeError` o un fallo de conexión respondía 400 y exponía el mensaje real.
 */
export class ErrorDominio extends Error {
  readonly esDeDominio = true;

  constructor(message: string) {
    super(message);
    this.name = "ErrorDominio";
  }
}

/** Construye un error de dominio sin repetir `new` en cada sitio. */
export function errorDominio(message: string): ErrorDominio {
  return new ErrorDominio(message);
}

/**
 * ¿Este error es un rechazo de negocio conocido y por tanto respondible con 400?
 *
 * Se usa `instanceof` y no la forma del mensaje: comprobar el texto sería frágil
 * (cualquier error interno cuyo mensaje contenga esas palabras se convertiría en un 400
 * con detalle filtrado) y rompería en cuanto se reescribiera un mensaje.
 */
export function esErrorDominio(error: unknown): error is ErrorDominio {
  return error instanceof ErrorDominio;
}
