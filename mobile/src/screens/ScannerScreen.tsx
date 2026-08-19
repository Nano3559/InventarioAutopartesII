import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";

export default function ScannerScreen({ navigation }: any) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Escanear Producto</Text>
      <Text style={styles.placeholder}>
       Funcionalidad de cámara - por implementar
      </Text>
      <TouchableOpacity style={styles.button} onPress={() => navigation.goBack()}>
        <Text style={styles.buttonText}>Volver</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    padding: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    fontSize: 22,
    fontWeight: "bold",
    marginBottom: 8,
  },
  placeholder: {
    color: "#6b7280",
    marginBottom: 24,
  },
  button: {
    backgroundColor: "#2563eb",
    borderRadius: 8,
    padding: 14,
    paddingHorizontal: 32,
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
