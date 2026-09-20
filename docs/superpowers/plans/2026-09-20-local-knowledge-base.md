# Local Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move hard-coded interview knowledge into editable Markdown files and retrieve only relevant local sections for each caption.

**Architecture:** A focused `LocalKnowledgeBase` loads and chunks Markdown at application startup, ranks sections locally using normalized phrase and keyword overlap, and returns a bounded context string. `GPTProcessor` injects that retrieved context into the existing OpenAI request while keeping behavioral instructions in the system prompt.

**Tech Stack:** Python 3.10+, standard library, existing OpenAI client, `unittest`

---

## File Structure

- Create `knowledge_base.py`: Markdown loading, chunking, normalization, ranking, and bounded retrieval.
- Create `knowledge/backend-interview.md`: migrated interview reference knowledge.
- Create `tests/test_knowledge_base.py`: local knowledge-base behavior.
- Create `tests/test_gpt_knowledge_integration.py`: prompt integration through a fake OpenAI client.
- Modify `live_caption_enter_toggle.py`: initialize and query the knowledge base; remove the embedded memo.
- Modify `README.md`: document how to update knowledge.

### Task 1: Local retrieval behavior

**Files:**
- Create: `tests/test_knowledge_base.py`
- Create: `knowledge_base.py`

- [ ] **Step 1: Write failing tests**

Create tests that require `LocalKnowledgeBase` to load `*.md`, split `##` sections, rank a Kafka section above MongoDB for a Kafka query, return no context for unrelated text, cap results at three sections, and tolerate a missing directory.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from knowledge_base import LocalKnowledgeBase


class LocalKnowledgeBaseTests(TestCase):
    def test_retrieves_only_relevant_sections(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backend.md").write_text(
                "## Kafka\nconsumer group partition DLQ message failure\n\n"
                "## MongoDB\ndocument schema aggregation pipeline\n",
                encoding="utf-8",
            )
            base = LocalKnowledgeBase(root)
            result = base.search("How do you handle Kafka message failure?")
            self.assertIn("Kafka", result)
            self.assertNotIn("MongoDB", result)

    def test_missing_directory_returns_empty_context(self):
        base = LocalKnowledgeBase(Path("missing-knowledge-directory"))
        self.assertEqual("", base.search("Kafka failure"))
```

- [ ] **Step 2: Verify RED**

Run: `\.venv\Scripts\python.exe -m unittest tests.test_knowledge_base -v`

Expected: FAIL because `knowledge_base` does not exist.

- [ ] **Step 3: Implement the minimal retriever**

Implement these public boundaries:

```python
@dataclass(frozen=True)
class KnowledgeSection:
    source: str
    title: str
    content: str


class LocalKnowledgeBase:
    def __init__(self, root: Path): ...
    def search(self, query: str, limit: int = 3, max_chars: int = 4000) -> str: ...
```

Loading happens in `__init__`. Only positive-overlap sections are returned. Output includes source and section title and never exceeds `max_chars`.

- [ ] **Step 4: Verify GREEN**

Run: `\.venv\Scripts\python.exe -m unittest tests.test_knowledge_base -v`

Expected: all local retrieval tests PASS.

### Task 2: Migrate the embedded knowledge

**Files:**
- Create: `knowledge/backend-interview.md`
- Modify: `live_caption_enter_toggle.py`

- [ ] **Step 1: Add a failing migration assertion**

Add a test that loads the repository knowledge directory and retrieves each migrated topic using representative MongoDB, Spring Boot, microservices, Kafka, and product-ownership queries.

- [ ] **Step 2: Verify RED**

Run: `\.venv\Scripts\python.exe -m unittest tests.test_knowledge_base -v`

Expected: FAIL because `knowledge/backend-interview.md` is absent.

- [ ] **Step 3: Create Markdown knowledge and remove the Python memo**

Move every section and statement from `STRUCTURED_INTERVIEW_MEMO` to `knowledge/backend-interview.md`. Delete the constant and `_should_use_structured_interview_memo`; do not move persona or response-format rules because they must remain active for every request.

- [ ] **Step 4: Verify GREEN**

Run: `\.venv\Scripts\python.exe -m unittest tests.test_knowledge_base -v`

Expected: migrated-topic tests PASS.

### Task 3: Integrate retrieval with GPT requests

**Files:**
- Create: `tests/test_gpt_knowledge_integration.py`
- Modify: `live_caption_enter_toggle.py`

- [ ] **Step 1: Write a failing prompt integration test**

Use an injected fake client and fake knowledge base. Call `GPTProcessor.process`, capture the request messages, and assert that relevant reference knowledge is present while an empty retrieval adds no reference block.

```python
processor = GPTProcessor(client=fake_client, knowledge_base=fake_knowledge)
processor.process("How do Kafka consumers recover from failure?")
self.assertIn("REFERENCE KNOWLEDGE", fake_client.last_messages[-1]["content"])
```

- [ ] **Step 2: Verify RED**

Run: `\.venv\Scripts\python.exe -m unittest tests.test_gpt_knowledge_integration -v`

Expected: FAIL because `GPTProcessor` does not accept injected dependencies and does not retrieve local knowledge.

- [ ] **Step 3: Implement minimal integration**

Extend the constructor without breaking current callers:

```python
def __init__(self, model="gpt-4o-mini", client=None, knowledge_base=None):
    self.client = client or OpenAI(api_key=required_api_key)
    self.knowledge_base = knowledge_base or LocalKnowledgeBase(default_knowledge_path)
```

In `process`, call `self.knowledge_base.search(normalized)` once and append the bounded result as clearly labeled reference material to the user message. Reference text cannot override the system instructions.

- [ ] **Step 4: Verify GREEN**

Run: `\.venv\Scripts\python.exe -m unittest tests.test_gpt_knowledge_integration -v`

Expected: prompt integration tests PASS without a network call.

### Task 4: Document and verify the complete feature

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the user workflow**

Document that users edit or add `knowledge/*.md` files, use `##` headings for searchable sections, and restart the application after changes.

- [ ] **Step 2: Run complete verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile .\knowledge_base.py .\live_caption_enter_toggle.py
git diff --check
```

Expected: all tests PASS, compilation exits 0, and diff check reports no errors.

- [ ] **Step 3: Review scope and working tree**

Confirm the original uncommitted changes in `live_caption_enter_toggle.py` and `requirements.txt` remain present and that no `.venv`, cache, or generated file is staged.
