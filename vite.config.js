import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig(() => ({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [react()],
  resolve: {
    alias: [
      { find: "@/components", replacement: path.resolve(__dirname, "./src/lib/components") },
      { find: "@/hooks", replacement: path.resolve(__dirname, "./src/lib/hooks") },
      { find: "@/lib", replacement: path.resolve(__dirname, "./src/lib/lib") },
      { find: "@/api", replacement: path.resolve(__dirname, "./src/api") },
      { find: "@", replacement: path.resolve(__dirname, "./src") },
    ],
  },
}));
