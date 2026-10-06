/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Deep SaaS background & surfaces
        dark: {
          bg: '#090d16',
          surface: '#0f172a',
          elevated: '#1e293b',
          hover: '#24334d',
          border: 'rgba(255, 255, 255, 0.08)',
          borderSubtle: 'rgba(255, 255, 255, 0.05)',
          borderFocus: 'rgba(99, 102, 241, 0.4)',
        },
        // Synapse Brand Primary (Electric Indigo / Cyan)
        synapse: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        cyanBrand: {
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
        },
        // Semantic status colors
        risk: {
          low:      '#10b981',  // emerald
          medium:   '#f59e0b',  // amber
          high:     '#ef4444',  // red
          critical: '#dc2626',  // dark red
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-sm': '0 0 15px -3px rgba(99, 102, 241, 0.15)',
        'glow-md': '0 0 25px -5px rgba(99, 102, 241, 0.25)',
        'glow-cyan': '0 0 25px -5px rgba(6, 182, 212, 0.25)',
        'glow-danger': '0 0 25px -5px rgba(239, 68, 68, 0.25)',
      },
      borderRadius: {
        'xl': '0.875rem',
        '2xl': '1.125rem',
      },
    },
  },
  plugins: [],
};
