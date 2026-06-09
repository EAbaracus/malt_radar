# Malt Radar

Malt Radar is a personal whisky database and tasting notes application built with Flutter and Python (FastAPI). It allows users to search for whiskies, rate them according to their own 100-point reference system, and store their whiskies in a local library (along with prices and tasting notes).

## Features

- **Offline-First Architecture:** Ability to work offline thanks to the local SQLite (Drift) database.
- **Backend Integration and Live Web Scraping:** Instead of settling for a limited CSV dataset, the application performs "live web scraping" directly from massive sources like Distiller.com. It instantly reflects the newest and most accurate whiskies, along with up-to-date age and cask details, in the search results. (It also provides fallback data via CSV and Mock API providers.)
- **Personal Scoring System:** The ability to rate other whiskies based on a 100-point reference whisky of your choice.
- **Modern Interface:** Riverpod State Management and a modern dark theme design.
- **Web Support:** Fast web compilation support with Drift's native Wasm files.

## Project Structure

The project consists of two main folders:
1. `backend/`: The backend service written with Python and FastAPI. It aggregates data sources and responds to search requests.
2. `frontend/`: The mobile/web application written with Dart and Flutter.

---

## Installation and Running

You will need two terminal tabs to run the project locally.

### 1. Starting the Backend (Python API) Server

Python must be installed to run the backend.

```bash
# Navigate to the backend folder from the project directory
cd "malt radar/backend"

# Install the required dependencies (Required for the first time)
pip install -r requirements.txt

# Start the development server
python run.py
```
*(The server runs on http://localhost:8080 by default)*

### 2. Starting the Frontend (Flutter Application) Server

Open a separate terminal tab. Flutter must be installed and configured.

```bash
# Navigate to the frontend folder from the project directory
cd "malt radar/frontend"

# (Optional) Download packages
flutter pub get

# Launch the application on the Chrome browser
flutter run -d chrome --web-port 8888
```

Once the application compiles successfully, you can start using it in your browser at http://localhost:8888.
