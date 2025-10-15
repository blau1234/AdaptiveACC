# Frontend Build Instructions

## Quick Start

### 1. Install Dependencies
```bash
npm install
```

### 2. Build for Production
```bash
npm run build
```

This will generate files in the `../templates/` directory that FastAPI will serve.

### 3. Start the Server
Go back to the project root and run:
```bash
python main.py
```

## Development Mode (Optional)

If you want to develop with hot reload:
```bash
npm run dev
```

Then visit http://localhost:3000

## Troubleshooting

### Build fails with "Cannot find module"
Make sure you ran `npm install` first.

### 3D model doesn't load
1. Check browser console for errors (F12)
2. Make sure the IFC file is valid
3. Try with a different IFC file

### Form submission fails
This is likely a backend issue, not frontend. Check FastAPI logs.

## File Structure

- `index.html` - Main HTML template
- `style.css` - Styling
- `main.js` - Three.js viewer and form logic
- `vite.config.js` - Build configuration
- `package.json` - Dependencies

## What's Included

✓ Three.js 3D viewer
✓ IFC file loader (web-ifc-three)
✓ Drag & drop file upload
✓ OrbitControls (mouse navigation)
✓ Form submission to backend
✓ Results display
