# Interview Coach Agent — Feature Gaps & Roadmap

> **Status:** Planned, not implemented. This file documents feature gaps only; it does not change the app's runtime behavior.
>
> **Start with the Figma diagram:** [Interview Coach Agent — architecture & workflow (node 221:31)](https://www.figma.com/design/eVmB2S0UTg8IP2yllKNH4O/temp?node-id=221-31&t=6eljU6Qq20O89JYw-4). **Review the diagram first** to understand how the interview loop, orchestration, scoring and knowledge services should interact.

## Already implemented: Live Answer Assistant

- Windows 11 Live Captions reading and Enter ON/OFF control.
- GPT answer generation in terminal using OpenAI API.
- Product Owner / Backend Engineer role selection and context separation.
- Caption completion detection and duplicate filtering.
- Markdown knowledge lookup from `knowledge/product-owner/` and `knowledge/backend/`.
- Short-term conversation context and follow-up question support.

These capabilities form a useful starting point; they do **not** constitute a fully implemented Interview Coach mode.

## Not yet implemented in captogpt

| Priority | Proposed feature | Acceptance criteria |
| --- | --- | --- |
| P0 | **Mode selection** | User can select *Live Answer Assistant* (existing behavior) or *Interview Coach Agent* (new mode). |
| P0 | **Session setup** | Choose interview role, difficulty, question count, language and optional CV/job description. |
| P0 | **Coach Orchestrator** | Owns session plan, question/turn counters and routing between planner, generator, evaluator and decision engine. |
| P0 | **GPT Planner** | Builds a question/competency plan tailored to role and session settings. |
| P0 | **Question Generator** | Produces a relevant question per turn; avoids repeating answered questions. |
| P0 | **Answer Evaluator** | Scores an answer 1–5 against five explicit criteria and returns evidence-based feedback. |
| P0 | **Decision Engine** | Chooses FOLLOW_UP, RETRY, NEXT or FINISH using evaluation outcomes and configured limits. Current caption retry logic is unrelated. |
| P0 | **Interactive coaching loop** | Ask → capture answer → evaluate → feedback → choose next action, without replacing the current answer-assistant flow. |
| P1 | **Persistent session state** | Stores questions, turns, progress, per-criterion scores and follow-up/retry counts; enables resume. |
| P1 | **Session JSON** | Export complete session history, answers and evaluation results as JSON. |
| P1 | **Markdown report** | Provide summary scores, strengths, gaps, practice recommendations and next-session plan. |
| P1 | **CV and job description inputs** | Optional local documents inform planning, generation and role-fit evaluation. |
| P1 | **Session-level knowledge retrieval** | Reuse the existing Markdown knowledge base for coaching questions and evaluation, with appropriate contextual retrieval. |
| P2 | **Evaluation and safety tests** | Verify score consistency, deterministic routing, maximum retries, data handling and no regressions to Live Answer mode. |

## Five scoring criteria from Figma

1. Relevance to the question.
2. Domain/technical knowledge.
3. Structure and clarity.
4. Examples and evidence.
5. Fit to the selected role / job description.

## Suggested delivery order

**Phase 1 — Working coach loop:** add mode selection, session settings, orchestration, planner, question generator, evaluator and decision engine. Retain Live Answer Assistant unchanged.

**Phase 2 — Traceability:** persist structured session state, JSON and Markdown report, and allow optional CV / JD context.

**Phase 3 — Quality:** strengthen role-specific evaluation, retrieval, tests and retry behavior.

## Architecture note

A **single Coach Orchestrator with specialized AI modules** is sufficient initially. Calling several model prompts does not automatically make this a multi-agent system with autonomous actors. Human control, transparent scoring and predictable state transitions are more important than autonomous tool execution at this stage.

**Source diagram:** https://www.figma.com/design/eVmB2S0UTg8IP2yllKNH4O/temp?node-id=221-31&t=6eljU6Qq20O89JYw-4
