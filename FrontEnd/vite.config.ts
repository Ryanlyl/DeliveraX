import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function normalizeBasePath(value: string) {
  const trimmedValue = value.trim();

  if (trimmedValue === "/" || trimmedValue === "") {
    return "/";
  }

  const withLeadingSlash = trimmedValue.startsWith("/") ? trimmedValue : `/${trimmedValue}`;

  return withLeadingSlash.endsWith("/") ? withLeadingSlash : `${withLeadingSlash}/`;
}

const repositoryName = process.env.GITHUB_REPOSITORY?.split("/")[1];
const defaultBasePath =
  process.env.GITHUB_ACTIONS === "true" && repositoryName ? `/${repositoryName}/` : "/";
const basePath = normalizeBasePath(process.env.VITE_BASE_PATH || defaultBasePath);

export default defineConfig({
  base: basePath,
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
