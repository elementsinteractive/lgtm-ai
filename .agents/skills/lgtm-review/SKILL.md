---
name: lgtm-review
description: 'Perform an lgtm-ai two-stage code review on the current git repository. Use when: user asks for a code review, says "lgtm", "review my changes", "review this branch", "review against main", "review my PR".'
argument-hint: 'Optional: base ref to compare against (e.g. "main", "HEAD~3"). Defaults to HEAD for uncommitted changes.'
---

# LGTM-AI Code Review

Performs a two-stage AI code review identical to the `lgtm` CLI:

1. **Reviewer** — initial pass generating comments with severity and category
2. **Summarizer** — refinement pass filtering noise, merging duplicates, adjusting score

Both stages run as **separate subagents** with isolated context, exactly as in the lgtm pipeline.

> **CRITICAL — subagent isolation:** Each subagent's `prompt` must contain ONLY:
> 1. The contents of the relevant prompt file (see Steps 2 and 3)
> 2. The input message for that stage
>
> Do NOT include this SKILL.md, any other stage's prompt, or any orchestration instructions in a subagent prompt. The system prompt files are in the same directory as this file.

---

## Step 1 — Collect Context

Run these shell commands to gather the same context the `lgtm` CLI collects:

```bash
BASE="${1:-HEAD}"  # ref provided by user, or HEAD for uncommitted changes

# PR metadata (from last commit message; user may also provide title/description directly)
TITLE=$(git log -1 --format="%s")
DESCRIPTION=$(git log -1 --format="%b")

# Full unified diff
DIFF=$(git diff "${BASE}"..HEAD)

# Context for each changed file
# Retrieve relevant hunks for functions, classes, or methods changed in the diff or related to changed files.
# Include them if they are relevant for understanding the change, but exclude if they are too large or unrelated.
```


Assemble the **Stage 1 input message** in exactly this format (mirrors lgtm's Jinja2 template):

````
PR METADATA:
- Title: <TITLE>
- Description: <DESCRIPTION>

PR DIFF:
```
<DIFF>
```

CONTEXT:
```file=<file_path>, branch=source
<full file contents>
```
... (one block per changed file)
````

---

## Step 2 — Stage 1: Reviewer Subagent

Read the file `reviewer-prompt.md` (in the same directory as this file). That file's entire contents are the subagent's prompt prefix.

Spawn a subagent whose `prompt` is:
```
<full contents of reviewer-prompt.md>

<Stage 1 input message from Step 1>
```

Nothing else. The subagent returns only JSON.

---

## Step 3 — Stage 2: Summarizer Subagent

Read the file `summarizer-prompt.md` (in the same directory as this file). That file's entire contents are the subagent's prompt prefix.

Assemble the **Stage 2 input message**:

````
PR METADATA:
- Title: <TITLE>
- Description: <DESCRIPTION>

PR DIFF:
```
<DIFF — same as Step 1>
```

REVIEW:
```
<Stage 1 JSON output verbatim>
```
````

Spawn a subagent whose `prompt` is:
```
<full contents of summarizer-prompt.md>

<Stage 2 input message>
```

Nothing else. The subagent returns only JSON.

---

## Step 4 — Render the Review

Map `raw_score` to a label:

| raw_score | Label |
|-----------|-------|
| 5 | LGTM |
| 4 | Nitpicks |
| 3 | Needs Work |
| 2 | Needs a Lot of Work |
| 1 | Abandon |

Output the review **directly as Markdown prose** — do NOT wrap it in a code block, do NOT echo the JSON, do NOT add any preamble. The output is intended for a human reading it in VS Code Copilot or Claude Code. Sort comments by severity (HIGH → MEDIUM → LOW), grouped by category. Category emojis: Correctness → 🎯, Quality → ✨, Testing → 🧪, Security → 🔒.

````markdown
## 🦉 lgtm Review

> **Score:** <label> <emoji>

### 🔍 Summary

<summary>

---

#### 🎯 Correctness  (or ✨ Quality / 🧪 Testing / 🔒 Security)

> **Severity:** HIGH 🔴  (or MEDIUM 🟡 / LOW 🔵)

**`<file>` — line <line_number>**

```
<quote_snippet>
```

<comment>

```suggestion   ← only if suggestion present
<suggestion.snippet>
```

````
