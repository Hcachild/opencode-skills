---
name: resume-builder
description: Use when the user wants to create, improve, optimize, review, rewrite, format, or translate a resume, CV, or 简历 — 写简历、做简历、改简历 — including ATS keyword optimization, bullet-point improvements, metrics/quantification, bilingual or multiple resume versions, or converting a tailored resume .md into a .docx + text-based .pdf deliverable. Do NOT use when the user has a specific job posting to customize to (use resume-tailor); not for LinkedIn profiles, portfolios, or general document formatting.
---

# Resume / CV Builder — Harvard Standards & ATS Best Practices

## Overview

This skill creates professional, high-standard resumes following Harvard Career Services guidelines, r/EngineeringResumes community best practices, and modern ATS (Applicant Tracking System) knowledge. It produces resumes optimized for both human recruiters (who spend 5-20 seconds scanning) and ATS parsing systems.

**Before starting any resume work, read the relevant reference files:**

- `references/format-and-structure.md` — Page layout, fonts, spacing, section ordering, PDF conversion
- `references/bullet-writing-guide.md` — XYZ/STAR formula, action verbs, quantification
- `references/ats-and-keywords.md` — ATS truths vs myths, keyword strategy
- `references/common-mistakes.md` — What to avoid, anti-patterns

---

## Quick Decision Framework

| User Request | Action |
|---|---|
| "Create my resume from scratch" | Full build: gather info → structure → write → format → deliver |
| "Improve/optimize my existing resume" | Analyze current → identify issues → rewrite bullets → reformat |
| "Tailor resume to job description" | Use the `resume-tailor` skill instead (JD-specific) — then return here for .docx/.pdf |
| "Review my resume" | Audit against checklist → provide specific feedback with examples |
| "Create multiple versions" | Build base resume → create variants (1-page, 2-page, language versions) |
| "Make it ATS-friendly" | Check format compliance → ensure parseable structure → add relevant keywords naturally |
| "Convert this resume.md to Word/PDF" | Run Document Generation below |

---

## Core Process

### Step 1: Gather Information

Before writing anything, collect:

1. **Full work history** — titles, companies, locations, dates, AND the domain/industry context of what each company does and what systems the user built
2. **Technical skills** — languages, frameworks, databases, tools, cloud, architecture patterns
3. **Education** — degrees, institutions, dates
4. **Projects** — personal, academic, open source
5. **Target market** — US/international (English), LATAM/Spain (Spanish), China (中文), or multiple
6. **Target roles** — what kind of positions they're applying for
7. **Page preference** — 1 page (junior/mid), 2 pages (6+ years senior), or flexible

**CRITICAL: Ask about domain context for each role.** The difference between "developed web applications" and "developed fintech credit management systems handling card issuance, payment links, and transaction processing" is the difference between a generic and a compelling resume. Always ask:

- What industry/domain was this? (fintech, legaltech, healthcare, logistics, security, etc.)
- What kind of data did you handle? (sensitive PII, financial, legal, medical)
- Who were the end users? (B2B, B2C, internal, government)
- What was the business impact?

### Step 2: Structure the Resume

Follow the section order recommended by Harvard Career Services and r/EngineeringResumes:

```
1. Name & Contact Information (centered)
2. Technical Skills (for engineering/tech roles — put skills FIRST)
3. Professional Experience (reverse chronological)
4. Projects & Contributions (if relevant)
5. Education (at bottom for experienced professionals)
```

**Why Skills first?** For tech roles, recruiters and hiring managers scan for specific technologies. Putting skills at the top gives them what they need in the first 5 seconds. Harvard recommends ordering headings "in order of importance" — for engineers, skills ARE the most important first-scan item.

**Education placement:** Harvard puts education first for students. For professionals with 3+ years experience, move education to the bottom. The experience section becomes the centerpiece.

### Step 3: Write Content

Read `references/bullet-writing-guide.md` for the complete guide. Key principles:

**Every bullet must follow the XYZ formula:**
> "Accomplished [X] as measured by [Y] by doing [Z]"

Or condensed: **Action Verb + What You Did + Technical Context + Business Impact**

**Example transformation:**

- BAD: "Responsible for developing web applications"
- GOOD: "Developed fintech web applications for credit management, card issuance, and transaction processing using React and NestJS, structured under Hexagonal Architecture and DDD"

### Step 4: Format and Deliver

Read `references/format-and-structure.md` for the complete guide. Key specs:

- **Font:** Calibri 10.5pt body, 16pt name, 11.5pt section headings
- **Margins:** 0.75 inches all sides
- **Line spacing:** 13pt
- **Format:** Single column, no tables for layout, no graphics
- **File format:** .docx (for editing) AND .pdf (for sending/uploading)

### Step 5: Generate .docx and .pdf (MANDATORY deliverable)

**Always deliver both .docx and .pdf versions.** The .docx is for future editing; the .pdf is for sending to employers.

See **Document Generation** below for the exact commands. Verify before delivering:

- PDF is text-based (not an image) and text extraction returns the full resume
- PDF page count matches expectations
- Name and key content appear correctly in extracted text (catches truncation or encoding issues)

**Why PDF matters:**

- .docx can render differently depending on the recipient's Word version, OS, and installed fonts
- PDF guarantees the recruiter sees EXACTLY what you designed
- Many job application portals specifically request PDF
- ATS parses text-based PDFs just as well as .docx

---

## Document Generation

Use Python and office tooling on the machine. Check what is available first, then follow this workflow:

**0. Detect the local setup:**

- `python --version` (or `py -3` / `python3`) and `python -m pip --version` must work
- PDF conversion options: Microsoft Word (Windows/macOS, via docx2pdf) or LibreOffice (`soffice` in PATH or common install paths, e.g. `C:\Program Files\LibreOffice\program\soffice.exe` on Windows)
- If neither Word nor LibreOffice is available, still produce the .docx and tell the user to export the PDF themselves

**1. Ensure dependencies:**

```
python -m pip install --user python-docx docx2pdf pypdf
```

**2. Build the .docx with python-docx.** Write a small Python script to a temp file (e.g. in the system temp directory) that applies the specs from `references/format-and-structure.md` (Calibri, 10.5pt body / 16pt name / 11.5pt headings, 0.75" margins, single column, text-only bullets, right-aligned dates). Run it with `python` and check for exceptions. Do not expect any prebuilt converter script in this skill.

**3. Convert to PDF.** Preferred when Microsoft Word is installed (most faithful rendering):

```
python -c "from docx2pdf import convert; convert(r'resume.docx', r'resume.pdf')"
```

Fallback when Word is unavailable — LibreOffice:

```
soffice --headless --convert-to pdf resume.docx
```

**4. Verify the PDF is text-based and complete:**

```
python -c "from pypdf import PdfReader; r=PdfReader('resume.pdf'); t=''.join(p.extract_text() or '' for p in r.pages); print('pages:', len(r.pages)); print('chars:', len(t)); print(t[:300])"
```

If extraction is empty, the PDF is image-based or broken — regenerate. Check page count and that the name and key sections extracted.

**5. Deliver both files.** Save outputs next to the user's context: default to `~/.resume/jobs/<company-slug>-<date>/` when tailoring for a posting, otherwise the current working directory or a path the user specifies.

---

## Language Guidelines

### For English Resumes

- Use active voice, no personal pronouns (no "I", "my", "we")
- Start every bullet with a strong action verb (see reference file)
- Use US English spelling for US-targeted roles
- Keep job titles in standard industry format

### For Chinese Resumes (中文简历)

- Keep the same structure and principles; section headers: 个人信息、技能、工作经历、项目经历、教育背景
- No personal pronouns; start bullets with strong verbs (主导、搭建、优化、推动、设计)
- Keep technical terms in English when industry standard (e.g., backend, DevOps, Kubernetes)
- Chinese resumes are usually 1-2 pages; photos/age/gender are optional and often omitted for international applications

### For Spanish Resumes

- Maintain the same structure and principles
- Use professional Spanish — avoid colloquialisms
- Keep technical terms in English when they're industry standard (e.g., "backend", "frontend", "DevOps", "SOLID", "CQRS")
- Start bullets with action verbs in Spanish (Desarrolle, Implemente, Lidere, Disene, Construi, Optimice, Arquitecte)

### Bilingual Strategy

When creating multiple language versions, ensure they are NOT literal translations. Each version should read naturally in its language while conveying the same information and impact.

---

## Checklist Before Delivery

Run this checklist against every resume before delivering:

**Format:**

- [ ] Name fits on one line without truncation (max 16pt)
- [ ] Single-column layout, no tables for layout, no graphics/icons
- [ ] Font is Calibri/Arial, minimum 10.5pt body, black color
- [ ] White space is balanced — not too cramped, not too sparse
- [ ] Dates use en dashes (–) not hyphens (-), with spaces around them
- [ ] Dates are right-aligned, bullets don't extend past dates
- [ ] URLs are plain text (no color, no underline, no "Email:" prefixes, no https://www.)

**Content:**

- [ ] No personal pronouns (I, my, we, our)
- [ ] Every bullet starts with a strong past-tense action verb
- [ ] No bullets end with periods (bullets are not sentences)
- [ ] Every experience describes the DOMAIN (industry, system type, data sensitivity)
- [ ] Metrics/quantification present where possible (use digits: 8, not "eight")
- [ ] Technologies listed per role AND in skills section
- [ ] No superfluous verbs (spearheaded, orchestrated, utilized, leveraged)
- [ ] No excessive adjectives/adverbs (excellent, innovative, strategically)
- [ ] Section names follow standard: "Experience", "Skills", "Projects", "Education"
- [ ] Dates are consistent format with "Present" for current role (not "Current"/"Now")
- [ ] Reverse chronological order within each section
- [ ] No spelling/grammar errors
- [ ] No internal company jargon or project names only insiders would understand

**Delivery:**

- [ ] PDF version generated from final .docx
- [ ] PDF is text-based (verified with pypdf extraction — text is extractable)
- [ ] PDF page count matches expectations
- [ ] All hyperlinks work and point to professional pages
- [ ] Both .docx and .pdf delivered to user

## Attribution

Adapted from https://github.com/dabydat/resume-builder-skill (MIT License), built on Harvard Career Services standards, r/EngineeringResumes, The Tech Resume Inside Out, and Tech Interview Handbook.
