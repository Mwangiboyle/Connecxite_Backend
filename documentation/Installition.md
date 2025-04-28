# Installation Guide

Follow the steps below to set up and run the project:

## Prerequisites
- Python 3.8 or higher installed on your system.
- `pip` package manager installed.

## Steps to Install and Run the Project

### 1. Clone the Repository
```bash
git clone https://github.com/Mwangiboyle/Connecxite_Backend.git
cd Connecxite_Backend
```

### 2. Create a Virtual Environment
Create a virtual environment to isolate project dependencies:
```bash
python -m venv venv
```

### 3. Activate the Virtual Environment
- On **Windows**:
    ```bash
    venv\Scripts\activate
    ```
- On **macOS/Linux**:
    ```bash
    source venv/bin/activate
    ```

### 4. Install Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 5. Run the FastAPI Project
Start the FastAPI server:
```bash
uvicorn main:app --reload
```

### 6. Access the Application
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### 7. API Documentation
FastAPI provides interactive API documentation:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Deactivating the Virtual Environment
When done, deactivate the virtual environment:
```bash
deactivate
```

You're all set!