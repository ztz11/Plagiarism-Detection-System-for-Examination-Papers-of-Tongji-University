// eslint.config.js
import js from "@eslint/js";

export default [
    js.configs.recommended,
    {
        files: ["src/**/*.{js,vue}"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
        },
        rules: {
            // 你可以在这里添加或覆盖任何规则
            // "no-console": "warn",
        },
    },
];