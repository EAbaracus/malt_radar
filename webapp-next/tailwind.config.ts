import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        caskChar: '#1A120B',
        surface: '#241A10',
        surfaceElevated: '#2B1F14',
        parchment: '#EDE1C8',
        parchmentLt: '#F5ECD8',
        inkSoft: '#2B1F14',
        copper: '#A6672C',
        copperDim: '#8A5424',
        verdigris: '#5C7A6E',
        brass: '#C9A227',
        oxblood: '#6B1E23',
        oxbloodLt: '#D6645C',
        textPrimary: '#EDE1C8',
        textSecondary: '#BDB2A0',
        textMuted: '#8C8071',
        success: '#5C7A6E',
      },
      fontFamily: {
        fraunces: ['Fraunces', 'serif'],
        body: ['SourceSerif4', 'serif'],
        ui: ['Inter', 'sans-serif'],
        medallion: ['CourierPrime', 'monospace'],
      },
      borderRadius: {
        xs: '10px',
        sm: '12px',
        md: '16px',
        lg: '20px',
        xl: '24px',
        pill: '999px',
      },
    },
  },
  plugins: [],
};

export default config;