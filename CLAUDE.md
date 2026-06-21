# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

同济大学软件管理与经济课程项目 — an Electron desktop application for detecting plagiarism in examination papers. The system analyzes .docx exam papers using OCR, NLP, and LLM-based similarity checking, then generates annotated reports.

## Project Structure

```
core/          FastAPI backend (Python)
front/         Electron + Vue 3 + Vite desktop app
```

The **backend** (`core/`) is a FastAPI server (port 8000) that handles:
- DOCX → Markdown conversion (pypandoc + LibreOffice)
- Image OCR via Pix2Text (`ocr_module.py`)
- LLM-based exam segmentation, tag extraction, format validation, and similarity analysis via OpenAI-compatible APIs (`llm_service.py`)
- Local NLP similarity using `sentence-transformers/distiluse-base-multilingual-cased-v1` (`main.py`)
- Annotated DOCX report generation (`/generate-report` endpoint)

The **frontend** (`front/`) is an Electron app using Vue 3, Vue Router, Tailwind CSS, and Vite. It communicates with the backend over HTTP (axios on `localhost:8000`) and persists application state locally via `lowdb` (JSON file at the Electron app root as `db.json`). IPC handlers in `main.js` manage courses, projects, documents, API configs, remote banks, users, colleges, reports, and similarity results.

## Commands

### Backend (core/)

```bash
# Install dependencies
pip install -r core/requirements.txt

# Run the FastAPI server
python core/main.py
# Starts on http://127.0.0.1:8000
```

The server requires:
- **LibreOffice Portable** directory at `core/LibreOfficePortable/` for DOCX↔PDF conversion
- **OCR models** at `core/models/` (Pix2Text, CnOCR, CnSTD)
- **NLP model** at `core/distiluse-base-multilingual-cased-v1/` for local similarity mode
- These are gitignored — deploy them separately.

### Frontend (front/)

```bash
cd front
npm install                      # Install dependencies
npm run dev                      # Vite dev server (hot-reload)
npm run build                    # Production build (Vite only)
npm run electron                 # Launch Electron against built dist/
npm run electron:dev             # Launch Electron (dev mode)
npm run preview                  # Preview production build
```

Electron loads from `VITE_DEV_SERVER_URL` in development, or `dist/index.html` in production.

### Linting

```bash
cd front
npx eslint src/                  # ESLint with basic js + vue config (eslint.config.mjs)
```

## Architecture Notes

### Backend API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /set-config` | Sets LLM base URL, model name, API key |
| `POST /analyze-exam` | Upload .docx, returns segmented blocks + questions |
| `POST /extract-tags` | Extracts question type, score, and 3 tags for a single question |
| `POST /check-similarity` | Compares two questions for duplicate content |
| `POST /validate-format` | Runs 9 predefined format checks on an exam paper |
| `POST /generate-report` | Generates annotated .docx with duplicate highlights and format check table |

All LLM calls use `instructor` for structured output via Pydantic models. The backend supports two similarity modes:
- **NLP mode**: Set model name to `"nlp"` — uses local `sentence-transformers` (no LLM needed)
- **LLM mode**: Any other model name — uses OpenAI-compatible API for tag checking + content similarity

### Frontend Data Flow

1. **Electron main process** (`main.js`) owns all data managers (CourseManager, ProjectManager, DocumentManager, etc.) backed by `lowdb` JSON file
2. **Preload script** (`preload.js`) exposes typed IPC APIs via `contextBridge` — `electronAPI`, `projectAPI`, `documentAPI`, `courseAPI`
3. **Vue renderer** calls these APIs, plus makes HTTP requests to the Python backend at `http://127.0.0.1:8000` for AI/OCR features

### Key Frontend Routes

- `/login` — Employee ID + password authentication
- `/menu` — Main navigation hub
- `/new-task` — Create plagiarism-check projects
- `/history` — Past project history
- `/question-bank` — Manage parsed question bank
- `/devide` — Exam paper segmentation view
- `/edit-exam` — Edit exam questions, tags, scores
- `/settings` — API configs, format checks, remote banks, user management
- `/remote-papers` — Fetch papers from remote MongoDB
- `/report` — View plagiarism check results
- `/profile` — User profile

### Database Schema (lowdb)

The `db.json` file stores: `courses`, `projects`, `documents`, `questions`, `documentProjects` (many-to-many join), `settings`, `apiConfigs`, `reports`, `similarityResults`, `formatChecks`, `users`, `colleges`, `remoteBanks`.

Default admin: employeeId `admin` / password `admin` (role 1 = super admin).

### External Dependencies

- **LibreOffice Portable** at `core/LibreOfficePortable/` — required for DOCX→PDF/PNG conversion
- **pypandoc** — wraps pandoc for DOCX→Markdown conversion
- **PyMuPDF (fitz)** — PDF text extraction for local format validation mode
- **Pix2Text** — OCR engine for Chinese/English/math formula recognition
- **sentence-transformers** — offline multilingual NLP similarity
- **instructor** — structured LLM output via Pydantic models
- **lowdb** — JSON-based local database for Electron app state
- **MongoDB driver** — remote paper bank fetching (connects to `examSystem` database)
