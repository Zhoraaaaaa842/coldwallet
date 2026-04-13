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
          primary: '#000000',
          secondary: '#0A0A0A',
          tertiary: '#111111',
          hover: '#1A1A1A',
          card: '#0D0D0D',
        },
        border: {
          DEFAULT: '#1F1F1F',
          focus: '#333333',
          light: '#2A2A2A',
        },
        text: {
          primary: '#FFFFFF',
          secondary: '#A0A0A0',
          muted: '#666666',
          dim: '#4A4A4A',
        },
        accent: {
          DEFAULT: '#FFFFFF',
          hover: '#E5E5E5',
          dark: '#CCCCCC',
        },
        success: '#00D26A',
        warning: '#F59E0B',
        error: '#FF4655',
        eth: {
          blue: '#627EEA',
        },
      },
      fontFamily: {
        sans: ['Segoe UI', 'Inter', 'Arial', 'sans-serif'],
        mono: ['Consolas', 'Courier New', 'monospace'],
      },
      fontSize: {
        'balance-rub': ['52px', { lineHeight: '1', fontWeight: '900' }],
        'balance-eth': ['32px', { lineHeight: '1.2', fontWeight: '700' }],
        'title': ['32px', { lineHeight: '1.2', fontWeight: '800' }],
      },
      borderRadius: {
        'xl': '16px',
        '2xl': '20px',
        '3xl': '24px',
      },
    },
  },
  plugins: [],
}
