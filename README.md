# Web Penetration Testing App

This application provides a simple web interface to initiate basic penetration tests against a target website URL. It uses a Next.js frontend and a Python (FastAPI) backend.

**Disclaimer:** This tool is for educational purposes only. Running penetration tests against websites without explicit permission from the owner is illegal and unethical. Ensure you have proper authorization before testing any website. The implemented tests are basic examples and not exhaustive.

## Features

*   Enter a target URL to scan.
*   Initiates a series of asynchronous penetration tests (currently includes SSL/TLS check, others simulated).
*   Displays the status (Pending, In Progress, Completed) and results (Passed, Vulnerable, Info) of each test.
*   Stores scan history and results in an SQLite database.
*   (Planned) Downloadable PDF summary report.

## Tech Stack

*   **Frontend:** Next.js (React), TypeScript, Tailwind CSS, Axios
*   **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy, AIOHTTP, Requests, ReportLab (for PDF generation)
*   **Database:** SQLite (via AIOSqlite)

## Prerequisites

*   Node.js (v18 or later recommended)
*   npm (usually comes with Node.js)
*   Python (v3.10 or later recommended)
*   `pip` (Python package installer)
*   `venv` (Python virtual environment tool, usually included with Python)

## Setup Instructions

1.  **Clone the Repository (if applicable):**
    ```bash
    git clone <repository-url>
    cd pen-test-app
    ```

2.  **Backend Setup:**
    *   Navigate to the backend directory:
        ```bash
        cd backend
        ```
    *   Create a Python virtual environment:
        ```bash
        python3 -m venv venv
        ```
    *   Activate the virtual environment:
        *   macOS/Linux: `source venv/bin/activate`
        *   Windows: `.\venv\Scripts\activate`
    *   Install Python dependencies:
        ```bash
        pip install -r requirements.txt 
        # (Note: requirements.txt needs to be generated first if not present)
        # Or install manually (as done during development):
        # pip install fastapi uvicorn[standard] requests beautifulsoup4 reportlab sqlalchemy python-dotenv aiohttp aiosqlite
        ```
    *   (Optional) Create a `.env` file if it doesn't exist, copying `.env.example` if available, or create it with the following content:
        ```env
        DATABASE_URL="sqlite+aiosqlite:///./pentest_results.db"
        ```

3.  **Frontend Setup:**
    *   Navigate to the frontend directory (from the project root `pen-test-app`):
        ```bash
        cd ../frontend 
        # Or just `cd frontend` if you are in the project root
        ```
    *   Install Node.js dependencies:
        ```bash
        npm install
        ```

## Running the Application

You need to run both the backend and frontend servers simultaneously.

1.  **Run the Backend Server:**
    *   Open a terminal in the `pen-test-app/backend` directory.
    *   Activate the virtual environment (`source venv/bin/activate` or `.\venv\Scripts\activate`).
    *   Start the FastAPI server:
        ```bash
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
        ```
    *   The backend API will be available at `http://localhost:8000`. The database (`pentest_results.db`) will be created automatically on first run.

2.  **Run the Frontend Server:**
    *   Open a *separate* terminal in the `pen-test-app/frontend` directory.
    *   Start the Next.js development server:
        ```bash
        npm run dev
        ```
    *   The frontend application will be available at `http://localhost:3000`.

## Using the Application

1.  Open your web browser and navigate to `http://localhost:3000`.
2.  Enter the full URL of the website you want to test (including `http://` or `https://`) in the input field.
3.  Click the "Start Scan" button.
4.  The application will display the list of tests being performed. The status icons will update as the tests run:
    *   ⏳: Pending
    *   ⚙️: In Progress
    *   ✅: Completed - Passed
    *   ❌: Completed - Vulnerable
    *   ℹ️: Completed - Informational
    *   ⚠️: Failed/Error during test execution
5.  Once all tests are complete, the overall scan status will update, and a "Download PDF Report" button will appear (Note: PDF generation is currently a placeholder).

## Development Notes

*   The backend uses `asyncio` and `BackgroundTasks` to run tests concurrently without blocking the API.
*   Database models are defined in `backend/models.py` using SQLAlchemy.
*   API endpoints are defined in `backend/main.py`.
*   Frontend components are in `frontend/src/app/`. The main page is `page.tsx`.
*   Frontend communicates with the backend API (defaulting to `http://localhost:8000`).
