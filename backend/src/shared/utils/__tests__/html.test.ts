import { test } from "node:test";
import assert from "node:assert/strict";
import { escapeHtml } from "../html";
test("texto libre de la nota no puede convertirse en etiquetas HTML", () => {
  assert.equal(escapeHtml('<script>alert("x")</script>&'), "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;&amp;");
});
