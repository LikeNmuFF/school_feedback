# ClassVoice – Anonymous Teacher Feedback App

A Flask web app for anonymous classroom feedback.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000

## Features
- Submit anonymous feedback with rating, category, and message
- View all feedback with stats (count, avg rating, positive responses)
- Filter feedback by category
- Data stored in feedback.json (no database needed)

## Project Structure
```
feedback_app/
├── app.py              # Flask routes & logic
├── requirements.txt
├── feedback.json       # Auto-created on first submission
└── templates/
    ├── base.html       # Shared nav & layout
    ├── index.html      # Submission form
    └── feedback.html   # View all feedback
```
