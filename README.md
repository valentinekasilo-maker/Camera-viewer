<p align="center">
  <img align="center" alt="logo" src="docs/static/img/branding/frigate.png">
</p>

# Frigate NVR™ with ANDRO-Vision Gemini Multimodal Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.13+](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/)
[![React: 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![Gemini: 3.6 Flash](https://img.shields.io/badge/Gemini-3.6%20Flash-purple.svg)](https://deepmind.google/technologies/gemini/)

A complete, local NVR designed for Home Assistant and standalone enterprise CCTV monitoring, featuring the **ANDRO-Vision Camera Intelligence Engine** powered by **Google Gemini 3.6 Flash** for multimodal camera reasoning, natural voice interaction, live frame visual analysis, and zero-hallucination multi-camera tracking.

---

## 🌟 Key Features

### 1. 🧠 ANDRO-Vision Camera Intelligence Engine
- **Multi-Stage Question Understanding**: Parses natural language inquiries, resolves temporal windows (`now`, `today`, `last 10 minutes`, `before gate opened`), and resolves conversational pronouns (`it`, `he`, `she`, `they`, `both`).
- **Context Planner & Tool Retrieval**: 12 internal retrieval tools querying camera state, event history, vehicle status, gate state machines, and person tracks.
- **Grounded Spatiotemporal Reasoner**: Reconstructs multi-camera spatial movements across all 8 cameras without keyword reliance.
- **Strict Zero-Hallucination Policy**: Distinguishes between confirmed sightings and missing evidence, refusing to fabricate events when camera evidence is unavailable.

### 2. ✨ Google Gemini 3.6 Flash Multimodal Integration
- **Multimodal Live Frame Inspector**: Inspects raw camera frames using `gemini-3.6-flash` for fine-grained visual questions (e.g. TV screen status, clothes on a clothesline, delivery package presence).
- **One-Click Vision Presets**: Instant analysis for TV screens, clotheslines, parking counts, gate obstruction, and deep security audits.
- **Collapsible Reasoning Trace**: Complete developer diagnostics including detected intent, resolved subject entities, tools queried, confidence score, and latency.

### 3. 🎙️ Natural Voice Interaction (STT & TTS)
- **Voice Speech-to-Text (STT)**: Direct microphone button in the query bar using the Web Speech API (`SpeechRecognition`).
- **Natural Voice Synthesis (TTS)**: Reads answers out loud with pleasant speech synthesis and provides an **Auto-Voice** mode for hands-free operations.

### 4. 📹 Real-Time NVR & Multi-Camera Management
- **Low-Overhead Object Detection**: Hardware-accelerated object detection via OpenCV, TensorFlow, ONNX, OpenVINO, Coral TPU, and TensorRT.
- **Live Video Streaming**: WebRTC, MSE, and RTSP re-streaming powered by go2rtc.
- **24/7 & Event Recording**: Smart retention rules based on detected objects, zones, and review segments.
- **Home Assistant Integration**: Seamless real-time entity updates, WebSockets, and MQTT broadcasts.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   USER QUESTION / VOICE                  │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│              QUESTION UNDERSTANDING ENGINE               │
│  - Intent & Entity Extraction (8 Camera Scopes)          │
│  - Rolling Multi-Turn Pronoun & Context Resolution       │
│  - Time Window Parsing (seconds / relative / absolute)   │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                     CONTEXT PLANNER                      │
│  - Targeted Tool Selection (12 Internal Tools)           │
│  - Bounded Multi-Camera Sighting & Event Retrieval       │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                   GROUNDED REASONER                      │
│  - Level 1: Local Spatiotemporal Multi-Camera Reasoner   │
│  - Level 2: Google Gemini 3.6 Flash Deep Reasoning       │
│  - Multimodal Vision: Gemini Frame Inspector             │
│  - Strict Zero-Hallucination Evidence Verification       │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│             NATURAL ANSWER + VOICE SYNTHESIS             │
│  - Formatted Text Answer with Camera Citations           │
│  - Collapsible Diagnostic Reasoning Trace                │
│  - Attached Visual Snapshot Preview                      │
└──────────────────────────────────────────────────────────┘
```

---

## 🗺️ Semantic Camera Map (Default 8-Camera Topology)

| Camera ID | Location | Primary Semantic Scope |
|---|---|---|
| **Camera 1** | Control Room | Network equipment, Raspberry Pi NVR, workstation |
| **Camera 2** | Dining | Television screen status, dining table area |
| **Camera 3** | Backyard | Garden, clothesline, lawn (plant wind motion suppressed) |
| **Camera 4** | Veranda | Covered patio, play area, exterior seating |
| **Camera 5** | Dining / Kitchen Island | Kitchen island, small kitchen entrance, cabinets |
| **Camera 6** | Entrance | Front entrance door, front walkway, porch steps |
| **Camera 7** | Gate / Parking | Motorized gate state, driveway, 2-car baseline parking |
| **Camera 8** | Small Kitchen | Secondary kitchen, utility sink, rear access |

---

## 🚀 Quick Start & Development

### Prerequisites
- Python 3.13+
- Node.js 18+ and npm
- (Optional) Google Gemini API Key configured in your environment

### 1. Environment Setup
```powershell
# Set Gemini API Key (optional, built-in key pre-configured)
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

### 2. Start Backend Server
```powershell
# Starts the FastAPI Backend, Intelligence Engine, and Go2RTC
python run_server.py
```
*Backend API available at `http://127.0.0.1:5000/`*

### 3. Start Frontend UI
```powershell
cd web
npm install
npm run dev
```
*Web Application available at `http://localhost:5173/`*

---

## 🧪 Running Automated Tests

Run the complete Python camera intelligence and reasoning test suite:

```powershell
python -u -m unittest frigate.test.test_camera_intelligence_v2 frigate.test.test_camera_intelligence_advanced frigate.test.test_camera_intelligence_scenarios
```

Build the web frontend production bundle:

```powershell
cd web
npm run build
```

---

## 📡 Key Intelligence API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/intelligence/ask` | Natural language multi-camera conversational Q&A |
| `POST` | `/api/intelligence/inspect-camera` | Gemini Multimodal Vision analysis on live frame |
| `GET` | `/api/intelligence/cameras/{camera_id}/snapshot` | Serve the latest live snapshot image for a camera |
| `GET` | `/api/intelligence/models` | List local model tiers, quantizations, and telemetry |
| `POST` | `/api/intelligence/models/switch` | Switch active local specialist model tier |
| `GET` | `/api/intelligence/semantic-feed` | Stream real-time semantic event understandings |
| `GET` | `/api/intelligence/gate` | Query gate status, transition history, and certainty |
| `GET` | `/api/intelligence/vehicles` | Query 2-car parking baseline status and detections |
| `GET` | `/api/semantic/cameras` | Retrieve all 8 camera semantic descriptions and metadata |
| `PUT` | `/api/semantic/cameras/{camera_id}` | Update semantic description for a specific camera |

---

## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

The "Frigate" name and Frigate logo are trademarks of Frigate, Inc. and are subject to the [Trademark Policy](TRADEMARK.md).

---

**Copyright © 2026 Frigate, Inc. & ANDRO-Vision**
