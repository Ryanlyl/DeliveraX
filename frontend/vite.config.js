import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, ".", "");
    var apiTarget = env.VITE_DELIVERAX_API_BASE_URL || "http://localhost:8000";
    return {
        plugins: [react()],
        server: {
            proxy: {
                "/api": {
                    target: apiTarget,
                    changeOrigin: true,
                },
                "/health": {
                    target: apiTarget,
                    changeOrigin: true,
                },
            },
        },
    };
});
