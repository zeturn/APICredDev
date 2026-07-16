/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f7f8fb",
          100: "#eef1f7",
          200: "#d9dfee",
          300: "#bcc7e4",
          400: "#96a6d1",
          500: "#7486be",
          600: "#5a6aa3",
          700: "#495686",
          800: "#3d476e",
          900: "#333b57"
        }
      },
      boxShadow: {
        watercolor: "0 18px 45px -28px rgba(15, 23, 42, 0.45)"
      }
    }
  },
  plugins: []
};
