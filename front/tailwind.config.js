/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
    "./public/**/*.html", // 确保公共文件夹中�?HTML 被扫�?    "./electron/**/*.js" // 确保 Electron 主进程文件被扫描
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms'), // 添加表单样式插件
    require('@tailwindcss/typography') // 添加排版插件
  ],
}
