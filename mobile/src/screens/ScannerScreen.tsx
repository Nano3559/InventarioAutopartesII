import React from "react";
import { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, Image, ScrollView, ActivityIndicator } from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as FileSystem from "expo-file-system";
import api from "../services/api";

interface SearchResult {
  id: number;
  itemCode: string;
  name: string;
  brand: string;
  model: string;
  price1: number;
  totalStock: number;
}

export default function ScannerScreen({ navigation }: any) {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [assetFileName, setAssetFileName] = useState<string | null>(null);
  const [assetFileSize, setAssetFileSize] = useState<number | undefined>(undefined);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const MAX_SIZE = 5 * 1024 * 1024;

  const ALLOWED_EXTENSIONS: Record<string, string> = {
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    png: "image/png",
    webp: "image/webp",
  };

  const getMimeType = (fileName: string | null | undefined, uri: string): string | null => {
    if (fileName) {
      const ext = fileName.split(".").pop()?.toLowerCase();
      if (ext && ALLOWED_EXTENSIONS[ext]) return ALLOWED_EXTENSIONS[ext];
    }
    const uriExt = uri.split(".").pop()?.split("?")[0]?.toLowerCase();
    if (uriExt && ALLOWED_EXTENSIONS[uriExt]) return ALLOWED_EXTENSIONS[uriExt];
    return null;
  };

  const getFileName = (assetFileName: string | null | undefined, uri: string, mimeType: string): string => {
    if (assetFileName) return assetFileName;
    const ext = mimeType === "image/png" ? "png" : mimeType === "image/webp" ? "webp" : "jpg";
    return `image.${ext}`;
  };

  const selectImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError("Necesitas permitir el acceso a tus fotos.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });
    if (!result.canceled) {
      const asset = result.assets[0];
      setImageUri(asset.uri);
      setAssetFileName(asset.fileName ?? null);
      setAssetFileSize(asset.fileSize);
      setResults([]);
      setError("");
    }
  };

  const searchImage = async () => {
    if (!imageUri) return;
    const mimeType = getMimeType(assetFileName, imageUri);
    if (!mimeType) {
      setError("Formato no permitido. Usa JPEG, PNG o WebP.");
      return;
    }
    let fileSize = assetFileSize;
    if (fileSize === undefined || fileSize === null) {
      const info = await FileSystem.getInfoAsync(imageUri);
      fileSize = info.exists ? info.size : undefined;
    }
    if (fileSize !== undefined && fileSize !== null && fileSize > MAX_SIZE) {
      setError("La imagen supera 5 MB. Usa una imagen más pequeña.");
      return;
    }
    try {
      setLoading(true);
      setError("");
      const fileName = getFileName(assetFileName, imageUri, mimeType);
      const form = new FormData();
      form.append("image", { uri: imageUri, name: fileName, type: mimeType } as any);
      const response = await api.post("/products/search-image", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResults(response.data.products || []);
      if (!(response.data.products || []).length) setError("No se encontraron productos relacionados.");
    } catch {
      setError("No se pudo realizar la búsqueda.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Buscar por imagen</Text>
      <Text style={styles.placeholder}>Selecciona una foto del repuesto para encontrar coincidencias.</Text>
      {imageUri && <Image source={{ uri: imageUri }} style={styles.preview} />}
      <TouchableOpacity style={styles.button} onPress={selectImage}>
        <Text style={styles.buttonText}>{imageUri ? "Cambiar imagen" : "Seleccionar imagen"}</Text>
      </TouchableOpacity>
      {imageUri && (
        <TouchableOpacity style={[styles.button, styles.searchButton]} onPress={searchImage} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Buscar producto</Text>}
        </TouchableOpacity>
      )}
      {!!error && <Text style={styles.error}>{error}</Text>}
      {results.map((product) => (
        <View key={product.id} style={styles.result}>
          <Text style={styles.resultName}>{product.name}</Text>
          <Text style={styles.resultText}>{product.brand} · {product.model}</Text>
          <Text style={styles.resultText}>Código: {product.itemCode}</Text>
          <Text style={styles.resultPrice}>Bs. {Number(product.price1).toFixed(2)} · Stock: {product.totalStock}</Text>
        </View>
      ))}
      <TouchableOpacity style={[styles.button, styles.backButton]} onPress={() => navigation.goBack()}>
        <Text style={styles.buttonText}>Volver</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    padding: 16,
    alignItems: "center",
    justifyContent: "flex-start",
  },
  title: {
    fontSize: 22,
    fontWeight: "bold",
    marginBottom: 8,
  },
  placeholder: {
    color: "#6b7280",
    marginBottom: 24,
    textAlign: "center",
  },
  preview: {
    width: 220,
    height: 220,
    borderRadius: 12,
    marginBottom: 16,
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
  searchButton: {
    backgroundColor: "#16a34a",
    marginTop: 10,
  },
  backButton: {
    backgroundColor: "#4b5563",
    marginTop: 20,
  },
  error: {
    color: "#dc2626",
    marginTop: 16,
    textAlign: "center",
  },
  result: {
    width: "100%",
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 14,
    marginTop: 12,
    borderWidth: 1,
    borderColor: "#e5e7eb",
  },
  resultName: {
    color: "#111827",
    fontSize: 16,
    fontWeight: "700",
  },
  resultText: {
    color: "#4b5563",
    marginTop: 4,
  },
  resultPrice: {
    color: "#2563eb",
    fontWeight: "600",
    marginTop: 8,
  },
});
