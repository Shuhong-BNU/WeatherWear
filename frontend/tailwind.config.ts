import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e7ff",
          200: "#bfd4ff",
          300: "#94b5ff",
          400: "#5f87ff",
          500: "#3459ff",
          600: "#2848d8",
          700: "#2038aa",
          900: "#12204a",
        },
      },
      boxShadow: {
        soft: "0 18px 40px rgba(15, 23, 42, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
