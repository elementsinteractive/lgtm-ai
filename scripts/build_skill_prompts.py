#!/usr/bin/env python3
"""Inject lgtm-ai prompts inline into the Claude plugin agent file.

Ensures the inlined prompts stay in sync with lgtm-cli as the Python prompts evolve.

Usage:
    poetry run python scripts/build_skill_prompts.py          # update in place
    poetry run python scripts/build_skill_prompts.py --check  # fail if out of date
    # or via just:
    just build-plugin-prompts
"""

import re
import sys
from pathlib import Path

from lgtm_ai.ai.prompts import REVIEWER_SYSTEM_PROMPT, SUMMARIZING_SYSTEM_PROMPT

PLUGIN_AGENT_FILE = Path(__file__).parent.parent / "plugins" / "lgtm-review" / "agents" / "lgtm-reviewer.md"

# Replaces <diff-format> in the reviewer prompt.
# The skill uses raw `git diff` output; lgtm-cli converts it to JSON first.
_UNIFIED_DIFF_DESCRIPTION = (
    "- A git diff in standard unified diff format (output of `git diff`)."
    " Lines starting with `+` are additions, lines with `-` are removals,"
    " context lines have no prefix."
    " `@@ -old_start,count +new_start,count @@` headers indicate where in the file changes occur."
)

# Replaces <hunk-boundary> in the summarizer prompt.
# Drops the JSON field names (hunk_start_new / hunk_start_old) irrelevant to unified diff.
_SKILL_HUNK_BOUNDARY = (
    "Ensure that suggestions don't span outside git hunk boundaries."
    " If they do, adjust the suggestion to fit within the hunk."
)

_REVIEWER_OUTPUT_SCHEMA = """
Return ONLY the following JSON (no markdown wrapping, no extra text):

{
  "summary": "<overall review summary>",
  "raw_score": <integer 1-5>,
  "comments": [
    {
      "file": "<file path>",
      "line_number": <integer>,
      "comment": "<review comment in markdown>",
      "category": "<Correctness|Quality|Testing|Security>",
      "severity": "<LOW|MEDIUM|HIGH>",
      "quote_snippet": "<relevant code snippet, no diff artifacts>"
    }
  ]
}
"""

_SUMMARIZER_OUTPUT_SCHEMA = """
Return ONLY the following JSON (no markdown wrapping, no extra text):

{
  "summary": "<improved summary>",
  "raw_score": <integer 1-5>,
  "comments": [
    {
      "file": "<file path>",
      "line_number": <integer>,
      "comment": "<refined comment>",
      "category": "<Correctness|Quality|Testing|Security>",
      "severity": "<LOW|MEDIUM|HIGH>",
      "quote_snippet": "<code snippet>",
      "suggestion": {
        "snippet": "<suggested replacement code>",
        "lines_above": <integer>,
        "lines_below": <integer>,
        "ready_for_replacement": <true|false>
      }
    }
  ]
}
"""


def _replace_xml_block(text: str, tag: str, replacement: str) -> str:
    """Replace <tag>...</tag> (including the tags themselves) with replacement."""
    return re.sub(rf"<{tag}>.*?</{tag}>", replacement, text, flags=re.DOTALL)


def _inject_into_sentinel(text: str, sentinel: str, content: str) -> str:
    """Replace content between <!-- BEGIN:sentinel --> and <!-- END:sentinel --> markers."""
    pattern = rf"(<!-- BEGIN:{re.escape(sentinel)} -->).*?(<!-- END:{re.escape(sentinel)} -->)"
    replacement = rf"\1\n{content}\n\2"
    return re.sub(pattern, replacement, text, flags=re.DOTALL)


def build_reviewer_prompt() -> str:
    prompt = REVIEWER_SYSTEM_PROMPT.strip()
    prompt = _replace_xml_block(prompt, "diff-format", _UNIFIED_DIFF_DESCRIPTION)
    return prompt + "\n" + _REVIEWER_OUTPUT_SCHEMA


def build_summarizer_prompt() -> str:
    prompt = SUMMARIZING_SYSTEM_PROMPT.strip()
    prompt = _replace_xml_block(prompt, "hunk-boundary", _SKILL_HUNK_BOUNDARY)
    return prompt + "\n" + _SUMMARIZER_OUTPUT_SCHEMA


def main() -> None:
    check_only = "--check" in sys.argv

    reviewer_prompt = build_reviewer_prompt()
    summarizer_prompt = build_summarizer_prompt()

    original = PLUGIN_AGENT_FILE.read_text()
    updated = _inject_into_sentinel(original, "reviewer-prompt", reviewer_prompt)
    updated = _inject_into_sentinel(updated, "summarizer-prompt", summarizer_prompt)

    if check_only:
        if original != updated:
            print(
                f"ERROR: {PLUGIN_AGENT_FILE} is out of date. Run 'just build-plugin-prompts' to fix.", file=sys.stderr
            )
            sys.exit(1)
        print(f"OK: {PLUGIN_AGENT_FILE}")
    else:
        PLUGIN_AGENT_FILE.write_text(updated)
        print(f"Updated: {PLUGIN_AGENT_FILE}")


if __name__ == "__main__":
    main()
