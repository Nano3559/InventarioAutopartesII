import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View, Switch, ScrollView } from "react-native";
import api, { pendingOperationId, completeOperation, getPendingOperation } from "../services/api";
import { useSession } from "../navigation/AppNavigator";
import { precioVentaNormal, totalCarrito } from "../utils/precioVenta";

interface Product { id: number; itemCode: string; name: string; brand: string; price1: number | string; price2?: number | string | null; wholesalePrice?: number | string | null; stock: number; }
interface CartItem { product: Product; quantity: number; priceMode: "POR_MENOR" | "POR_MAYOR"; }

export default function SalesScreen() {
  const { user, permissions } = useSession();
  const [search, setSearch] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [bankAccounts, setBankAccounts] = useState<{ id: number; code: string; name: string }[]>([]);
  const [bankAccountId, setBankAccountId] = useState(0);
  const [bankReference, setBankReference] = useState("");
  const [bankDate, setBankDate] = useState(new Intl.DateTimeFormat("en-CA", { timeZone: "America/La_Paz", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date()));
  const [bankConfirmed, setBankConfirmed] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("EFECTIVO");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [creditCustomer, setCreditCustomer] = useState("");
  useEffect(() => { if (user) void getPendingOperation(user.id, "SALE_NORMAL").then(setPendingId); }, [user]);
  const checkPending = async () => {
    if (!pendingId || !user) return;
    try {
      const response = await api.get(`/operations/SALE_NORMAL/${pendingId}`);
      Alert.alert("Venta confirmada", `Venta #${response.data.result.id}${response.data.result.status === "VOIDED" ? " ANULADA" : ""}. Revise el comprobante antes de cerrar el intento.`, [
        { text: "Volver", style: "cancel" },
        { text: "Ya revisé el resultado", onPress: () => { void completeOperation(user.id, "SALE_NORMAL").then(() => { setPendingId(null); setCart([]); }); } },
      ]);
    } catch (error: any) { Alert.alert("Resultado pendiente", error.response?.data?.message || "Reintente sin cambiar los datos de la venta."); }
  };
  // Cada línea comunica su nivel de precio al servidor.
  const total = totalCarrito(cart.map((item) => ({ producto: item.product, cantidad: item.quantity, priceMode: item.priceMode })));

  const findProducts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get("/products", { params: { search: search.trim() || undefined, limit: 20, locationId: user?.locationId || undefined } });
      setProducts(response.data.products || []);
    } catch (requestError: any) {
      Alert.alert("Error", requestError.response?.data?.message || "No se pudieron consultar productos.");
    } finally { setLoading(false); }
  }, [search, user?.locationId]);

  useEffect(() => {
    const timer = setTimeout(findProducts, 300);
    return () => clearTimeout(timer);
  }, [findProducts]);

  const addToCart = (product: Product) => {
    if (product.stock < 1) { Alert.alert("Sin stock", "Este producto no tiene stock disponible."); return; }
    setCart((current) => {
      const found = current.find((item) => item.product.id === product.id);
      if (found) return current.map((item) => item.product.id === product.id ? { ...item, quantity: Math.min(item.quantity + 1, product.stock) } : item);
      return [...current, { product, quantity: 1, priceMode: "POR_MENOR" }];
    });
  };

  const changeQuantity = (productId: number, delta: number) => setCart((current) => current.flatMap((item) => {
    if (item.product.id !== productId) return [item];
    const quantity = item.quantity + delta;
    return quantity > 0 && quantity <= item.product.stock ? [{ ...item, quantity }] : quantity <= 0 ? [] : [item];
  }));

  useEffect(() => { setBankConfirmed(false); }, [total, paymentMethod, bankAccountId, bankReference, bankDate]);
  useEffect(() => { if (["QR", "TRANSFERENCIA"].includes(paymentMethod)) void api.get("/payments/receiving-accounts").then(r => setBankAccounts(r.data.accounts)).catch(() => Alert.alert("Cuenta no disponible", "No se pudieron cargar cuentas receptoras. Configure las cuentas desde administración web.")); }, [paymentMethod]);

  const submitSale = async () => {
    if (submitting) return;
    if (paymentMethod === "CREDITO" && !creditCustomer.trim()) { Alert.alert("Cliente requerido", "Identifique al cliente de la venta a crédito."); return; }
    if (!cart.length) { Alert.alert("Carrito vacío", "Agrega al menos un producto."); return; }
    try {
      setSubmitting(true);
      if (!user) return;
      const operationId = await pendingOperationId(user.id, "SALE_NORMAL");
      setPendingId(operationId);
      const response = await api.post("/sales", {
        operationId,
        ...(paymentMethod === "CREDITO" ? { customerData: { name: creditCustomer.trim() } } : {}),
        items: cart.map(({ product, quantity, priceMode }) => ({ productId: product.id, quantity, priceMode })),
        payments: [{ method: paymentMethod, amount: total, ...(["QR", "TRANSFERENCIA"].includes(paymentMethod) ? { bankVerification: { receivingAccountId: bankAccountId, reference: bankReference, operationDate: bankDate, confirmed: bankConfirmed } } : {}) }],
        locationId: user?.locationId || undefined,
      });
      await completeOperation(user.id, "SALE_NORMAL");
      setPendingId(null);
      if (response.data.status === "VOIDED") { Alert.alert("Venta anulada", "El intento corresponde a una venta anulada. Revise su historial."); return; }
      setCart([]);
      setCreditCustomer(""); setBankConfirmed(false); setBankReference("");
      await findProducts();
      Alert.alert("Venta registrada", "La venta se registró y el stock fue actualizado.");
    } catch (requestError: any) {
      Alert.alert("No se registró la venta", requestError.response?.data?.message || "Verifica el stock y el pago.");
    } finally { setSubmitting(false); }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Nueva venta</Text>
      {paymentMethod === "CREDITO" && <TextInput style={styles.search} value={creditCustomer} onChangeText={setCreditCustomer} placeholder="Nombre del cliente a crédito" />}
      {pendingId && <TouchableOpacity onPress={checkPending}><Text>Consultar resultado del intento pendiente</Text></TouchableOpacity>}
      <TextInput style={styles.search} placeholder="Buscar producto o código" value={search} onChangeText={setSearch} />
      {loading ? <ActivityIndicator color="#2563eb" /> : null}
      <FlatList data={products} keyExtractor={(item) => String(item.id)} style={styles.results} renderItem={({ item }) => (
        <TouchableOpacity style={styles.product} onPress={() => addToCart(item)}>
          <View style={styles.productInfo}><Text style={styles.name}>{item.name}</Text><Text style={styles.muted}>{item.brand} · {item.itemCode} · Stock: {item.stock}</Text></View>
          <Text style={styles.price}>Bs. {precioVentaNormal(item).toFixed(2)}</Text>
        </TouchableOpacity>
      )} />
      <View style={styles.cart}>
        <Text style={styles.section}>Carrito ({cart.length})</Text>
        {cart.map(({ product, quantity, priceMode }) => <View style={styles.cartRow} key={product.id}>
          <Text style={styles.cartName}>{product.name} x{quantity}</Text>
          <TouchableOpacity disabled={!permissions.includes("ventas-mayor") || !Number(product.wholesalePrice) || Number(product.wholesalePrice) > Number(product.price1)} onPress={() => setCart((prev) => prev.map((line) => line.product.id === product.id ? { ...line, priceMode: line.priceMode === "POR_MENOR" ? "POR_MAYOR" : "POR_MENOR" } : line))}><Text>{priceMode === "POR_MENOR" ? "POR MENOR" : "POR MAYOR"}</Text></TouchableOpacity>
          <View style={styles.controls}><TouchableOpacity onPress={() => changeQuantity(product.id, -1)}><Text style={styles.control}>−</Text></TouchableOpacity><TouchableOpacity onPress={() => changeQuantity(product.id, 1)}><Text style={styles.control}>+</Text></TouchableOpacity></View>
          <Text style={styles.lineTotal}>Bs. {(precioVentaNormal(product, priceMode) * quantity).toFixed(2)}</Text>
        </View>)}
        <Text style={styles.total}>Total: Bs. {total.toFixed(2)}</Text>
        <View style={styles.methods}>{["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"].map((method) => <TouchableOpacity key={method} style={[styles.method, paymentMethod === method && styles.selected]} onPress={() => setPaymentMethod(method)}><Text style={paymentMethod === method ? styles.selectedText : styles.methodText}>{method}</Text></TouchableOpacity>)}</View>
        {["QR", "TRANSFERENCIA"].includes(paymentMethod) && <ScrollView style={{ maxHeight: 220 }} nestedScrollEnabled><Text>Verificación manual. Compruebe el abono en la cuenta de la empresa, no solo una captura.</Text>
          {!bankAccounts.length && <Text>Registre una cuenta receptora desde administración web.</Text>}
          {bankAccounts.map(account => <TouchableOpacity key={account.id} onPress={() => setBankAccountId(account.id)}><Text>{bankAccountId === account.id ? "✓ " : "○ "}{account.code} · {account.name}</Text></TouchableOpacity>)}
          <TextInput accessibilityLabel="Referencia bancaria" style={styles.search} value={bankReference} onChangeText={setBankReference} placeholder="Referencia bancaria" maxLength={120} />
          <TextInput accessibilityLabel="Fecha bancaria" style={styles.search} value={bankDate} onChangeText={setBankDate} placeholder="Fecha del abono YYYY-MM-DD" />
          <View style={styles.controls}><Switch value={bankConfirmed} onValueChange={setBankConfirmed} /><Text>Comprobé abono, importe y cuenta</Text></View>
        </ScrollView>}
        <TouchableOpacity style={styles.button} onPress={submitSale} disabled={submitting}>{submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Registrar venta</Text>}</TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f3f4f6", padding: 16 }, title: { fontSize: 22, fontWeight: "bold", marginBottom: 12 }, search: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#d1d5db", borderRadius: 8, padding: 12, marginBottom: 8 }, results: { maxHeight: 220 }, product: { backgroundColor: "#fff", padding: 12, marginVertical: 4, borderRadius: 8, flexDirection: "row", justifyContent: "space-between" }, productInfo: { flex: 1 }, name: { fontWeight: "700", color: "#111827" }, muted: { color: "#6b7280", marginTop: 4 }, price: { color: "#2563eb", fontWeight: "700" }, cart: { borderTopWidth: 1, borderColor: "#d1d5db", paddingTop: 12, marginTop: 8 }, section: { fontSize: 18, fontWeight: "700", marginBottom: 8 }, cartRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }, cartName: { flex: 1 }, controls: { flexDirection: "row", gap: 12 }, lineTotal: { color: "#111827", fontWeight: "700" }, control: { color: "#2563eb", fontSize: 22, fontWeight: "700" }, total: { textAlign: "right", fontSize: 18, fontWeight: "700", marginVertical: 10 }, methods: { flexDirection: "row", flexWrap: "wrap", gap: 6 }, method: { borderWidth: 1, borderColor: "#9ca3af", borderRadius: 6, padding: 8 }, selected: { backgroundColor: "#2563eb", borderColor: "#2563eb" }, methodText: { color: "#374151", fontSize: 12 }, selectedText: { color: "#fff", fontSize: 12 }, button: { backgroundColor: "#16a34a", borderRadius: 8, padding: 14, alignItems: "center", marginTop: 12 }, buttonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
