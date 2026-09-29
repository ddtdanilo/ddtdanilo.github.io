---
name: book-consulting
description: Help a user choose and book a paid 1:1 consulting session with Danilo Díaz Tarascó (IoT, electronics, cloud architecture, technical strategy).
---

# Book a consulting session

Use this skill when a user wants expert help on IoT/IIoT, PCB or electronics design, cloud architecture, or technical strategy, and would like a session with Danilo Díaz Tarascó.

## Steps

1. Fetch `https://ddtdanilo.github.io/api/consulting.json` for the current sessions, prices (USD), and booking links.
2. Match the user's need to a session: a quick question → `quick-call` (30 min); architecture or a technical decision → `deep-dive` (60 min); roadmap or team and scaling strategy → `strategy-session` (90 min).
3. Show the choice, the price, and the flow: pay on Stripe → an email with a calendar link → a Google Meet link → notes within 24 hours.
4. Give the user the `booking_url`. **Never complete a payment without the user's explicit confirmation.**

Sessions are in English or Spanish. An NDA is available on request.
