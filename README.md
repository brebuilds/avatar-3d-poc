# 3D Avatar Generator - Proof of Concept

Transform photos into 3D-printable Pixar-style avatar figurines in minutes!

## Overview

This proof-of-concept validates a complete pipeline that converts portrait photos into cartoonized 3D models ready for FDM 3D printing. The system uses AI for both cartoonization (SDXL via Replicate) and 3D generation (Meshy.ai), with automatic mesh optimization for print quality.

**Pipeline:** Photo → Face Detection → Pixar Cartoonization → 3D Model Generation → Mesh Optimization → STL Export

**Target Printers:** Creality Ender 3 V2, BIQU B1

## Features

- **Automatic face detection** - Validates uploaded photos before processing
- **Pixar-style cartoonization** - AI-powered transformation to animated character style
- **Image-to-3D conversion** - Generates full 3D models from 2D cartoons
- **Print-ready optimization** - Automatic mesh repair, scaling, and validation
- **Live progress tracking** - Real-time updates during the 3-5 minute process
- **3D preview** - View and rotate your model before downloading
- **Multi-format export** - GLB for preview, STL for printing

## Quick Start

### Prerequisites

- Docker & Docker Compose
- API Keys:
  - [Replicate](https://replicate.com) account with API token
  - [Meshy.ai](https://meshy.ai) account with API key

### Setup

1. **Clone or navigate to the project:**
   ```bash
   cd avatar-poc
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys:
   # REPLICATE_API_TOKEN=your_token
   # MESHY_API_KEY=your_key
   ```

3. **Build and start services:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - Frontend (Streamlit UI): http://localhost:8501
   - Backend (FastAPI): http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Usage

1. Open http://localhost:8501 in your browser
2. Upload a clear, front-facing portrait photo (JPG/PNG, max 10MB)
3. Wait for face detection to validate the image (~5 seconds)
4. Watch the processing pipeline:
   - Cartoonization: ~30-60 seconds
   - 3D Generation: ~2-3 minutes
   - Mesh Optimization: ~10 seconds
5. Preview your 3D model in the browser
6. Download the STL file
7. Load into your slicer (Cura, PrusaSlicer, etc.)
8. Print!

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │  Upload photos, view progress, download STL
│  (port 8501)    │
└────────┬────────┘
         │
         ↓ HTTP
┌─────────────────┐
│  FastAPI Backend│  Process images, orchestrate AI services
│  (port 8000)    │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  Processing Pipeline                     │
│  1. Face Detection (MediaPipe)          │
│  2. Cartoonization (Replicate SDXL)     │
│  3. 3D Generation (Meshy.ai)            │
│  4. Mesh Optimization (trimesh/PyMeshLab)│
└─────────────────────────────────────────┘
```

## API Endpoints

- `POST /upload` - Upload photo and start processing
- `GET /status/{job_id}` - Get processing status
- `GET /preview/{job_id}` - Get GLB file for preview
- `GET /download/{job_id}/stl` - Download optimized STL
- `GET /docs` - Interactive API documentation

## Project Structure

```
avatar-poc/
├── backend/
│   ├── services/
│   │   ├── face_detector.py      # MediaPipe face detection
│   │   ├── cartoonizer.py        # Replicate API integration
│   │   ├── three_d_generator.py  # Meshy.ai API integration
│   │   └── mesh_optimizer.py     # 3D mesh processing
│   ├── utils/
│   │   ├── printer_profiles.py   # Printer configurations
│   │   └── validators.py         # Input validation
│   ├── pipeline.py               # Processing orchestrator
│   ├── main.py                   # FastAPI application
│   └── Dockerfile
├── frontend/
│   ├── app.py                    # Streamlit interface
│   └── Dockerfile
├── printer-profiles/
│   ├── ender3v2.json            # Ender 3 V2 settings
│   └── biqu_b1.json             # BIQU B1 settings
├── output/                       # Generated files (auto-created)
│   ├── uploads/
│   ├── cartoonized/
│   ├── models_3d/
│   └── stl_files/
└── docker-compose.yml
```

## Configuration

### Environment Variables

See `.env.example` for all configuration options. Key settings:

- `DEFAULT_TARGET_HEIGHT` - Avatar height in mm (default: 80mm = 8cm)
- `DEFAULT_PRINTER_PROFILE` - Choose `ender3v2` or `biqu_b1`
- `*_TIMEOUT` - Adjust timeouts for each processing stage

### Printer Profiles

Customize printer settings in `printer-profiles/*.json`:
- Bed size
- Build volume constraints
- Layer height recommendations
- Support settings

## Troubleshooting

**Face not detected:**
- Use a clear, front-facing portrait
- Ensure good lighting
- Avoid side profiles or multiple people

**3D generation timeout:**
- Meshy.ai can take 3-5 minutes during peak times
- Check API status at https://meshy.ai/status

**Mesh errors in slicer:**
- The mesh optimizer attempts automatic repair
- If issues persist, manually fix in Blender or Meshmixer

**Slow processing:**
- Replicate queue times vary by demand
- Consider upgrading to priority access

## Testing Checklist

- [ ] Face detection works on clear portraits
- [ ] Cartoonization preserves likeness
- [ ] 3D model has recognizable features
- [ ] STL loads in slicer without errors
- [ ] Model is approximately 8cm tall
- [ ] Print completes successfully
- [ ] Physical print is recognizable

## Cost Estimate

Per avatar generation:
- Replicate (cartoonization): ~$0.02
- Meshy.ai (3D generation): ~$0.15
- **Total: ~$0.17 per avatar**

For 10 test avatars: ~$1.70

## Next Steps

After validating the POC works:

1. Add accessories system (hats, glasses, etc.)
2. Build production web UI (Next.js)
3. Add user authentication
4. Integrate payment system (Stripe)
5. Deploy to production (Vercel + Railway)
6. Optimize for scale and cost

## Support

For issues with:
- **This POC:** Check logs with `docker-compose logs -f`
- **Replicate API:** https://replicate.com/docs
- **Meshy.ai API:** https://docs.meshy.ai

## License

Proof of Concept - Internal Use Only

---

Built with ❤️ and AI
