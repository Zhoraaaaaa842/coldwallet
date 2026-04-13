/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0F0F13',
          secondary: '#17171C',
          tertiary: '#1E1E26',
          hover: '#252530',
        },
        border: {
          DEFAULT: '#2A2A35',
          focus: '#A855F7',
        },
        text: {
          primary: '#FFFFFF',
          secondary: '#9CA3AF',
          muted: '#6B7280',
        },
        accent: {
          DEFAULT: '#A855F7',
          hover: '#9333EA',
          dark: '#7C3AED',
        },
        success: '#22C55E',
        warning: '#F59E0B',
        error: '#EF4444',
        eth: {
          blue: '#627EEA',
        },
      },
      fontFamily: {
        sans: ['Segoe UI', 'Inter', 'Arial', 'sans-serif'],
        mono: ['Consolas', 'Courier New', 'monospace'],
      },
      fontSize: {
        'balance-rub': ['46px', { lineHeight: '1.1', fontWeight: '800' }],
        'balance-eth': ['42px', { lineHeight: '1.1', fontWeight: '700' }],
        'title': ['28px', { lineHeight: '1.2', fontWeight: '700' }],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '20px',
      },
    },
  },
  plugins: [],
}
