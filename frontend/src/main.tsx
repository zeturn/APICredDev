import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeProvider } from "./lib/watercolor";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import ToastViewport from "./ui/ToastViewport";
import GlobalLoading from "./ui/GlobalLoading";
import { I18nProvider } from "./i18n";
import { ThemeProvider as DarkModeProvider } from "./theme";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <DarkModeProvider>
        <I18nProvider>
        <BrowserRouter>
          <GlobalLoading />
          <App />
          <ToastViewport />
        </BrowserRouter>
        </I18nProvider>
      </DarkModeProvider>
    </ThemeProvider>
  </React.StrictMode>
);

