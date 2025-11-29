"""Resume Analysis Python

This file extracts text from resumes (PDF or TXT), structures key information
(skills, experience, education, projects), builds a user profile, infers
proficiency and saves the structured insights as JSON.

This rewrite handles environments where `pdfplumber` may be missing by
attempting several fallbacks (pdfplumber -> PyPDF2). If no PDF library is
available the code will provide a helpful error and a fallback path: supply
plain-text resumes (.txt) or install a PDF parser in your environment.

Also includes lightweight tests that run when executed without a real file.
"""

import os
import sys
import json
import re
import importlib
from typing import Dict, Any, List, Optional

# ---------------------- PDF TEXT EXTRACTION WITH FALLBACKS ----------------------

def _import_pdf_text_extractors():
    """
    Try to import PDF text extraction libraries in order of preference.
    Returns a dict with available extractors.
    """
    available = {}

    # Try pdfplumber
    try:
        pdfplumber = importlib.import_module("pdfplumber")
        available["pdfplumber"] = pdfplumber
    except Exception:
        pass

    # Try PyPDF2
    try:
        pypdf2 = importlib.import_module("PyPDF2")
        available["pypdf2"] = pypdf2
    except Exception:
        pass

    return available


def extract_text_from_pdf_with_fallback(pdf_path: str) -> str:
    """
    Extract text from a PDF file using any available library. If none are
    available, raise RuntimeError with actionable instructions.
    """
    available = _import_pdf_text_extractors()

    if "pdfplumber" in available:
        pdfplumber = available["pdfplumber"]
        # pdfplumber API
        with pdfplumber.open(pdf_path) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\n".join(pages)

    if "pypdf2" in available:
        PyPDF2 = available["pypdf2"]
        # Different PyPDF2 versions have different APIs (PdfReader vs PdfFileReader)
        try:
            # Newer PyPDF2: PdfReader
            reader = PyPDF2.PdfReader(pdf_path)
            pages = []
            for p in reader.pages:
                try:
                    pages.append(p.extract_text() or "")
                except Exception:
                    # fallback: try reading /data as string
                    pages.append("")
            return "\n".join(pages)
        except Exception:
            try:
                # Older API
                reader = PyPDF2.PdfFileReader(open(pdf_path, "rb"))
                pages = []
                for i in range(reader.getNumPages()):
                    try:
                        pages.append(reader.getPage(i).extractText() or "")
                    except Exception:
                        pages.append("")
                return "\n".join(pages)
            except Exception:
                pass

    # No supported PDF library is available
    raise RuntimeError(
        "No PDF parser library is available in this environment. "
        "Install 'pdfplumber' or 'PyPDF2' (e.g. pip install pdfplumber PyPDF2), "
        "or provide the resume as a plain-text .txt file."
    )

# ---------------------- TXT EXTRACTION ----------------------

def extract_text_from_txt(txt_path: str) -> str:
    """Simple read for .txt resumes."""
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

# ---------------------- INFORMATION EXTRACTION ----------------------

def normalize_text(text: str) -> str:
    """Normalize whitespace and remove weird characters for easier regexing."""
    return re.sub(r"\s+", " ", text).strip()


def extract_skills(text: str, extra_keywords: Optional[List[str]] = None) -> List[str]:
    skill_keywords = [
        "python", "java", "c++", "c#", "sql", "html", "css", "javascript",
        "typescript", "react", "node", "django", "flask", "machine learning",
        "deep learning", "data analysis", "pandas", "numpy", "git", "docker",
    ]
    if extra_keywords:
        skill_keywords = list(dict.fromkeys(skill_keywords + extra_keywords))

    lowered = text.lower()
    found = []
    for skill in skill_keywords:
        # match whole word where sensible
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, lowered):
            found.append(skill)
    return found


def extract_education(text: str) -> List[str]:
    edu_patterns = [
        r"\b(BS|B\.S\.|Bachelor[^,\n]*)\b[\s\S]{0,80}",
        r"\b(MS|M\.S\.|Master[^,\n]*)\b[\s\S]{0,80}",
        r"\b(Bachelor of [^,\n]+)\b",
        r"\b(Master of [^,\n]+)\b",
        r"\b(High School|Intermediate|Matriculation|Matric)\b[\s\S]{0,40}",
        r"\b(Ph\.D|PhD|Doctorate)\b[\s\S]{0,80}",
    ]
    results = []
    for pattern in edu_patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            snippet = m.group(0).strip()
            if snippet not in results:
                results.append(snippet)
    return results


def extract_experience(text: str) -> List[Dict[str, Any]]:
    """
    Extracts experience blocks by looking for common headings like 'Experience',
    or lines with 'years' e.g. '3 years', or job lines with company and dates.
    Returns a list of dicts with simple extracted info.
    """
    experiences = []

    # First, split by common section headings
    sections = re.split(r"\n{2,}|\r\n{2,}", text)
    for sec in sections:
        if re.search(r"\bexperience\b", sec, flags=re.IGNORECASE) or re.search(r"\bworked as\b", sec, flags=re.IGNORECASE):
            experiences.append({"raw": sec.strip()})

    # fallback: find patterns like 'X years' near job titles
    for m in re.finditer(r"([A-Za-z &,-]{2,60})\s+[-@\|]?\s*(\d+)\s+years?", text, flags=re.IGNORECASE):
        title = m.group(1).strip()
        years = int(m.group(2))
        experiences.append({"role": title, "years": years})

    # make unique by raw text when present
    unique = []
    seen = set()
    for e in experiences:
        key = e.get("raw") or (e.get("role") + str(e.get("years")))
        if key not in seen:
            unique.append(e)
            seen.add(key)

    return unique


def extract_projects(text: str) -> List[str]:
    # Look for lines starting with Project or Projects or 'Selected Projects'
    projects = []
    for m in re.finditer(r"(Project[s]?[:\-]?\s*)([\s\S]{1,300}?)(?=(\n\n|$|\n[A-Z]))", text, flags=re.IGNORECASE):
        proj = m.group(2).strip()
        if proj and proj not in projects:
            projects.append(proj)
    return projects

# ---------------------- PROFILE BUILDER & PROFICIENCY ----------------------

def build_profile(text: str, extra_skill_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    normalized = normalize_text(text)
    skills = extract_skills(normalized, extra_skill_keywords)
    education = extract_education(normalized)
    experience = extract_experience(text)
    projects = extract_projects(text)

    profile = {
        "skills": skills,
        "education": education,
        "experience": experience,
        "projects": projects,
    }
    profile["proficiency"] = identify_proficiency(skills)
    return profile


def identify_proficiency(skills: List[str]) -> Dict[str, str]:
    proficiency_map = {}
    for skill in skills:
        sk = skill.lower()
        if sk in ["python", "machine learning", "deep learning", "data analysis", "pandas", "numpy"]:
            proficiency_map[skill] = "Advanced"
        elif sk in ["java", "c++", "c#", "sql"]:
            proficiency_map[skill] = "Intermediate"
        else:
            proficiency_map[skill] = "Beginner"
    return proficiency_map

# ---------------------- STORAGE ----------------------

def save_profile(profile: Dict[str, Any], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=4, ensure_ascii=False)

# ---------------------- MAIN PIPELINE ----------------------

def analyze_resume(path: str, output_path: str = "resume_profile.json") -> Dict[str, Any]:
    """
    Accepts a path to a resume file. Supports .pdf and .txt.
    If PDF support libraries are missing, a RuntimeError will be raised with
    guidance on how to proceed.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = extract_text_from_pdf_with_fallback(path)
    elif ext in [".txt", ".md"]:
        text = extract_text_from_txt(path)
    else:
        raise ValueError("Unsupported file type. Please provide a .pdf or .txt resume.")

    profile = build_profile(text)
    save_profile(profile, output_path)
    return profile

# ---------------------- LIGHTWEIGHT TESTS ----------------------

def _run_smoke_tests():
    print("Running smoke tests on text-based parsing...")

    sample_text = """
    John Doe
    Email: john@example.com

    Education
    Bachelor of Science in Computer Science, University of Nowhere, 2018

    Experience
    Software Engineer - ExampleCorp (2019 - Present)
    - Worked as backend engineer for 3 years using Python, Django and SQL.

    Projects
    Project: Smart Analytics - built ML pipelines using pandas and scikit-learn.

    Skills: Python, SQL, Django, pandas, machine learning, Git, Docker
    """

    profile = build_profile(sample_text)
    print(json.dumps(profile, indent=2))

    assert "Python" in profile["skills"] or "python" in [s.lower() for s in profile["skills"]], "python should be detected"
    assert any("Bachelor" in e or "Bachelor" in str(e) for e in profile["education"]), "education should detect Bachelor"
    assert profile["projects"], "projects should be detected"

    print("All smoke tests passed. If you want tests against real PDFs, ensure a PDF parser is installed in your environment.")

# ---------------------- CLI ENTRY POINT ----------------------

if __name__ == "__main__":
    # Usage:
    #   python resume_analysis.py path/to/resume.pdf
    #   python resume_analysis.py path/to/resume.txt
    # If no argument provided, run smoke tests.
    if len(sys.argv) == 1:
        _run_smoke_tests()
    else:
        path = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else "resume_profile.json"
        try:
            profile = analyze_resume(path, out)
            print(f"Analysis complete. Structured profile saved to: {out}")
            print(json.dumps(profile, indent=2))
        except RuntimeError as e:
            print("ERROR:", e)
            print("If you cannot install packages in this environment, please convert the resume to .txt and run again.")
        except Exception as e:
            print("Unhandled error:", repr(e))
            raise

