# EHRMS Device Bridge Manager — Build & Usage Guide

## Overview

The **EHRMSBridge Manager** is a .NET 10 self-hosted web application that provides a graphical interface for installing, configuring, and running the Hikvision EHRMS Device Bridge.

It compiles to a **single executable** (`.exe` on Windows, binary on macOS/Linux) that launches a local web UI in your browser.

---

## Features

| Feature | Description |
|---|---|
| **Setup Wizard** | 6-step guided installation (Python check, venv, deps, config, DB, device) |
| **Settings Manager** | Edit all `.env` variables through a clean form interface |
| **Service Control** | Start/stop the Bridge and Streamlit Dashboard with one click |
| **Diagnostics** | System health checks, DB/device connection tests |
| **Log Viewer** | View bridge and dashboard logs with syntax highlighting |
| **User Guide** | Embedded documentation and troubleshooting |

---

## Prerequisites for Building

- [.NET 10 SDK](https://dotnet.microsoft.com/download) (you have `10.0.101`)

---

## Build Commands

### Windows `.exe` (deploy to Windows PCs)
```bash
cd installer/EHRMSBridge
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o ../publish/win-x64
```
Output: `installer/publish/win-x64/EHRMSBridge.exe`

### macOS (Apple Silicon)
```bash
dotnet publish -c Release -r osx-arm64 --self-contained true -p:PublishSingleFile=true -o ../publish/osx-arm64
```
Output: `installer/publish/osx-arm64/EHRMSBridge`

### macOS (Intel)
```bash
dotnet publish -c Release -r osx-x64 --self-contained true -p:PublishSingleFile=true -o ../publish/osx-x64
```

### Linux
```bash
dotnet publish -c Release -r linux-x64 --self-contained true -p:PublishSingleFile=true -o ../publish/linux-x64
```

---

## How to Deploy

1. **Copy the `publish/<platform>/` folder** to the target machine
2. Place it **inside the project root** (next to `hikvision_bridge.py`)
3. The folder structure should look like:
   ```
   your-project/
     hikvision_bridge.py
     dashboard.py
     requirements.txt
     .env
     ...
     publish/
       win-x64/
         EHRMSBridge.exe    ← double-click this
   ```
4. **Run the executable** — it opens `http://localhost:5199` in your browser automatically

> The app auto-detects the project root by looking for `hikvision_bridge.py` in parent directories.

---

## How to Use

### First Time Setup
1. Launch `EHRMSBridge.exe`
2. Browser opens to the **Home** dashboard
3. Click **Setup Wizard** and follow the 6 steps:
   - **Step 1** — Verifies Python 3.10+ is installed
   - **Step 2** — Creates `.venv` virtual environment
   - **Step 3** — Installs all pip dependencies
   - **Step 4** — Opens Settings to configure device/DB/webhook
   - **Step 5** — Tests MySQL database connection
   - **Step 6** — Tests Hikvision device connectivity

### Running the System
1. Go to **Run Services**
2. Click **Start** on Bridge and Dashboard
3. The Streamlit dashboard opens at `http://localhost:8502`

### Troubleshooting
1. Go to **Diagnostics** → **Run All Checks**
2. Use **Test Database** and **Test Device** buttons
3. Check **Logs** for error details

---

## Development

Run locally during development:
```bash
cd installer/EHRMSBridge
dotnet run
```

The app runs on `http://localhost:5199` and hot-reloads static files.

---

## Technical Details

- **Framework:** .NET 10 Minimal API + static HTML/CSS/JS
- **UI:** Single-page app with sidebar navigation, brand color `#790D0B`
- **Architecture:** Self-hosted Kestrel web server → REST API → Process management
- **Size:** ~99 MB (self-contained, no .NET runtime needed on target)
- **Port:** 5199 (manager UI), 8502 (Streamlit dashboard)
