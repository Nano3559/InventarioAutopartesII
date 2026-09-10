import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import express, { Express } from "express";
import type { Server } from "node:http";
import { imageUpload } from "../searchImage.service";
import { errorHandler } from "../../../shared/middlewares/errorHandler";

/**
 * Tests unitarios del middleware de subida real usado por el endpoint de
 * búsqueda por imagen (público e interno). No requiere base de datos ni OCR.
 */

function buildApp(): Express {
  const app = express();
  app.post("/upload", imageUpload.single("image"), (req, res) => {
    res.json({
      present: Boolean(req.file),
      name: req.file?.originalname ?? null,
      size: req.file?.size ?? 0,
      mimetype: req.file?.mimetype ?? null,
    });
  });
  app.use(errorHandler);
  return app;
}

let server: Server;
let baseUrl: string;

before(async () => {
  server = await new Promise((resolve, reject) => {
    const srv = buildApp().listen(0, "127.0.0.1", () => resolve(srv));
    srv.on("error", reject);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("No se pudo obtener puerto");
  baseUrl = `http://127.0.0.1:${address.port}`;
});

after(async () => {
  await new Promise<void>((resolve) => {
    if (typeof (server as any).closeAllConnections === "function") {
      server.closeAllConnections();
    }
    server.close(() => resolve());
  });
});

function blobOf(bytes: number, mime: string): Blob {
  return new Blob([Buffer.alloc(bytes)], { type: mime });
}

async function postUpload(field: string, file: Blob | null): Promise<Response> {
  const fd = new FormData();
  if (file) fd.append(field, file, "test.png");
  return fetch(`${baseUrl}/upload`, { method: "POST", body: fd });
}

test("J3: acepta JPEG, PNG y WebP (MIME permitidos por imageUpload)", async () => {
  for (const mime of ["image/jpeg", "image/png", "image/webp"]) {
    const res = await postUpload("image", blobOf(1024, mime));
    assert.equal(res.status, 200, `${mime} debería aceptarse`);
    const body: any = await res.json();
    assert.equal(body.present, true);
    assert.equal(body.mimetype, mime);
    assert.ok(body.size > 0);
  }
});

test("J3: rechaza un MIME no permitido (text/plain) con 400 y mensaje claro", async () => {
  const res = await postUpload("image", blobOf(128, "text/plain"));
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.message, "Tipo de archivo no permitido");
});

test("J3: rechaza un archivo de más de 5 MB (límite de imageUpload)", async () => {
  const res = await postUpload("image", blobOf(5 * 1024 * 1024 + 1, "image/jpeg"));
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.message, "El archivo excede el tamaño máximo permitido");
});

test("J3: rechaza un campo multipart distinto a image", async () => {
  const res = await postUpload("otroCampo", blobOf(1024, "image/png"));
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.message, "Se recibió un archivo o campo inesperado en la petición");
});

test("J3: sin archivo, multer no crea req.file (flujo llega al handler)", async () => {
  const res = await postUpload("image", null);
  assert.equal(res.status, 200);
  const body: any = await res.json();
  assert.equal(body.present, false);
});