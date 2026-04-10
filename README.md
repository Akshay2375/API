# College Chatbot API

This is a FastAPI-based API that serves as a backend connecting a natural language chatbot (using Google Gemini) to a PostgreSQL/SQLite database of Maharashtra engineering colleges, as well as providing an engine for predicting college admission cutoffs.

## Endpoints

### 1. Root Endpoint
A simple endpoint to welcome users and provide version and docs links.

**Endpoint:** `GET /`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/"
```

**Response (`200 OK`):**
```json
{
  "message": "Welcome to College Chatbot API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

### 2. Health Check
Verifies that the server is up and running.

**Endpoint:** `GET /health`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/health"
```

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### 3. Metadata Lookup
Retrieves a comprehensive list of all unique cities, divisions, and universities present in the database. Can be used for frontend filter dropdowns.

**Endpoint:** `GET /api/v1/metadata`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/metadata" -H "accept: application/json"
```

**Response (`200 OK`):**
```json
{
  "cities": [
    "Mumbai",
    "Nagpur",
    "Pune"
  ],
  "divisions": [
    "Mumbai Division",
    "Nagpur Division",
    "Pune Division"
  ],
  "universities": [
    "Mumbai University",
    "Rashtrasant Tukadoji Maharaj Nagpur University",
    "Savitribai Phule Pune University"
  ]
}
```

---

### 4. Fetch Eligible Cutoffs
Returns eligible cutoffs based on rigorous user filtering parameters including gender, category, city, division, course types, and automatically applies a +/- 10 threshold margin on passed percentiles.

**Endpoint:** `POST /api/v1/get-cutoffs`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/get-cutoffs" \
     -H "Content-Type: application/json" \
     -d '{
  "user_gender": "M",
  "user_category": "OPEN",
  "user_minority_list": [],
  "user_home_university": "Savitribai Phule Pune University",
  "division": ["Pune Division"],
  "city": ["Pune"],
  "percentile_cet": 85.5,
  "percentile_ai": 80.0,
  "is_tech": true,
  "is_civil": false,
  "is_mechanical": false,
  "is_electrical": false,
  "is_electronic": false,
  "is_other": false,
  "is_ews": false
}'
```

**Response (`200 OK`):**
```json
{
  "user_details": {
    "user_gender": "M",
    "user_category": "OPEN",
    "user_minority_list": [],
    "user_home_university": "Savitribai Phule Pune University",
    "division": [
      "Pune Division"
    ],
    "city": [
      "Pune"
    ],
    "percentile_cet": 85.5,
    "percentile_ai": 80.0,
    "is_tech": true,
    "is_civil": false,
    "is_mechanical": false,
    "is_electrical": false,
    "is_electronic": false,
    "is_other": false,
    "is_ews": false,
    "calculated_bounds": {
      "min_percentile_cet": 75.5,
      "max_percentile_cet": 95.5,
      "min_percentile_ai": 70.0,
      "max_percentile_ai": 90.0
    }
  },
  "count": 1,
  "results": [
    {
      "college_code": "6006",
      "college_name": "College of Engineering, Pune",
      "course_name": "Computer Engineering",
      "city": "Pune",
      "division": "Pune Division",
      "home_university": "Savitribai Phule Pune University",
      "reservation_category": "OPEN",
      "gender": "M",
      "sorting_value": 88.5
    }
  ]
}
```

---

### 5. Chatbot Interface
Parses natural language input about Maharashtra engineering colleges into SQL, retrieves context from the database, and returns a human-readable summarized response.

**Endpoint:** `POST /api/v1/chat`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{
  "query": "Best colleges in Nagpur for Computer Engineering under 80 percentile"
}'
```

**Response (`200 OK`):**
```json
{
  "query": "Best colleges in Nagpur for Computer Engineering under 80 percentile",
  "sql_generated": "SELECT college_name FROM colleges WHERE city = 'Nagpur' AND course_name LIKE '%Computer%' AND exam = 'CET' AND cutoff_percentile <= 80 ORDER BY cutoff_percentile DESC LIMIT 5",
  "answer": "Based on the records, here are some of the best colleges in Nagpur for Computer Engineering under 80 percentile: ...",
  "row_count": 5
}
```

**Common Error Responses for Chat:**
* `400 Bad Request`: Invalid or blank query.
* `404 Not Found`: Execution successful, but query returned 0 rows.
* `503 Service Unavailable`: AI failed to generate correct SQL or Database rejected the query.
