# PeerShare: P2P File Sharing Application

A high-performance Peer-to-Peer file sharing application built with a Python TCP & FastAPI backend and a dark-themed React + Vite + Tailwind CSS frontend.

---

## 📌 Implementation Roadmap & Completion Checklist

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | **Audit & Core TCP Transfer Protocol** (Framing, SHA-256 integrity, safe filenames, overwrite avoidance, connection cleanup) | ✅ **Completed** |
| **Phase 7** | **React UI Implementation** (Dark-themed dashboard, Send/Receive, WebSockets, REST API, SQLite history) | ✅ **Completed** |
| **Phase 2** | **Tracker-Based Peer Discovery** (Peer registration, file announcements, healthchecks, file search) | ⏳ Next |
| **Phase 3** | **File Chunking & Resumable Transfers** (Logical chunk manifests, chunk integrity, resume interrupted downloads) | ⏳ Pending |
| **Phase 4** | **Multiple Peers & Swarming** (Concurrent multi-peer downloads, peer scheduling, chunk distribution) | ⏳ Pending |

---

## 🏗️ Architecture

```
PeerShare/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server & TCP daemon lifecycle
│   │   ├── config.py            # Peer configuration & paths
│   │   ├── api/
│   │   │   └── routes.py        # REST endpoints & WebSockets
│   │   ├── networking/
│   │   │   ├── protocol.py      # Frame protocol, SHA-256 & path sanitizers
│   │   │   ├── sender.py        # FileSender TCP client with callbacks
│   │   │   └── receiver.py      # FileReceiver TCP server with atomic .part commit
│   │   ├── database/
│   │   │   └── db.py            # SQLite transfer history
│   │   └── transfer/
│   │       └── manager.py       # TransferManager & background daemon
│   ├── tests/
│   │   ├── test_networking.py   # Protocol unit tests (small, empty, binary, integrity, cleanup)
│   │   └── test_api_integration.py # E2E API + TCP integration tests
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Sidebar.tsx
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── SendFilesPage.tsx
│   │   │   ├── ReceiveFilesPage.tsx
│   │   │   ├── PeersPage.tsx
│   │   │   ├── SharedFilesPage.tsx
│   │   │   ├── HistoryPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── App.tsx
│   └── package.json
│
├── downloads/                   # Received files
├── shared/                      # Seeding files
├── sender.py                    # Root CLI sender (backward compatible)
├── receiver.py                  # Root CLI receiver (backward compatible)
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
pip install -r backend/requirements.txt
```

Run backend server (starts FastAPI on port 8000 and TCP daemon on port 5000):
```bash
python backend/app/main.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4. Running Automated Tests
```bash
python -m pytest backend/tests/
```
All 8 tests (unit and integration) will execute and verify SHA-256 integrity, connection cleanup, safe filenames, and API-driven transfers.
