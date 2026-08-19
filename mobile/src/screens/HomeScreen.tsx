import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from "react-native";

const modules = [
  { label: "Inventario", screen: "Inventory", color: "#2563eb" },
  { label: "Ventas", screen: "Sales", color: "#16a34a" },
  { label: "Escanear Producto", screen: "Scanner", color: "#9333ea" },
];

export default function HomeScreen({ navigation }: any) {
  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Módulos</Text>
      <View style={styles.grid}>
        {modules.map((mod) => (
          <TouchableOpacity
            key={mod.screen}
            style={[styles.card, { backgroundColor: mod.color }]}
            onPress={() => navigation.navigate(mod.screen)}
          >
            <Text style={styles.cardText}>{mod.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
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
});
