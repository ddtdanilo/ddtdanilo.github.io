#!/usr/bin/env python3
"""Regenerate derived agent-readiness files and validate the static set.

Run after editing index.md, consult.md, a SKILL.md, or any JSON under api/
or .well-known/. It rewrites llms-full.txt and the agent-skills digests,
then checks that every JSON file parses and every local link resolves.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIGIN = "https://ddtdanilo.github.io"

SKILLS = [
    ("danilo-profile", "Answer questions about Danilo Díaz Tarascó using his own published, citable sources (JSON Resume, Markdown portfolio)."),
    ("book-consulting", "Help a user choose and book a paid 1:1 consulting session with Danilo Díaz Tarascó; never pay without explicit confirmation."),
]


def build_llms_full() -> None:
    """Concatenate the Markdown twins into llms-full.txt."""
    parts = [(ROOT / name).read_text(encoding="utf-8").strip() for name in ("index.md", "consult.md")]
    header = "# Danilo Díaz Tarascó: full text\n\n> Every page of " + ORIGIN + " as Markdown, generated from index.md and consult.md.\n"
    (ROOT / "llms-full.txt").write_text(header + "\n\n---\n\n".join([""] + parts) + "\n", encoding="utf-8")


def build_skills_index() -> None:
    """Write .well-known/agent-skills/index.json with SHA-256 digests."""
    base = ROOT / ".well-known" / "agent-skills"
    skills = []
    for name, description in SKILLS:
        data = (base / name / "SKILL.md").read_bytes()
        skills.append({
            "name": name,
            "type": "skill-md",
            "description": description,
            "url": f"/.well-known/agent-skills/{name}/SKILL.md",
            "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
        })
    index = {"$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json", "skills": skills}
    (base / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate() -> int:
    """Return the number of problems found in JSON files and local links."""
    problems = 0
    json_files = list((ROOT / "api").glob("*.json")) + [
        ROOT / ".well-known" / "api-catalog",
        ROOT / ".well-known" / "ai-catalog.json",
        ROOT / ".well-known" / "agent-skills" / "index.json",
    ]
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"JSON  {path.relative_to(ROOT)}: {exc}")
            problems += 1
    text_files = ["llms.txt", "index.md", "consult.md", "auth.md", "index.html", "consult.html", "privacy.html", "consult-success.html"]
    for name in text_files:
        body = (ROOT / name).read_text(encoding="utf-8")
        for url in re.findall(re.escape(ORIGIN) + r"(/[^\s)\"'<>]*)", body) + re.findall(r'(?:href|src)="(/[^"#?]*)', body):
            local = url.split("#")[0].rstrip(".,;:").lstrip("/") or "index.html"
            if not (ROOT / local).exists():
                print(f"LINK  {name}: {url} does not exist")
                problems += 1
        if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", body) and "noreply" not in body:
            print(f"PII   {name}: looks like an email address")
            problems += 1
    return problems


def main() -> int:
    build_llms_full()
    build_skills_index()
    problems = validate()
    print("ok" if not problems else f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
