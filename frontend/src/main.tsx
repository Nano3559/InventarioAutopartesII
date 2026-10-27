import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import App from "./App";
import "./index.css";

function Root() {
  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
}

useAuthStore.getState().loadFromStorage();

const root = (import.meta.hot?.data.root as ReturnType<typeof ReactDOM.createRoot> | undefined)
  ?? ReactDOM.createRoot(document.getElementById("root")!);
if (import.meta.hot) import.meta.hot.data.root = root;
root.render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
