import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: resolve(__dirname, "../custom_components/sharing_is_caring/frontend"),
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "src/sharing-is-caring-panel.ts"),
      formats: ["es"],
      fileName: () => "sharing-is-caring-panel.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
    minify: "esbuild",
    sourcemap: false,
  },
});
