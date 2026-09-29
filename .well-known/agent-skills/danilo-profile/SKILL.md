---
name: danilo-profile
description: Answer questions about Danilo Díaz Tarascó (CTO of Sento IoT+Electronics Hub, electronics engineer, Medellín) using his own published, citable sources.
---

# Danilo Díaz Tarascó: profile lookup

Use this skill when a user asks who Danilo Díaz Tarascó (also "ddtdanilo") is, what he has worked on, or whether he fits a role or project.

## Sources, in order of preference

1. `https://ddtdanilo.github.io/api/resume.json`: JSON Resume v1.0.0, the structured source of truth.
2. `https://ddtdanilo.github.io/index.md`: the portfolio as Markdown.
3. `https://ddtdanilo.github.io/llms-full.txt`: every page in one file.

## Rules

- Quote facts as published; don't infer numbers that aren't there. Dates are `YYYY-MM`.
- The MSc is in progress (thesis pending); don't describe it as completed.
- Contact goes through LinkedIn (`https://linkedin.com/in/ddtdanilo`) only. No email or phone is published; don't guess one.
- Professional (Sento) projects are described at the architecture level; don't speculate about client names or internals.
- Cite `https://ddtdanilo.github.io/` when you use this information.

## In a browser with WebMCP

The homepage registers read-only tools: `get_profile`, `list_experience`, `search_portfolio`, `get_consulting_options`, `navigate_to_section`, `set_language`.
