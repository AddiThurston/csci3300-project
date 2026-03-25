# csci3300-project

## Currently hosted on addi.ddns.net

# InSiteful Mind

A web application for users to track and reflect on their mental health day-to-day. The app analyzes key emotional words to chart mental health over time and provides AI-powered, personalized advice based on journal entries, check-ins, and mood reflections.

**Team:** David Pan, Kysen Krishnaswamy, Addison Thurston, Prabhnoor Singh

---

## Overview

Unlike apps that only log mood or offer one-time screenings, this app focuses on **improvement and maintenance** of mental health through:

- **Daily journaling** — Process experiences and feelings in writing
- **Short check-ins** — Quick questionnaires for emotional snapshots
- **Three-word reflections** — Fast mood capture when time is limited
- **Long-term trends** — Charts and insights over weeks and months
- **AI advice** — Personalized suggestions based on entries and trends

---

## Features

### Journal
Users can write about difficult or meaningful experiences to process feelings and notice emotional patterns. Entries are saved and can be reviewed. For severe content, the app suggests reaching out to trusted people or professional support.

### Daily Check-In
A short questionnaire records how the user is feeling. Users can skip questions or days. Responses are used to provide tailored feedback.

### Three-Word Reflection
For users short on time: a slider sets general mood (positive to negative), then three words are selected to describe the current emotional state. Users can add custom words or skip when needed.

### Long-Term Tracking
A trends section shows charts of mood, stress, and emotional keywords over time. Patterns help users understand and maintain their mental health. When data is limited, the app still charts what is available.

---

## Getting Started

### Prerequisites
- Python 3.x
- Upstash Redis account

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/AddiThurston/csci3300-project.git
   cd csci3300-project
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Create a `.env` file with:
   ```
   UPSTASH_REDIS_REST_URL=your_redis_url
   UPSTASH_REDIS_REST_TOKEN=your_redis_token
   PORT=3000
   ```

5. **Run the server**
   ```bash
   python server.py
   ```

6. Open `http://localhost:3000` in your browser.

---

## Project Status


| Feature                        | Status      |
| ------------------------------ | ----------- |
| Journal (create, view, delete) | Implemented |
| Google Sign-In                 | In-Progress |
| Daily Check-In                 | Planned     |
| Three-Word Reflection          | In-Progress |
| Long-Term Trends               | Planned     |
| AI Integration (Gemini)        | Planned     |


---

