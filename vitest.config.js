import { defineConfig } from "vitest/config";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  test: {
    environment: "node",
    pool: "threads",
    include: ["src/**/*.test.js"],
    exclude: [
      "**/node_modules/**",
      "**/dist/**",
      "**/.pytest_cache/**",
      "**/backend/.pytest_cache_local/**",
      "**/pytest-cache-files-*/**",
    ],
  },
  resolve: {
    alias: [
      { find: "@/components", replacement: path.resolve(__dirname, "./src/lib/components") },
      { find: "@/hooks", replacement: path.resolve(__dirname, "./src/lib/hooks") },
      { find: "@/lib", replacement: path.resolve(__dirname, "./src/lib/lib") },
      { find: "@/api", replacement: path.resolve(__dirname, "./src/api") },
      { find: "@", replacement: path.resolve(__dirname, "./src") },
    ],
  },
});
