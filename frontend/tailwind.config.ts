import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        'apple-bg': '#f5f5f7',
        'apple-card': '#ffffff',
        'apple-text': '#1d1d1f',
        'apple-muted': '#999999',
        'apple-border': '#e5e5e7',
      },
      borderRadius: {
        'apple': '12px',
        'apple-lg': '16px',
      },
      boxShadow: {
        'apple-sm': '0 1px 3px rgba(0, 0, 0, 0.1)',
        'apple-md': '0 4px 12px rgba(0, 0, 0, 0.1)',
      },
      fontFamily: {
        system: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: []
};

export default config;

