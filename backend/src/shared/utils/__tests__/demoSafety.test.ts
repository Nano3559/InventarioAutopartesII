import { test } from "node:test";
import assert from "node:assert/strict";
import { assertDemoDatabase } from "../demoSafety";
test("demo rechaza remotos, producción, base operativa y falta de autorización", () => {
  for (const url of [undefined, "postgresql://user@remote.example/app_demo", "postgresql://postgres@localhost/operativa", "invalid"]) assert.throws(() => assertDemoDatabase(url, { ALLOW_DEMO_DATA: "1" }));
  assert.throws(() => assertDemoDatabase("postgresql://postgres@localhost/app_demo", {}));
  assert.throws(() => assertDemoDatabase("postgresql://postgres@localhost/app_demo", { ALLOW_DEMO_DATA: "1", NODE_ENV: "production" }));
});
test("demo permite únicamente base local dedicada con opt-in", () => {
  assert.doesNotThrow(() => assertDemoDatabase("postgresql://postgres@127.0.0.1:55439/repuestopro_demo", { ALLOW_DEMO_DATA: "1", NODE_ENV: "development" }));
});
