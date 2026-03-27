import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: [
      "@zeturn/watercolor-react",
      "prop-types",
      "react-is",
    ],
  },
  server: {
    port: 5106,
  },
});

