/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        railway: {
          dark: '#080c14',
          card: '#0f172a',
          border: '#1e293b',
          accent: '#0284c7',
          cyan: '#38bdf8',
          red: '#ef4444',
          yellow: '#eab308',
          green: '#22c55e',
        },
      },
    },
  },
  plugins: [],
}
