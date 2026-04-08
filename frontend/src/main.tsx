import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeProvider } from "./lib/watercolor";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import ToastViewport from "./ui/ToastViewport";
import GlobalLoading from "./ui/GlobalLoading";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <GlobalLoading />
        <App />
        <ToastViewport />
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>
);

