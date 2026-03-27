import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiPort = process.env.WEATHERWEAR_API_PORT || "8000";
const apiUrl = process.env.WEATHERWEAR_API_URL || `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return;
          }
          if (id.includes("react-router-dom") || id.includes("react-dom") || id.includes("react")) {
            return "react-vendor";
          }
          if (id.includes("i18next") || id.includes("react-i18next")) {
            return "i18n-vendor";
          }
          if (id.includes("@tanstack/react-query")) {
            return "query-vendor";
          }
          return undefined;
        },
      },
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    open: process.env.WEATHERWEAR_OPEN_BROWSER === "1",
    proxy: {
      "/api": {
        target: apiUrl,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
  },
});
