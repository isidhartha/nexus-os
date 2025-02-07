/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        nexus: {
          bg: '#020b18',
          panel: '#041225',
          border: '#0a3060',
          cyan: '#00d4ff',
          blue: '#0084ff',
          purple: '#7b2fff',
          glow: '#00d4ff40',
          text: '#c8e6ff',
          dim: '#4a7090',
        },
      },
      animation: {
        pulse_orb: 'pulse_orb 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        spin_slow: 'spin 8s linear infinite',
        glow_ring: 'glow_ring 3s ease-in-out infinite',
        scan_line: 'scan_line 3s linear infinite',
        float: 'float 4s ease-in-out infinite',
      },
      keyframes: {
        pulse_orb: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.08)', opacity: '0.85' },
        },
        glow_ring: {
          '0%, 100%': { boxShadow: '0 0 20px #00d4ff40, 0 0 40px #00d4ff20' },
          '50%': { boxShadow: '0 0 40px #00d4ff80, 0 0 80px #00d4ff40' },
        },
        scan_line: {
          '0%': { top: '0%' },
          '100%': { top: '100%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Orbitron', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
