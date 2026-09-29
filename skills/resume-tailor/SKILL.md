---
name: resume-tailor
description: Use when the user wants their existing resume tailored or customized for a specific job posting (JD) — 根据JD改简历、简历定制、简历匹配度、tailor my resume、customize resume for this job、should I apply、resume match score. Produces ATS-optimized, keyword-matched versions with strict no-fabrication rules and anti-AI-slop writing standards. Do NOT use for creating a resume from scratch or general improvement without a target job (use resume-builder).
---

# Resume Tailoring Skill

Create compelling, tailored resumes that make it obvious the candidate is the right person for one specific job. Three non-negotiables:

1. **Never fabricate** — only reorganize and reframe real experience
2. **Never inflate** — reframe only what exists in the source materials
3. **Never sound like AI** — short sentences, plain words, no emdashes

## Priority Hierarchy

When instructions conflict, resolve in this order (highest first):

1. **Accuracy** — never fabricate, inflate, or assume facts not in the source materials
2. **User corrections** — explicit corrections from the user override all generated content
3. **Workflow steps** — follow the workflow below as written
4. **Writing quality** — clear, concise, human-sounding language (target Flesch score > 90 where applicable)
5. **Output format** — consistent section headers and structure
6. **Tone and style** — professional but approachable; match the role's seniority level

## Data Directory

All user data lives in a `.resume/` folder. Resolve it in this order:

1. Check the current working directory for `.resume/` — use it if found
2. Check `~/.resume/` — use it if found
3. If neither exists, create `~/.resume/` and tell the user where it is

```
DATA_DIR/
  resume/                 # User's master resume (PDF/DOCX/MD/TXT)
  profile.md              # Work history profile (optional but strongly recommended)
  jobs/                   # One folder per application
    <company-slug>-<date>/
      posting.md          # Saved job description
      resume.md           # Tailored resume
```

## Workflow

### Step 0: Check Inputs

Resolve DATA_DIR. Get the source resume:

- Check `DATA_DIR/resume/` for the user's master resume
- Otherwise ask the user to paste it, give a file path, or point at a file in the workspace

Check for `DATA_DIR/profile.md`. If it is missing, ask the user to choose:

- **(a) Quick work-history interview now** — build `profile.md` using `references/profile-template.md`. Takes a few minutes, but makes every future tailoring dramatically better and enables assumption-free resumes.
- **(b) Proceed with resume only** — fastest, but every assumption made will be listed for verification at the end (Step 3a).

### Step 1: Get Job Details

Ask for the job URL (or accept a pasted job description).

Fetch the posting with the `webfetch` tool. If the page fails to load, is JS-rendered, or returns empty content, try an available web-extract/search tool (e.g. Tavily extract), then ask the user to paste the description directly.

Parse and extract:

- **Job title** and level (IC vs. manager, seniority)
- **Company** name and what they do
- **Responsibilities** — what the job actually involves day-to-day
- **Requirements** — must-have qualifications
- **Nice-to-haves** — preferred qualifications
- **Keywords** — industry terms, tools, methodologies mentioned
- **Team context** — who they report to, team size, cross-functional partners
- **Company stage/size** indicators

Create a job folder at `DATA_DIR/jobs/[company-slug]-[date]/` and save the parsed posting to `posting.md`.

### Step 2: Analyze Match

Before writing, map the candidate's experience to the job:

1. **Level match**: Confirm the candidate's experience level matches the role. A VP-level candidate applying for a Director role should lean on strategic impact. A Director applying for VP should emphasize scope and leadership growth.

2. **Requirement mapping**: For each job requirement, identify the strongest evidence from the resume/profile:
   - Direct experience ("Led SEO strategy" → job asks for SEO experience)
   - Analogous experience ("Scaled marketplace from 1M to 10M users" → job asks for growth experience)
   - Transferable skills ("Managed 30-person team" → job asks for leadership)

3. **Gap identification**: Note requirements with no clear match. These must NOT be fabricated — find adjacent experience that demonstrates capability, or omit.

4. **Keyword alignment**: Identify the job posting's language and terminology to mirror in the resume.

5. **Compelling narrative**: Determine the 2-3 sentence story of why this person is the obvious choice. What's the throughline?

### Step 3: Generate Tailored Resume

Read `references/tailoring-guide.md` for the full section-by-section playbook (summary, bullets, skills, level calibration). Key principles:

**Structure:**

- **Header**: Name, contact info, LinkedIn (same as original)
- **Summary/Profile**: 2-3 sentences positioning the candidate specifically for THIS role. Reference the company and role context directly. Not generic.
- **Experience**: All roles from the resume, bullets rewritten, reordered, selectively emphasized
- **Skills**: Reorganized to lead with what the job asks for
- **Education**: Same as original

**Bullet principles:**

- Lead each role with the bullets most relevant to the target job
- Rewrite bullets to mirror the job posting's language where authentic
- Include metrics and quantified impact (from the work history profile)
- Remove or de-emphasize bullets irrelevant to this specific role
- Add bullets from the work history profile that weren't on the original resume but ARE relevant to this job
- Each bullet: strong action verb + what you did → how you did it → what the impact was

**Writing rules (CRITICAL — target Flesch score above 90):**

- Write like a sharp executive, not a language model. Short sentences. Plain words.
- Every sentence gets one idea. If a sentence has "and" connecting two unrelated clauses, split it.
- Never use emdashes. Use commas, periods, colons, semicolons, or parentheses instead.
- Vary sentence structure. Not every bullet should follow the exact same pattern.
- No preamble clauses. Bad: "Leveraging deep expertise in marketplace dynamics, led..." Good: "Led..."
- No stacking adjectives. Bad: "cross-functional, data-driven, customer-centric approach". Pick one.
- No filler phrases: "demonstrating ability to", "showcasing expertise in", "with a track record of", "needed to drive", "spanning", "leveraging", "utilizing"
- No compound noun piles: "AI-driven product opportunity identification and execution" — just say what you did
- Summaries must be 2-3 SHORT sentences. Each sentence under 20 words. No run-on sentences connecting multiple capabilities with commas and "and".

**Strict accuracy rules (CRITICAL):**

- ONLY use information explicitly stated on the resume or in the work history profile
- NEVER assume business model (B2B vs B2C), revenue type, or company stage unless stated
- NEVER infer scope beyond what's written (e.g., don't add "P&L ownership" if resume says "revenue targets")
- NEVER add responsibilities, skills, or functional areas the candidate didn't mention
- NEVER assume cross-functional partnerships that aren't listed
- When the resume is ambiguous, use conservative language or omit the detail entirely
- If you need to frame experience differently for the target role, only reframe what IS there, never invent what ISN'T

**What NOT to do:**

- Don't fabricate experience or skills the candidate doesn't have
- Don't use generic buzzwords that aren't backed by specific experience
- Don't make the resume longer than 2 pages
- Don't change job titles or dates
- Don't remove roles (gaps look suspicious)
- Don't assume anything about the candidate's business, scope, or responsibilities that isn't explicitly documented

### Step 3a: Verify Assumptions (only if no profile exists)

Present the user with a list of every assumption made:

```
Before we finalize, here are the assumptions I made. Please correct
any that are wrong:

1. [Company] - I assumed [X]. Is that right?
2. [Role scope] - I described your scope as [Y]. Accurate?
3. [Business model] - I framed this as [Z]. Correct?
...
```

Wait for the user to verify or correct before finalizing. Apply all corrections to the resume AND save them to `DATA_DIR/profile.md` so they persist.

### Step 3b: Critique and Rewrite (MANDATORY — before presenting)

Review every line and fix AI-sounding writing. Go sentence by sentence and ask:

1. **Is this sentence doing too much?** More than one comma-separated clause? Split into separate sentences or bullets.
2. **Would a real person say this?** Read it out loud. If it sounds like a LinkedIn post or a ChatGPT response, rewrite it.
3. **Is there filler?** Cut any phrase that doesn't add information. "Demonstrating ability to identify and execute on AI-driven product opportunities from ideation through production" → "Built an AI product from idea to production."
4. **Are there stacked buzzwords?** "Cross-functional, data-driven, customer-centric leadership" → pick the one that matters for this job and give a concrete example.
5. **Is the summary under control?** Max 3 sentences. Each under 20 words. No sentence should list more than 2 things.

**Common AI patterns to kill:**

- "I combine X with Y, Z, and the W needed to..." → Split into separate statements
- "...demonstrating [abstract quality]" → Delete or replace with the actual result
- "...spanning [long list]" → Pick the most relevant 1-2 items
- "Led [action], [action], and [action] across [scope]" → One action per bullet
- Any bullet over 2 lines is probably trying to do too much — split it
- Gerund clauses tacked onto the end: "...delivering X while maintaining Y" → Two sentences

**Test:** After rewriting, re-read the summary and first 3 bullets. If any sentence takes more than one breath to read aloud, it's too long. Shorten it.

**Save:** write the tailored resume to `DATA_DIR/jobs/[company-slug]-[date]/resume.md`

### Step 4: Present and Iterate

Present the resume with tailoring notes:

```
Here's your tailored resume for [Role] at [Company].

**Key changes I made:**
- [What was reordered/emphasized and why]
- [What bullets were rewritten and why]
- [What was added from your work history]

**The narrative:** [2-3 sentence pitch for why you're the right person]

The resume is saved to: DATA_DIR/jobs/[folder]/resume.md
```

Ask if the user wants to adjust: tone (more technical/strategic/metrics-heavy), emphasis, length (1 page vs 2), specific bullets. Apply and re-save.

If the user wants a Word/PDF deliverable, use the `resume-builder` skill to produce .docx + text-based .pdf from the final markdown.

### Step 5: Update Profile (ALWAYS)

Every time the user corrects a factual detail, update `DATA_DIR/profile.md` immediately:

- Business model corrections (e.g., "this was B2C, not B2B")
- Scope corrections (e.g., "I had revenue targets, not P&L ownership")
- Responsibility corrections (e.g., "I didn't manage candidate workflows")
- Any other clarification about roles, teams, or accomplishments

This prevents the same mistakes on future resumes. If the profile is still a blank template, create a new one with whatever the user has told you so far. Use the structure from `references/profile-template.md` but fill in only what you know for certain.

## Response Format

Structure user-facing output:

1. **Tailored Resume** — the full resume text
2. **Tailoring Notes** — key changes (reordered bullets, rewritten sections, added content from profile) and the narrative pitch
3. **What's Next** — suggest iterating on tone/emphasis, or generating the .docx/.pdf via resume-builder

## Attribution

Adapted from Proficiently's open-source skills (https://github.com/proficientlyjobs/proficiently-claude-skills, MIT License).
