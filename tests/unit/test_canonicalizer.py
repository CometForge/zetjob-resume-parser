from app.v2.canonicalizer import _heuristic_canonicalize, _parse_experience, _segment_sections


def test_segment_sections_detects_known_headers():
    text = """Summary\nBackend engineer\nExperience\nSenior Engineer | Acme | Jan 2020 - Present\nSkills\nPython, FastAPI\n"""
    sections, order = _segment_sections(text)
    assert order == ["summary", "experience", "skills"]
    assert "Backend engineer" in sections["summary"]
    assert any("Senior Engineer" in ln for ln in sections["experience"])


def test_parse_experience_extracts_dates_company_and_bullets():
    lines = [
        "Senior Backend Engineer | NovaStack, Jan 2021 - Present",
        "- Built 6 APIs and reduced latency by 30%",
        "Bengaluru, India",
    ]
    roles = _parse_experience(lines)
    assert len(roles) == 1
    role = roles[0]
    assert role.title == "Senior Backend Engineer"
    assert role.company == "NovaStack"
    assert role.start_date == "2021-01"
    assert role.is_current is True
    assert role.location == "Bengaluru, India"
    assert role.bullets and "reduced latency" in role.bullets[0]


def test_heuristic_canonicalize_builds_metadata_and_sections():
    text = """Summary
Product engineer focused on reliability.
Experience
Staff Engineer | Orbit Labs, Mar 2019 - Present
- Improved API uptime from 99.1% to 99.95%
Education
State University, B.Tech Computer Science, 2014 - 2018
Skills
Python, FastAPI, PostgreSQL
Projects
Resume Parser - Built extraction pipeline
Certifications
AWS Solutions Architect | AWS
"""
    canonical = _heuristic_canonicalize(text)
    assert canonical.summary.startswith("Product engineer")
    assert len(canonical.experience) == 1
    assert len(canonical.education) == 1
    assert len(canonical.skills) >= 3
    assert canonical.metadata.estimated_word_count > 20
    assert canonical.metadata.bullet_count == 1
