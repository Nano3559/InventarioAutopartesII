import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import LoginScreen from "../screens/LoginScreen";
import HomeScreen from "../screens/HomeScreen";
import InventoryScreen from "../screens/InventoryScreen";
import SalesScreen from "../screens/SalesScreen";
import ScannerScreen from "../screens/ScannerScreen";

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Login">
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
        <Stack.Screen name="Home" component={HomeScreen} options={{ title: "Inicio" }} />
        <Stack.Screen name="Inventory" component={InventoryScreen} options={{ title: "Inventario" }} />
        <Stack.Screen name="Sales" component={SalesScreen} options={{ title: "Ventas" }} />
        <Stack.Screen name="Scanner" component={ScannerScreen} options={{ title: "Escanear" }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
