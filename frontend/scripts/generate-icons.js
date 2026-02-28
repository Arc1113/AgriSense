// Icon generation script for AgriSense PWA
// Run with: node scripts/generate-icons.js

const fs = require('fs');
const path = require('path');

const sizes = [72, 96, 128, 144, 152, 192, 384, 512];
const iconsDir = path.join(__dirname, '../public/icons');

// Simple SVG icon with proper sizing
const generateSVGIcon = (size) => `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#22c55e"/>
      <stop offset="100%" style="stop-color:#16a34a"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="100" fill="url(#bg)"/>
  <g transform="translate(100, 80) scale(1.6)">
    <path fill="#ffffff" d="M140 20c-20 0-80 40-80 100s40 80 80 80c0-40 0-80 20-100s60-20 60-20c0-40-40-60-80-60z"/>
    <path fill="none" stroke="#16a34a" stroke-width="5" stroke-linecap="round" d="M140 120c-20 20-40 60-40 80"/>
    <path fill="none" stroke="#16a34a" stroke-width="4" stroke-linecap="round" d="M120 140c10-10 25-15 35-12"/>
    <path fill="none" stroke="#16a34a" stroke-width="4" stroke-linecap="round" d="M130 160c8-8 20-12 28-10"/>
  </g>
</svg>`;

// Ensure icons directory exists
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

// For now, create SVG versions (can be converted to PNG using tools like sharp or canvas)
sizes.forEach(size => {
  const svgContent = generateSVGIcon(size);
  const filename = path.join(iconsDir, `icon-${size}x${size}.svg`);
  fs.writeFileSync(filename, svgContent);
  console.log(`Generated: icon-${size}x${size}.svg`);
});

console.log('\\nIcon generation complete!');
console.log('To convert to PNG, use a tool like sharp, canvas, or an online converter.');
