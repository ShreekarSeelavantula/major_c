# Prep Genie - Local Setup Guide

## Prerequisites
- **Python 3.8+** installed
- **MongoDB Atlas Account** (free tier available at https://www.mongodb.com/cloud/atlas)
- **Groq API Key** (free at https://console.groq.com)
- **Tesseract OCR** (for PDF text extraction)

---

## Step 1: Clone & Navigate to Project
```bash
git clone <your-repo-url>
cd major_c
```

---

## Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

---

## Step 3: Install Python Dependencies
```bash
pip install -r requirements.txt
```

---

## Step 4: Install System Dependencies (for OCR)

### **Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install libopenjp2-7-dev libjp2-dev libwebp-dev libtiff-dev
```

### **macOS:**
```bash
brew install tesseract
```

### **Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki
Or use: `choco install tesseract` (if using Chocolatey)

---

## Step 5: Configure Environment Variables
Create a `.env` file in the project root:
```env
# MongoDB Atlas Connection
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/study_planner?retryWrites=true&w=majority

# Database Name
DATABASE_NAME=study_planner

# Groq API Key (get from https://console.groq.com)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx

# Session Security (use a random string in production)
SESSION_SECRET=your-secret-key-here-change-in-production
```

### Getting Connection Strings:
1. **MongoDB Atlas URI:**
   - Go to https://www.mongodb.com/cloud/atlas
   - Create cluster → Database → Connect
   - Copy connection string

2. **Groq API Key:**
   - Go to https://console.groq.com
   - Create API key under "API Keys"

---

## Step 6: Run the Application
```bash
python -m uvicorn app.main:app --reload
```

The app will be available at: **http://localhost:8000**

---

## Project Structure Overview

```
major_c/
├── app/
│   ├── core/               # Adaptive learning algorithms
│   ├── models/             # Pydantic models & data structures
│   ├── routes/             # API endpoints
│   ├── services/           # Business logic
│   ├── storage/            # Data persistence
│   ├── templates/          # HTML templates (Jinja2)
│   ├── static/             # CSS, JS, images
│   ├── main.py             # FastAPI app initialization
│   └── database.py         # MongoDB connection
├── data/                   # Local JSON storage (learners, plans)
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
└── README.md              # Project documentation
```

---

## Key Features to Test

1. **Home Page:** http://localhost:8000/
2. **Sign Up:** http://localhost:8000/signup
3. **Login:** http://localhost:8000/login
4. **Dashboard:** http://localhost:8000/dashboard (after login)
5. **Upload Syllabus:** Upload PDF from dashboard
6. **Create Study Plan:** Generate adaptive study plan
7. **Track Progress:** Log daily study hours

---

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'passlib'`
```bash
pip install passlib --upgrade
```

### Error: `ModuleNotFoundError: No module named 'bson'`
```bash
# Remove conflicting bson package
pip uninstall bson -y

# Reinstall pymongo
pip install --upgrade pymongo
```

### MongoDB Connection Error
- Verify `MONGODB_URI` in `.env` file
- Check MongoDB Atlas cluster is active
- Whitelist your IP in MongoDB Atlas Network Access
- Verify username/password are correct (no special characters like @, !, etc.)

### Tesseract Not Found
- Ensure Tesseract is installed (run `tesseract --version`)
- On Windows, update `.env` with Tesseract path:
  ```env
  PYTESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
  ```

### API Key Issues
- Verify `GROQ_API_KEY` is correct from https://console.groq.com
- Check rate limits (free tier: 30 requests/min)

---

## Development Notes

- **Hot Reload:** Using `--reload` flag for auto-restart on code changes
- **Database:** Uses MongoDB Atlas for production, JSON files for local state storage
- **Frontend:** Jinja2 templates with Bootstrap 5 CSS
- **API:** RESTful endpoints with JSON request/response
- **Authentication:** Session-based authentication with password hashing

---

## Production Deployment

When deploying to production:
1. Generate a strong `SESSION_SECRET`
2. Set `DEBUG=False`
3. Use HTTPS
4. Update MongoDB connection to production cluster
5. Configure CORS if needed
6. Set up proper logging

