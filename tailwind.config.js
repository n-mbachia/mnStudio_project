/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
    './static/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        mahogany: {
          50: '#fbf7f6',
          100: '#f5ebe8',
          200: '#ebd5cd',
          300: '#deb5a8',
          400: '#cc8d78',
          500: '#b86f56',
          600: '#a55a42',
          700: '#8a4836',
          800: '#733d30',
          900: '#60352b',
          950: '#361a14',
        },
        charcoal: {
          50: '#f6f6f6',
          100: '#e7e7e7',
          200: '#d1d1d1',
          300: '#b0b0b0',
          400: '#888888',
          500: '#6d6d6d',
          600: '#5d5d5d',
          700: '#4f4f4f',
          800: '#454545',
          900: '#1c1917',
          950: '#0f0e0d',
        },
        timber: {
          50: '#f9f7f4',
          100: '#f0ebe3',
          200: '#e0d6c5',
          300: '#ccba9e',
          400: '#b89d7a',
          500: '#a8855e',
          600: '#9c7652',
          700: '#825f44',
          800: '#6b4f3b',
          900: '#574131',
          950: '#2e211b',
        },
      },
      fontFamily: {
        serif: ['Playfair Display', 'Georgia', 'Cambria', 'Times New Roman', 'serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};
