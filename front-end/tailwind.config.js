/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        civic: {
          50: '#effbff',
          100: '#d7f4ff',
          200: '#b5ecff',
          300: '#82ddff',
          400: '#47c7ff',
          500: '#1fa9f5',
          600: '#1189d2',
        },
      },
      boxShadow: {
        soft: '0 10px 30px -12px rgba(15, 23, 42, 0.2)',
        glow: '0 0 40px -10px rgba(34, 211, 238, 0.45)',
      },
    },
  },
  plugins: [],
}

