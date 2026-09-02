import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import api from "../services/api";
import { useSession } from "../navigation/AppNavigator";

interface Product { id: number; itemCode: string; name: string; brand: string; price1: number | string; stock: number; }
interface CartItem { product: Product; quantity: number; }

export default function SalesScreen() {
  const { user } = useSession();
  const [search, setSearch] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [paymentMethod, setPaymentMethod] = useState("EFECTIVO");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const total = cart.reduce((sum, item) => sum + item.quantity * Number(item.product.price1), 0);

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
      return [...current, { product, quantity: 1 }];
    });
  };

  const changeQuantity = (productId: number, delta: number) => setCart((current) => current.flatMap((item) => {
    if (item.product.id !== productId) return [item];
    const quantity = item.quantity + delta;
    return quantity > 0 && quantity <= item.product.stock ? [{ ...item, quantity }] : quantity <= 0 ? [] : [item];
  }));

  const submitSale = async () => {
    if (!cart.length) { Alert.alert("Carrito vacío", "Agrega al menos un producto."); return; }
    try {
      setSubmitting(true);
      await api.post("/sales", {
        items: cart.map(({ product, quantity }) => ({ productId: product.id, quantity, unitPrice: Number(product.price1) })),
        payments: [{ method: paymentMethod, amount: Number(total.toFixed(2)) }],
        locationId: user?.locationId || undefined,
      });
      setCart([]);
      await findProducts();
      Alert.alert("Venta registrada", "La venta se registró y el stock fue actualizado.");
    } catch (requestError: any) {
      Alert.alert("No se registró la venta", requestError.response?.data?.message || "Verifica el stock y el pago.");
    } finally { setSubmitting(false); }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Nueva venta</Text>
      <TextInput style={styles.search} placeholder="Buscar producto o código" value={search} onChangeText={setSearch} />
      {loading ? <ActivityIndicator color="#2563eb" /> : null}
      <FlatList data={products} keyExtractor={(item) => String(item.id)} style={styles.results} renderItem={({ item }) => (
        <TouchableOpacity style={styles.product} onPress={() => addToCart(item)}>
          <View style={styles.productInfo}><Text style={styles.name}>{item.name}</Text><Text style={styles.muted}>{item.brand} · {item.itemCode} · Stock: {item.stock}</Text></View>
          <Text style={styles.price}>Bs. {Number(item.price1).toFixed(2)}</Text>
        </TouchableOpacity>
      )} />
      <View style={styles.cart}>
        <Text style={styles.section}>Carrito ({cart.length})</Text>
        {cart.map(({ product, quantity }) => <View style={styles.cartRow} key={product.id}>
          <Text style={styles.cartName}>{product.name} x{quantity}</Text>
          <View style={styles.controls}><TouchableOpacity onPress={() => changeQuantity(product.id, -1)}><Text style={styles.control}>−</Text></TouchableOpacity><TouchableOpacity onPress={() => changeQuantity(product.id, 1)}><Text style={styles.control}>+</Text></TouchableOpacity></View>
        </View>)}
        <Text style={styles.total}>Total: Bs. {total.toFixed(2)}</Text>
        <View style={styles.methods}>{["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"].map((method) => <TouchableOpacity key={method} style={[styles.method, paymentMethod === method && styles.selected]} onPress={() => setPaymentMethod(method)}><Text style={paymentMethod === method ? styles.selectedText : styles.methodText}>{method}</Text></TouchableOpacity>)}</View>
        <TouchableOpacity style={styles.button} onPress={submitSale} disabled={submitting}>{submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Registrar venta</Text>}</TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f3f4f6", padding: 16 }, title: { fontSize: 22, fontWeight: "bold", marginBottom: 12 }, search: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#d1d5db", borderRadius: 8, padding: 12, marginBottom: 8 }, results: { maxHeight: 220 }, product: { backgroundColor: "#fff", padding: 12, marginVertical: 4, borderRadius: 8, flexDirection: "row", justifyContent: "space-between" }, productInfo: { flex: 1 }, name: { fontWeight: "700", color: "#111827" }, muted: { color: "#6b7280", marginTop: 4 }, price: { color: "#2563eb", fontWeight: "700" }, cart: { borderTopWidth: 1, borderColor: "#d1d5db", paddingTop: 12, marginTop: 8 }, section: { fontSize: 18, fontWeight: "700", marginBottom: 8 }, cartRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }, cartName: { flex: 1 }, controls: { flexDirection: "row", gap: 12 }, control: { color: "#2563eb", fontSize: 22, fontWeight: "700" }, total: { textAlign: "right", fontSize: 18, fontWeight: "700", marginVertical: 10 }, methods: { flexDirection: "row", flexWrap: "wrap", gap: 6 }, method: { borderWidth: 1, borderColor: "#9ca3af", borderRadius: 6, padding: 8 }, selected: { backgroundColor: "#2563eb", borderColor: "#2563eb" }, methodText: { color: "#374151", fontSize: 12 }, selectedText: { color: "#fff", fontSize: 12 }, button: { backgroundColor: "#16a34a", borderRadius: 8, padding: 14, alignItems: "center", marginTop: 12 }, buttonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
