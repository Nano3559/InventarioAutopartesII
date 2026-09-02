import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, TextInput, View } from "react-native";
import api from "../services/api";

interface Product {
  id: number;
  itemCode: string;
  name: string;
  manufacturer: string;
  brand: string;
  model: string;
  year: string;
  price1: number | string;
  price2: number | string;
  stock: number;
}

export default function InventoryScreen() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadProducts = useCallback(async (isRefresh = false) => {
    try {
      isRefresh ? setRefreshing(true) : setLoading(true);
      setError("");
      const response = await api.get("/products", { params: { search: search.trim() || undefined, limit: 100 } });
      setProducts(response.data.products || []);
    } catch (requestError: any) {
      setError(requestError.response?.data?.message || "No se pudo cargar el inventario.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [search]);

  useEffect(() => {
    const timer = setTimeout(() => loadProducts(), 300);
    return () => clearTimeout(timer);
  }, [loadProducts]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Inventario</Text>
      <TextInput style={styles.search} placeholder="Buscar por nombre, código o marca" value={search} onChangeText={setSearch} />
      {loading && !refreshing ? <ActivityIndicator size="large" color="#2563eb" style={styles.loader} /> : null}
      {!!error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        data={products}
        keyExtractor={(item) => String(item.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => loadProducts(true)} />}
        ListEmptyComponent={!loading ? <Text style={styles.empty}>No hay productos para mostrar.</Text> : null}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.name}>{item.name}</Text>
              <Text style={[styles.stock, item.stock === 0 && styles.noStock]}>Stock: {item.stock}</Text>
            </View>
            <Text style={styles.muted}>{item.brand} · {item.model} · {item.year}</Text>
            <Text style={styles.muted}>Código: {item.itemCode} · Fabricante: {item.manufacturer}</Text>
            <Text style={styles.price}>Minorista: Bs. {Number(item.price1).toFixed(2)} · Venta: Bs. {Number(item.price2).toFixed(2)}</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f3f4f6", padding: 16 },
  title: { fontSize: 22, fontWeight: "bold", marginBottom: 12 },
  search: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#d1d5db", borderRadius: 8, padding: 12, marginBottom: 12 },
  loader: { marginTop: 24 },
  error: { color: "#dc2626", marginBottom: 10 },
  empty: { color: "#6b7280", textAlign: "center", marginTop: 24 },
  card: { backgroundColor: "#fff", borderRadius: 10, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: "#e5e7eb" },
  row: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  name: { flex: 1, color: "#111827", fontSize: 16, fontWeight: "700" },
  stock: { color: "#15803d", fontWeight: "700" },
  noStock: { color: "#dc2626" },
  muted: { color: "#4b5563", marginTop: 5 },
  price: { color: "#2563eb", fontWeight: "600", marginTop: 8 },
});
