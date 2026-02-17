/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './directory/templates/**/*.html',
    './directory/**/*.py',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#0ea5e9',
        secondary: '#06b6d4',
      }
    }
  },
  plugins: [],
}
