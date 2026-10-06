import { describe, it, expect } from "vitest";
import axios from "axios";

/**
 * Test de regresión del 400 "Debe subir una imagen".
 *
 * No basta con comprobar que se llamó a `api.post`: la regresión发生时
 * `visionApi` sí construía un FormData correcto, pero la instancia de axios
 * traía `Content-Type: application/json` por defecto. axios detecta ese
 * content-type y serializa el FormData a JSON (`{"image":{}}`), por lo que los
 * bytes del archivo se pierden y multer no encuentra `req.file`.
 *
 * Estos tests pasan un `adapter` que captura el `Content-Type` y el body
 * **finales** queaxios enviaría realmente, sin performing red.
 */
function jpegBytes(): ArrayBuffer {
  // SOI + EOI: un JPEG mínimo pero con bytes reales (> 0).
  return new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0xff, 0xd9]).buffer as ArrayBuffer;
}

interface Captura {
  url?: string;
  contentType?: unknown;
  body: unknown;
}

async function cuerpoRealQueAxiosEnvia(config: {
  baseURL?: string;
  headers?: Record<string, string>;
}): Promise<Captura> {
  const inst = axios.create(config);
  let captura: Captura = { body: undefined };
  inst.defaults.adapter = (cfg) => {
    captura = {
      url: cfg.url,
      contentType: cfg.headers.get("Content-Type"),
      body: cfg.data,
    };
    return Promise.resolve({
      status: 200,
      statusText: "OK",
      headers: {},
      config: cfg,
      data: {},
    });
  };

  const data = new FormData();
  const archivo = new File([jpegBytes()], "pieza.jpg", { type: "image/jpeg" });
  data.append("image", archivo);
  data.append("vehiculoMarca", "Toyota");

  await inst.post("/vision/public/detectar", data);
  return captura;
}

describe("multipart real hacia /api/vision/public/detectar", () => {
  it("NO serializa el FormData a JSON con la instancia de producción (sin Content-Type por defecto)", async () => {
    const cap = await cuerpoRealQueAxiosEnvia({ baseURL: "http://localhost:3000/api" });

    // El body debe seguir siendo FormData: si axios lo convirtiera a JSON, el
    // backend recibiría `{"image":{}}` y multer no vería req.file (400).
    expect(cap.body).toBeInstanceOf(FormData);

    const contenido = cap.contentType as string | undefined;
    expect(contenido === undefined || !contenido.includes("application/json")).toBe(true);
  });

  it("la instancia de producción (la que exporta services/api) no declara Content-Type json", async () => {
    // Se importa la instancia real del proyecto, no una recreada.
    const { default: apiReal } = await import("../api");
    const declarado = (apiReal.defaults.headers?.common?.["Content-Type"] ?? "") as string;
    expect(declarado).not.toContain("application/json");
  });

  it("regresión documentada: un default application/json SÍ destruye el archivo", async () => {
    // Fixture de control: fija el comportamiento de axios que causa el bug, para
    // que el test no pase por accidente si axios cambia su lógica.
    const cap = await cuerpoRealQueAxiosEnvia({
      baseURL: "http://localhost:3000/api",
      headers: { "Content-Type": "application/json" },
    });

    expect(cap.contentType).toContain("application/json");
    // Y el cuerpo deixa de serFormData: el archivo viaja como `{"image":{}}`.
    expect(cap.body).not.toBeInstanceOf(FormData);
    expect(typeof cap.body).toBe("string");
    expect(String(cap.body)).not.toContain("\xff\xd8");
  });

  it("el FormData real contiene la clave image con un File de bytes > 0 y MIME válido", async () => {
    const data = new FormData();
    const archivo = new File([jpegBytes()], "pieza.jpg", { type: "image/jpeg" });
    data.append("image", archivo);

    expect(data.has("image")).toBe(true);
    const valor = data.get("image");
    expect(valor).toBeInstanceOf(File);
    const file = valor as File;
    expect(file.size).toBeGreaterThan(0);
    expect(file.type).toBe("image/jpeg");
    expect(file.name).toBe("pieza.jpg");
  });

  it("no fija Content-Type manual en la configuración de la petición de visión", async () => {
    // Replica la llamada real de visionApi contra la instancia de producción,
    // sin mockear `api`, y comprueba el body final.
    const { default: api } = await import("../api");
    let capt: Captura = { body: undefined };
    const originalAdapter = api.defaults.adapter;
    api.defaults.adapter = (cfg: any) => {
      capt = { contentType: cfg.headers.get("Content-Type"), body: cfg.data, url: cfg.url };
      return Promise.resolve({ status: 200, statusText: "OK", headers: {}, config: cfg, data: {} });
    };

    const data = new FormData();
    data.append("image", new File([jpegBytes()], "captura.jpg", { type: "image/jpeg" }));

    await api.post("/vision/public/detectar", data, { timeout: 20000 });
    api.defaults.adapter = originalAdapter;

    expect(capt.body).toBeInstanceOf(FormData);
    expect((capt.body as FormData).get("image")).toBeInstanceOf(File);
    const ct = capt.contentType as string | undefined;
    expect(ct === undefined || !ct.includes("application/json")).toBe(true);
  });
});