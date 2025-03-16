# Samarth - AI-Powered Job Matching Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.0+-green.svg)](https://fastapi.tiangolo.com/)

> Intelligently connecting talent with opportunity using advanced AI.

Samarth is an AI-powered job matching platform developed for the Execute 4.0 Hackathon at DTU (Delhi Technical University). The platform uses advanced semantic matching algorithms to connect job seekers with the right opportunities and provides actionable feedback to improve application success rates.

![Job Matching Platform](https://via.placeholder.com/1200x400?text=AI-Powered+Job+Matching+Platform)

## Features

### For Job Seekers
- Resume upload and AI-powered analysis
- Personalized job recommendations
- Detailed match analysis with job postings
- Resume improvement suggestions
- Application tracking

### For Recruiters
- Intelligent job posting creation
- Automatic candidate ranking and filtering
- In-depth match analytics
- Market analysis for skill trends
- Candidate pipeline management

## Quick Start with Docker

The simplest way to run the application is using Docker:

```bash
# Clone the repository
git clone <your-repository-url>
cd job-matching-platform

# Build and start the Docker containers
docker-compose up -d

# Access the application at http://localhost:8000
```

## Manual Installation

### Prerequisites
- Python 3.9+
- SQLite (pre-installed on most systems)
- [Google API key for Gemini](https://ai.google.dev/) (for AI features)

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repository-url>
   cd job-matching-platform
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root with the following variables:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   SECRET_KEY=a_secret_key_for_jwt
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:8000`

## Project Structure

```
├── api.py                 # API endpoints
├── core/                  # Core configuration
│   ├── config.py          # Application settings
│   └── security.py        # Authentication logic
├── db/                    # Database
│   └── database.py        # Database connection
├── models.py              # Database models
├── schemas.py             # Data validation schemas
├── services.py            # Business logic services
├── ui.py                  # UI routes and handlers
├── main.py                # Application entry point
├── templates/             # Jinja2 templates
│   ├── auth/              # Authentication templates
│   ├── dashboard/         # Dashboard templates
│   ├── resumes/           # Resume templates
│   ├── jobs/              # Job templates
│   ├── applications/      # Application templates
│   ├── analysis/          # Analysis templates
│   └── base.html          # Base template
├── static/                # Static files
│   ├── css/               # CSS files
│   ├── js/                # JavaScript files
│   └── img/               # Images
├── uploads/               # Uploaded resume files
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
└── docker-compose.yml     # Docker Compose configuration
```

## API Documentation

The API documentation is available at `/docs` or `/redoc` when the application is running.

### Key Endpoints

- `/api/v1/auth/register` - Register a new user
- `/api/v1/auth/login` - Login and get access token
- `/api/v1/resumes` - Resume management
- `/api/v1/jobs` - Job management
- `/api/v1/applications` - Application management
- `/api/v1/match` - Match resumes to jobs
- `/api/v1/recommendations/{resume_id}` - Get job recommendations
- `/api/v1/market-analysis` - Get market analysis data

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Frontend**: Jinja2, TailwindCSS, DaisyUI, Alpine.js, Chart.js
- **AI**: Google Gemini Pro
- **Database**: SQLite (can be scaled to PostgreSQL)
- **Authentication**: JWT

## License

This project is licensed under the MIT License - see the LICENSE file for details.