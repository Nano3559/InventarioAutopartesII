import { test } from "node:test";
import assert from "node:assert/strict";
import { ROLES_CON_COSTOS, ROLES_CON_VISTA_GLOBAL, SIN_ALCANCE, alcanceDeFiltro, puedeVerCostos, resolveLocationScope, tieneAlcanceGlobal } from "../scope";

/**
 * Estas reglas sustituyeron deny-lists (`!esTienda`, `role !== "TIENDA"`) por
 * allow-lists. El riesgo que cubren: el nombre del rol viene de RoleModel.name, una
 * tabla data-driven editable desde el panel, así que con un deny-list un rol creado
 * en el futuro (p. ej. "CAJERO") caía del lado permitido y recibía costos de compra y
 * existencias de toda la cadena.
 */

test("solo ADMIN e INVENTARIO tienen alcance global", () => {
  assert.equal(tieneAlcanceGlobal({ role: "ADMIN" }), true);
  assert.equal(tieneAlcanceGlobal({ role: "INVENTARIO" }), true);
});

test("un rol futuro o desconocido NO tiene alcance global", () => {
  for (const rol of ["CAJERO", "VENDEDOR", "REPORTERO", "ADMINISTRADOR", "admin", "Tienda", ""]) {
    assert.equal(tieneAlcanceGlobal({ role: rol }), false, `${rol} no debe tener vista global`);
  }
  assert.equal(tieneAlcanceGlobal(undefined), false);
  assert.equal(tieneAlcanceGlobal(null), false);
});

test("un rol desconocido NO ve costos financieros por defecto", () => {
  for (const rol of ["CAJERO", "VENDEDOR", "REPORTERO", "Tienda", ""]) {
    assert.equal(puedeVerCostos({ role: rol }), false, `${rol} no debe ver costos`);
  }
  assert.equal(puedeVerCostos(undefined), false);
  assert.equal(puedeVerCostos(null), false);
});

test("ADMIN e INVENTARIO sí ven costos", () => {
  assert.equal(puedeVerCostos({ role: "ADMIN" }), true);
  assert.equal(puedeVerCostos({ role: "INVENTARIO" }), true);
});

test("TIENDA nunca ve costos, tenga o no ubicación", () => {
  assert.equal(puedeVerCostos({ role: "TIENDA", locationId: 10 }), false);
  assert.equal(puedeVerCostos({ role: "TIENDA" }), false);
});

test("resolveLocationScope acota a la tienda y nunca amplía el alcance", () => {
  assert.equal(resolveLocationScope({ role: "TIENDA", locationId: 10 }), 10);
  // Sin ubicación no se amplía a la vista global: null significa "sin inventarios".
  assert.equal(resolveLocationScope({ role: "TIENDA", locationId: null }), null);
  assert.equal(resolveLocationScope({ role: "CAJERO", locationId: 7 }), 7);
  assert.equal(resolveLocationScope({ role: "CAJERO", locationId: null }), null);
  assert.equal(resolveLocationScope({ role: "ADMIN", locationId: 3 }), null);
});

test("alcanceDeFiltro da vista global solo a la allow-list", () => {
  assert.equal(alcanceDeFiltro({ role: "ADMIN", locationId: 5 }), null);
  assert.equal(alcanceDeFiltro({ role: "INVENTARIO" }), null);
  assert.equal(alcanceDeFiltro({ role: "TIENDA", locationId: 10 }), 10);
});

test("alcanceDeFiltro rechaza a un rol sin ubicación en vez de darle la vista global", () => {
  // Este es el caso que el deny-list cubría mal: un rol nuevo sin locationId habría
  // visto todas las tiendas.
  assert.equal(alcanceDeFiltro({ role: "CAJERO", locationId: null }), SIN_ALCANCE);
  assert.equal(alcanceDeFiltro({ role: "TIENDA", locationId: null }), SIN_ALCANCE);
  assert.equal(alcanceDeFiltro(undefined), SIN_ALCANCE);
  assert.equal(alcanceDeFiltro(null), SIN_ALCANCE);
});

test("los dos conjuntos de roles son el mismo y están vacíos para roles ajenos", () => {
  assert.equal(ROLES_CON_COSTOS, ROLES_CON_VISTA_GLOBAL);
  assert.equal(ROLES_CON_COSTOS.has("CAJERO"), false);
  assert.equal(ROLES_CON_VISTA_GLOBAL.has("TIENDA"), false);
});
