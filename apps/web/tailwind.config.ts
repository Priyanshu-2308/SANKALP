import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#005c55",
          container: "#0f766e",
          hover: "#0d9488",
          active: "#115e59",
          fixed: "#9cf2e8",
          "fixed-dim": "#80d5cb",
          "on-fixed": "#00201d",
        },
        surface: {
          DEFAULT: "#f7f9fd",
          dim: "#d8dade",
          bright: "#f7f9fd",
          container: "#eceef2",
          "container-lowest": "#ffffff",
          "container-low": "#f2f4f8",
          "container-high": "#e6e8ec",
          "container-highest": "#e0e2e6",
        },
        ink: {
          primary: "#191c1f",
          secondary: "#3e4947",
          muted: "#6e7977",
          border: "#e5e7eb",
          "border-subtle": "#bdc9c6",
        },
        accent: {
          amber: "#9c573a",
          amberBg: "#ffe5db",
          green: "#0f766e",
          greenBg: "#e6f4f1",
          blue: "#2563eb",
          blueBg: "#eff6ff",
          red: "#ba1a1a",
          redBg: "#ffdad6",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        md: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.5rem",
      },
    },
  },
  plugins: [],
};

export default config;
