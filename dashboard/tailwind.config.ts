import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      keyframes: {
        "fade-slide-in": {
          "0%": { opacity: "0", transform: "translateY(-8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-slide-in": "fade-slide-in 0.3s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
