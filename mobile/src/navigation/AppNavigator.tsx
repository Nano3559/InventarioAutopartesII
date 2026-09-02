import React, { createContext, useContext, useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import LoginScreen from "../screens/LoginScreen";
import HomeScreen from "../screens/HomeScreen";
import InventoryScreen from "../screens/InventoryScreen";
import SalesScreen from "../screens/SalesScreen";
import ScannerScreen from "../screens/ScannerScreen";
import { clearSession, getStoredSession, LoginResponse, User } from "../services/api";

const Stack = createNativeStackNavigator();

interface SessionContextValue {
  user: User | null;
  setSession: (session: LoginResponse) => void;
  logout: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession debe usarse dentro de AppNavigator");
  return context;
};

export default function AppNavigator() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStoredSession().then((session) => {
      setUser(session?.user || null);
      setLoading(false);
    });
  }, []);

  const logout = async () => {
    await clearSession();
    setUser(null);
  };

  if (loading) {
    return <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}><ActivityIndicator size="large" color="#2563eb" /></View>;
  }

  const canInventory = user?.role === "ADMIN" || user?.role === "INVENTARIO" || user?.role === "TIENDA";
  const canSales = user?.role === "ADMIN" || user?.role === "TIENDA";

  return (
    <SessionContext.Provider value={{ user, setSession: (session) => setUser(session.user), logout }}>
      <NavigationContainer>
        <Stack.Navigator>
          {!user ? (
            <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
          ) : (
            <>
              <Stack.Screen name="Home" component={HomeScreen} options={{ title: "Inicio" }} />
              {canInventory && <Stack.Screen name="Inventory" component={InventoryScreen} options={{ title: "Inventario" }} />}
              {canSales && <Stack.Screen name="Sales" component={SalesScreen} options={{ title: "Ventas" }} />}
              <Stack.Screen name="Scanner" component={ScannerScreen} options={{ title: "Escanear" }} />
            </>
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </SessionContext.Provider>
  );
}
