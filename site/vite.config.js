import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// O site é publicado em https://dpdanilo.github.io/painel-ministerios/
export default defineConfig({
  base: "/painel-ministerios/",
  plugins: [svelte()],
  build: { target: "es2022", chunkSizeWarningLimit: 600 },
});
