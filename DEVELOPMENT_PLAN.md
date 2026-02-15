# Development Plan for Resume Parser Enhancements

This document outlines a plan for enhancing the resume parser to achieve ATS-grade matching, universal resume parsing, technical innovation, and a robust testing strategy.

### 1. Matching ATS-Grade Standards

The goal is to extract data with high accuracy and map it to a schema that mirrors what Applicant Tracking Systems (ATS) expect.

*   **Expand the Output Schema:** Evolve the `ParseResponse` towards a richer, nested JSON structure. This expanded schema should include granular fields common in ATS systems, such as:
    ```json
    {
      "personal_info": {
        "name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "123-456-7890",
        "location": "San Francisco, CA",
        "links": ["linkedin.com/in/johndoe", "github.com/johndoe"]
      },
      "summary": "Experienced software engineer...",
      "work_experience": [
        {
          "job_title": "Senior Software Engineer",
          "company": "Tech Solutions Inc.",
          "location": "San Jose, CA",
          "start_date": "2022-01-01",
          "end_date": "Present",
          "responsibilities": [
            "Led the development of...",
            "Mentored junior engineers..."
          ]
        }
      ],
      "education": [
        {
          "institution": "University of Example",
          "degree": "Master of Science in Computer Science",
          "end_date": "2021-12-31"
        }
      ],
      "skills": {
        "technical": ["Python", "FastAPI", "React", "PostgreSQL"],
        "soft": ["Team Leadership", "Agile Methodologies"]
      }
    }
    ```
*   **Incorporate a Job Description:**
    *   Modify the API to accept a job description alongside the resume.
    *   Use the LLM to perform a "gap analysis" by extracting required skills/experience from the job description and matching them against the resume content.
    *   Add a `match_score` to the output, quantifying the overlap between the resume and job description.

### 2. Achieving Universal Resume Parsing

This section focuses on handling the variety of resume formats and layouts.

*   **Support More File Types:**
    *   **Image-based formats (.jpeg, .png):** Integrate an Optical Character Recognition (OCR) engine like **Tesseract** (`pytesseract` library) to extract text from image-based resumes or scans.
    *   **Other text formats (.rtf, .txt, .doc):** Add libraries to handle these common but older formats.
*   **From Text Extraction to Layout-Aware Parsing:**
    *   Implement using a **multi-modal LLM (like Gemini Pro Vision)**. Instead of sending just the extracted text, send an *image* of each resume page. The model can then interpret the document's visual structure (font size, bolding, layout), significantly improving extraction accuracy for complex designs.

### 3. Technical Improvements & Innovations

*   **Asynchronous Processing:**
    *   Utilize a task queue (e.g., **Celery** with **Redis** or **RabbitMQ**) for parsing.
    *   Modify the `/parse` endpoint to immediately return a `task_id`.
    *   Create a `/results/{task_id}` endpoint for clients to poll for the completed parsing results.
*   **Feedback Loop:**
    *   Develop a mechanism for users to review and correct extracted JSON output.
    *   Collect these corrections to build a dataset for future model fine-tuning or rule refinement.
*   **Candidate Knowledge Graph (Advanced):**
    *   Explore storing extracted information in a graph database (e.g., Neo4j).
    *   Represent candidates, skills, companies, and education as interconnected nodes to enable deeper analysis (e.g., career progression, skill development).

### 4. Testing Strategy

A robust testing strategy is crucial for maintaining quality and enabling continuous development.

*   **Unit Tests:**
    *   Thoroughly test rule-based extractors with a wide range of inputs and edge cases.
    *   Use `unittest.mock` to patch external API calls (e.g., LLM) in `app/llm.py` to test prompt engineering and response handling logic independently.
*   **Integration Tests:**
    *   Test the `run_pipeline` function from file input to JSON output, with mocked external dependencies, to ensure correct flow and data handling.
*   **End-to-End & Regression Testing (The "Golden Dataset"):**
    *   **Create a "Golden Dataset":** Curate a diverse collection of 20-50 real resumes in various formats and layouts.
    *   **Create "Golden" JSON:** Manually create and store the expected, perfectly extracted JSON output for each resume in the dataset.
    *   **Automate Comparison:** Implement automated tests that:
        1.  Run each resume through the live `/parse` endpoint.
        2.  Compare the API's JSON output against the corresponding "golden" JSON.
        3.  Report any discrepancies, potentially using a "semantic diff" tool for JSON structures. This dataset will serve as a critical regression suite for all future changes.