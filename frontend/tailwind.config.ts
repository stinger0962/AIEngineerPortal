import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14213d",
        cream: "#f8f3e8",
        ember: "#f77f00",
        sand: "#e7d8c9",
        pine: "#264653",
        mint: "#d9f0e1"
      },
      boxShadow: {
        panel: "0 20px 50px rgba(20, 33, 61, 0.12)"
      },
      fontFamily: {
        display: ["Georgia", "serif"],
        body: ["Segoe UI", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
