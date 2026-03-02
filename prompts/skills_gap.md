# Skills Gap Analysis

Analyse the gap between a candidate's current skills and the skills required/preferred for a target job.

## Candidate Skills
{resume_skills}

## Required Skills (Job)
{required_skills}

## Preferred Skills (Job)
{preferred_skills}

## Instructions

Return a JSON object with:
- `gap_score` (float 0-100): percentage of target skills the candidate already has.
- `matched_skills` (list[str]): skills the candidate has that match the job.
- `missing_required` (list of objects with `skill`, `status`, `importance`, `learning_suggestion`): required skills the candidate lacks.
- `missing_preferred` (list of objects with `skill`, `status`, `importance`, `learning_suggestion`): preferred skills the candidate lacks.
- `learning_path` (list[str]): ordered steps for the candidate to close the gap, starting with highest-priority skills.
- `summary` (str): a concise 1-2 sentence summary of the gap analysis.

Respond ONLY with valid JSON.
