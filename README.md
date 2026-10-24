# Live Caption Enter Toggle

Capture Windows Live Captions and send to GPT in real-time while capture is ON.

## Figma architecture & planned features

**Please open and review the [Interview Coach Agent architecture and workflow diagram in Figma (node 221:31)](https://www.figma.com/design/eVmB2S0UTg8IP2yllKNH4O/temp?node-id=221-31&t=6eljU6Qq20O89JYw-4) first.** The diagram makes it much easier to understand the end-to-end flow, the roles of the Coach Orchestrator, GPT Planner, Question Generator, Answer Evaluator, Decision Engine, and how these components connect to Windows Live Captions, OpenAI, and the knowledge base.

**Important implementation status:** This repository currently implements the **Live Answer Assistant** flow. The **Interview Coach Agent** shown in the Figma diagram is the *proposed target architecture*, not a completed feature. For the list of missing components and implementation priorities, see [Interview Coach roadmap](docs/INTERVIEW_COACH_ROADMAP.md).

## Solution Architecture & RAG Implementation

**Use case:** A Windows interview assistant converts live spoken questions to captions, retrieves relevant locally maintained role-specific knowledge and sends bounded reference context to GPT to produce an answer. This is an application of **Retrieval-Augmented Generation (RAG)**, not model training or fine-tuning.

**Implemented RAG flow (single horizontal line):**

`Windows Live Captions → Question/domain detection → Local Markdown sections → Keyword/phrase ranking → Top relevant context (bounded) → GPT completion → Answer`

**Implemented architecture decisions**
- **Input integration:** Windows Live Captions are read through Windows UI automation. The operator toggles sending with Enter; this is not a recording/transcription server and depends on captions being available.
- **Knowledge ownership:** `knowledge/backend/` and `knowledge/product-owner/` contain human-editable Markdown reference content. Documents are loaded on startup and split into heading-level searchable sections.
- **Retriever:** `knowledge_base.py` normalizes Vietnamese accents, calculates deterministic keyword and phrase-overlap scores, filters by domain and adds source/section labels to the selected context. The default search returns at most three sections within a character budget; Product Owner mode uses two Product Owner sections plus an optional Backend section.
- **Generation:** `GPTProcessor.process` appends the retrieved material as labeled reference knowledge to an OpenAI Chat Completions call, separately from the system instructions. If no section matches, the assistant can still answer using the base system prompt.
- **Evaluation and traceability:** Unit tests exercise section loading, retrieval ranking, role selection and injection of context into model messages using a fake model client. Local source labels aid manual verification; they are not a formal groundedness benchmark.
- **Security and cost trade-offs:** Limiting retrieved text bounds token usage, but the selected caption/knowledge content is transmitted to an external model. Do not send confidential personal or employer data without permission; keep model keys outside Git. Add masking, access policy, observable token/latency metrics and consent controls before organizational deployment.
- **Production roadmap (not implemented):** For large corpora add incremental indexing, embeddings, vector or hybrid search, reranking, retrieval quality metrics, answer citations, redaction, latency/cost monitoring and authenticated multi-user operation.

**Important implementation boundary:** This is **lexical RAG (keyword and phrase matching)**. It does **not** currently use embeddings, FAISS, a vector database, semantic similarity ranking or vector retriever. A separate Interview Coach Agent architecture in Figma is planned, not implemented; this repository implements the Live Answer Assistant.

## What this project does

- Press `Enter` once: start collecting captions and send updates to GPT immediately.
- Press `Enter` again: stop sending.
- Press `Ctrl + C`: exit.

This matches your flow: Enter toggles ON/OFF, and ON mode sends continuously.

## Requirements

- Windows 11 (Live Captions available)
- Python 3.10+
- OpenAI API key

## Setup (PowerShell)

Run these commands in the project folder:

```powershell
git clone https://github.com/ydangishere/captogpt.git
cd captogpt
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY="your_openai_api_key_here"
```

Purpose:

- `python -m venv .venv`: create isolated Python environment.
- `Activate.ps1`: activate that environment for this terminal.
- `pip install -r requirements.txt`: install all required packages.
- `OPENAI_API_KEY`: allow the app to call GPT.

## Run (PowerShell)

```powershell
cd path\to\captogpt
.\.venv\Scripts\Activate.ps1
python .\live_caption_enter_toggle.py
```

Purpose:

- Start the module and listen for global Enter key toggles.

## Quick run option

You can also double-click `start.bat`.

To make the API key available when double-clicking `start.bat`, save it once
from PowerShell, then close and reopen the terminal:

```powershell
setx OPENAI_API_KEY "your_openai_api_key_here"
```

Purpose:

- Auto-create venv (if missing), install dependencies, and start the app.

## Usage

1. Open Live Captions with `Ctrl + Win + L`.
2. In the running terminal, press `Enter` to start capture.
3. Speak/play audio in Chrome (or any app).
4. While ON, each new caption update is sent to GPT.
5. Press `Enter` again to stop sending.
6. Read GPT output in terminal.

## Update the knowledge base

Reference knowledge is stored by role instead of being embedded in the Python
script:

```text
knowledge/
  backend/        # Java/Python/backend interview knowledge
  product-owner/  # Product Owner experience and case studies
```

To add or update knowledge:

1. Edit an existing `.md` file or add a new one under the matching role folder.
2. Use `##` headings to separate searchable topics.
3. Restart the app so it reloads the files.

The app detects Product Owner questions from signals such as roadmap, backlog,
prioritization, discovery, stakeholder, user story, and product metrics. It then
switches to the Product Owner system prompt and searches only
`knowledge/product-owner/`. Backend questions continue using the existing
backend prompt and `knowledge/backend/`. Follow-up questions keep the recent
context for the selected role.

For every completed caption, at most three relevant sections are sent to GPT.
If a role folder has no matching knowledge, GPT still answers using that role's
system prompt. The way you start, stop, and use the app does not change.

## Notes

- Live Captions is system-level, not Chrome-only.
- If no captions appear, make sure Live Captions is open and receiving audio.
