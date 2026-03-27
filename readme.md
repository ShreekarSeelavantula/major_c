# Prep Genie — Project Context (paste this at the start of every new chat)

## Project Overview
AI-Based Personalized Study Plan Generator
Full name: "A Dynamic Learner State Estimation Framework for Adaptive Study Plan Generation"
Stack: FastAPI + Jinja2 + MongoDB + GridFS + Groq API (llama-3.1-8b-instant) + JSON file storage

---

## Project Structure
```
app/
  core/
    adaptive_plan_generator.py   ← priority engine, daily scheduling, fatigue logic
    learner_initializer.py       ← sets up fresh learner state per topic
    learner_updater.py           ← updates familiarity/speed/consistency after each day
    retention_scheduler.py       ← marks topics for revision based on decay
  models/
    learner_state.py             ← Pydantic model for per-topic state
    structured_syllabus.py       ← Unit + Topic models
    syllabus_model.py            ← MongoDB document model
    user_model.py                ← UserCreate, UserLogin
  routes/
    auth.py                      ← signup, login, logout
    diagnostic.py                ← rule-based question generation (legacy)
    familiarity_test.py          ← initial test, micro test, self-rating, submit, result
    pages.py                     ← dashboard, profile, plans pages
    plan.py                      ← configure, generate, view plan
    planner.py                   ← direct JSON planner endpoint
    progress.py                  ← today's tasks, submit progress
    syllabus.py                  ← upload, preview, validate, structure
  services/
    bulk_question_generator.py   ← ONE bulk Groq API call → all questions stored to file
    complexity_engine.py         ← Bloom's taxonomy + structural scoring
    diagnostic_service.py        ← legacy rule-based MCQ generator
    familiarity_updater.py       ← smooth familiarity update with forgetting curve
    ocr_service.py               ← pdf2image + pytesseract fallback
    plan_orchestrator.py         ← central coordinator: syllabus → topics → plan
    planner_service.py           ← wraps adaptive_plan_generator
    revision_scheduler.py        ← picks topics due for revision
    subject_detector.py          ← regex-based course code + title extractor
    syllabus_parser.py           ← PyMuPDF text extraction
    syllabus_pipeline.py         ← extract topics → complexity → time estimate
    syllabus_structurer.py       ← regex parser: units → topics → subtopics
    syllabus_to_plan_converter.py← flat topic list from structured syllabus
    syllabus_validator.py        ← is this actually a syllabus?
    test_evaluator.py            ← scores MCQ answers
    test_sampler.py              ← unit-aware topic sampling for micro tests
    time_estimator.py            ← hours per topic based on complexity score
    topic_analyzer.py            ← Bloom verb + concept density + dependency
    topic_cleaner.py             ← Groq API call to clean extracted topic names
    topic_complexity_engine.py   ← full complexity dict per topic
    user_profile.py              ← loads study_preference + year for plan personalization
  storage/
    learner_store.py             ← JSON file CRUD for learner state + mark_unit_as_tested
    plan_store.py                ← JSON file CRUD for study plans
  templates/                     ← Jinja2 HTML templates (Bootstrap 5)
  static/                        ← CSS, JS, images
  database.py                    ← MongoDB client, GridFS, collections
  main.py                        ← FastAPI app, middleware, routers, error handlers
data/
  learners/                      ← {user_id}.json per user
  plans/                         ← {user_id}.json per user
  question_banks/                ← {syllabus_id}.json per syllabus
```

---

## Key Data Flows

### Syllabus Upload Flow
Upload PDF/image → GridFS storage → PyMuPDF extraction → OCR fallback if <50 words
→ syllabus_collection (MongoDB) → preview page → validate → detect subjects
→ select subject → structure_syllabus() → evaluate_topic() complexity
→ TopicCleaner (Groq) → save structured_syllabus → redirect preview

### Familiarity Assessment Flow
Click "Take Familiarity Test" → bulk_question_generator builds bank (ONE Groq API call)
→ Unit-1 diagnostic test (1 question per topic, ~20 questions)
→ result page → self-rating for Units 2-5 (0/0.25/0.5/0.75/1.0 scale)
→ build_adaptive_plan() called → plan saved → redirect to plan view
→ Every visit to Today's page: check tested_units → show micro test popup if needed
→ Micro test popup: slides from right → blooms to center → one question at a time
→ Submit via fetch() to /familiarity/micro/popup/submit (JSON, no page reload)
→ familiarity updated → plan regenerated → result shown inside popup → toast

### Plan Generation Flow
structured_syllabus → flat topic list → load/init learner_state
→ get_user_profile() (study_preference + year)
→ topic_order = hard_first/easy_first/priority
→ year_pace_multiplier = 1.2 (yr1-2) or 0.9 (yr3-4)
→ generate_adaptive_plan() → priority engine per topic
→ schedule dict {day: [tasks]} → save to data/plans/

### Daily Progress Flow
Today's page → user checks done tasks + enters actual hours
→ POST /progress/submit → update_learner_state() → save
→ build_adaptive_plan() regenerates plan → redirect back to Today

---

## Learner State Structure (per user JSON)
```json
{
  "topic_states": {
    "Topic Name": {
      "familiarity": 0.0-1.0,
      "confidence": 0.0-1.0,
      "retention": 0.0-1.0,
      "attempts": 0,
      "last_studied": "YYYY-MM-DD or null",
      "revision_due": false,
      "complexity": "Easy/Medium/Hard",
      "self_rated": true/false
    }
  },
  "learning_speed": 0.7-1.5,
  "consistency": 0.5-1.0,
  "tested_units": [1, 2],
  "history": [{"date": "...", "actual_hours": 0, "expected_hours": 0}]
}
```

---

## Bugs Fixed in This Session
1. Plan stuck on one topic — added days_scheduled tracker in adaptive_plan_generator.py
2. learning_speed degrading too fast — clamped to min 0.7, max 1.5
3. Micro test popup — replaced simple setTimeout with slide-in notification → bloom animation
4. Test result page — now shows correct CTA buttons based on test_type (initial vs micro)
5. Unit-aware micro test sampling — test_sampler.py returns (topics, unit_number) tuple

---

## Bugs Still Pending
1. Sidebar buttons (Dynamic Plan, Full Plan) redirect to home if no plan exists
   → Need graceful empty state page instead of crash redirect
2. Two incompatible date formats for retention decay
   → learner_updater.py uses "YYYY-MM-DD" string
   → familiarity_updater.py uses Unix timestamp (time.time())
   → These need to be unified to one format
3. Generic topic names ("Definition", "Types", "Introduction", "Labor", "Emotional")
   → topic_cleaner.py not filtering single generic words
   → Need post-clean filter: reject single generic words under 12 chars
4. MongoDB credentials hardcoded in database.py
   → Move to .env file

---

## AI Usage in This Project
- Groq API (llama-3.1-8b-instant) used for:
  1. bulk_question_generator.py — ONE call per syllabus, generates all MCQs
  2. topic_cleaner.py — ONE call per syllabus, cleans extracted topic names
- NO AI used for plan generation (pure rule-based algorithm)
- This distinction is important for academic journal/viva

---

## Current Task
[REPLACE THIS WITH WHAT YOU WANT TO WORK ON]