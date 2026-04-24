import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./components/**/*.{ts,tsx}",
    "./styles/**/*.css",
    "../../apps/*/frontend/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-geist-sans)"],
        mono: ["var(--font-geist-mono)"],
      },
      colors: {
        bg: "var(--color-bg)",
        surface: {
          DEFAULT: "var(--color-surface)",
          raised: "var(--color-surface-raised)",
          high: "var(--color-surface-high)",
          bright: "var(--color-surface-bright)",
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          dim: "var(--color-accent-dim)",
        },
        border: "var(--color-border)",
      },
      textColor: {
        primary: "var(--color-text)",
        secondary: "var(--color-text-secondary)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
      },
      boxShadow: {
        ambient:
          "0px 24px 48px rgba(0, 0, 0, 0.4), 0px 0px 4px var(--color-accent-glow)",
        subtle: "0px 8px 24px rgba(0, 0, 0, 0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
