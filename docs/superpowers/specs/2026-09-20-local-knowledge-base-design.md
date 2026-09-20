# Local Knowledge Base Design

## Goal

Move the existing backend interview knowledge out of
`live_caption_enter_toggle.py` into editable Markdown files. After the initial
integration, adding or changing knowledge must not require Python edits.

## Storage

- Store knowledge in `knowledge/*.md`.
- Split the current interview memo into topic-based Markdown sections such as
  MongoDB, Spring Boot, microservices, Kafka, and product ownership.
- Treat Markdown files as the source of truth. The application will not write
  to them.

## Retrieval

- Load all Markdown files when the application starts.
- Split documents by Markdown headings into small, independently searchable
  sections.
- Search locally without an additional API request.
- Normalize Vietnamese accents and technical terms, then rank sections using
  phrase and keyword overlap.
- Add at most three relevant sections to a GPT request, with a fixed size cap.
- If nothing is relevant, send no knowledge section.

## Application Integration

- Add a small, isolated local knowledge-base module.
- Initialize it once in `GPTProcessor`.
- Retrieve relevant sections for each completed caption.
- Keep persona and answer-format rules in the system prompt because they are
  behavioral instructions, not reference knowledge.
- Remove the hard-coded `STRUCTURED_INTERVIEW_MEMO` after its content has been
  migrated to Markdown.

## Failure Handling

- A missing or empty `knowledge/` directory must not stop the application.
- An unreadable individual file must be skipped with a warning.
- OpenAI requests must continue with the base prompt when retrieval finds no
  useful section.

## Verification

- Unit tests will prove that documents load, headings become sections,
  relevant topics rank above unrelated topics, and missing storage is safe.
- A prompt-construction test will prove that only retrieved knowledge is added.
- Run the complete test suite and Python syntax compilation before completion.

## User Workflow

1. Add or edit a Markdown file under `knowledge/`.
2. Restart the application.
3. The application loads the updated knowledge automatically.

Live reload while the application is already running is outside this scope.
