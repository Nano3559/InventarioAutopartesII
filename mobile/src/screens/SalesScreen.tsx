import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function SalesScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Ventas</Text>
      <Text style={styles.placeholder}>Módulo de ventas - por implementar</Text>
    </View>
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
    marginBottom: 8,
  },
  placeholder: {
    color: "#6b7280",
  },
});
