import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from "react-native";
import { useSession } from "../navigation/AppNavigator";

const modules = [
  { label: "Inventario", screen: "Inventory", color: "#2563eb" },
  { label: "Ventas", screen: "Sales", color: "#16a34a" },
  { label: "Escanear Producto", screen: "Scanner", color: "#9333ea" },
];

export default function HomeScreen({ navigation }: any) {
  const { user, logout } = useSession();
  const availableModules = modules.filter((mod) =>
    mod.screen === "Inventory"
      ? user?.role === "ADMIN" || user?.role === "INVENTARIO" || user?.role === "TIENDA"
      : mod.screen === "Sales"
        ? user?.role === "ADMIN" || user?.role === "TIENDA"
        : true
  );

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.welcome}>Hola, {user?.name}</Text>
      <Text style={styles.title}>Módulos</Text>
      <View style={styles.grid}>
        {availableModules.map((mod) => (
          <TouchableOpacity
            key={mod.screen}
            style={[styles.card, { backgroundColor: mod.color }]}
            onPress={() => navigation.navigate(mod.screen)}
          >
            <Text style={styles.cardText}>{mod.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <TouchableOpacity style={styles.logout} onPress={logout}>
        <Text style={styles.logoutText}>Cerrar sesión</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    padding: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: "bold",
    marginBottom: 16,
  },
  welcome: {
    color: "#4b5563",
    marginBottom: 4,
  },
  grid: {
    gap: 12,
  },
  card: {
    borderRadius: 12,
    padding: 24,
    alignItems: "center",
  },
  cardText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
  },
  logout: {
    borderWidth: 1,
    borderColor: "#dc2626",
    borderRadius: 8,
    padding: 12,
    alignItems: "center",
    marginTop: 24,
  },
  logoutText: {
    color: "#dc2626",
    fontWeight: "600",
  },
});
