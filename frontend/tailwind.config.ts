import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        aleph: {
          blue: "#0085FF",
          dark: "#0A0E27",
          purple: "#6366F1",
        },
      },
    },
  },
  plugins: [],
};

export default config;
