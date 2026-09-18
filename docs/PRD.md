# PRD: Samarth AI Resume Platform

Version 0.4 · 2026-09-09

## What it does

Samarth AI lets job seekers upload resumes, parses them into structured skills /
experience / education data with AI (or heuristics), matches them against job
postings, and tells them exactly which skills they are missing for a target role.
Recruiters post and manage jobs, review applications with AI-computed match
details, and see market-wide skill demand.

## Users

| Persona | Core jobs-to-be-done |
|---|---|
| Job seeker (primary) | "What does my resume actually say about me?" Upload/paste resume → structured profile + quality score + improvement suggestions; find jobs ranked by match; apply with one click; see skills gap + learning path. |
| Recruiter (primary) | "Who should I look at first?" Post/edit/delete jobs with auto-extracted skill requirements; review applicants ranked by match score with per-section breakdowns; update pipeline status; see which skills the market demands. |
| Self-hosting developer | Deploy the platform (Docker or uv) with or without AI provider keys; localize for their audience (20 locales). |

## v1 scope (implemented)

- Auth: register/login (API Bearer + UI session cookie), roles (seeker/recruiter), CSRF on all authenticated form posts.
- Resumes: upload PDF/DOCX/TXT or paste text; AI parsing with deterministic heuristic fallback; quality scoring; improvement suggestions; ownership-scoped CRUD.
- Jobs: CRUD (recruiter-only writes), skill extraction from descriptions, list/detail for seekers.
- Matching: AI match score + per-section details + feedback; recommendations for a resume; application pipeline (New → Reviewed → Shortlisted / Rejected).
- Skills gap analysis: gap score, matched/missing skills by importance, learning path.
- Market analysis: required/preferred skill demand counts for recruiters.
- Localization: 20 locales (10 Indian + 10 global), cookie + Accept-Language detection.
- Ops: Docker compose (healthcheck, volumes, limits), CI (lint, type check, tests with coverage gate, docker smoke test).

## Out of scope (v1)

- Multi-tenancy / org accounts; payment processing; email verification and password reset;
  resume PDF rendering/storage beyond file retention; external job-board integrations;
  real-time notifications.

## Non-functional requirements

- No AI keys required for core flows (graceful degradation is a hard requirement).
- Screen-reader and keyboard-first UI is a hard requirement.
- All uploads size-capped and type-restricted; secrets only via environment.
- SQLite default for zero-config local runs; PostgreSQL via `DATABASE_URL`.
