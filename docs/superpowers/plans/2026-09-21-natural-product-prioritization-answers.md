# Natural Product Prioritization Answers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guide Product Owner prioritization answers through a light, natural decision flow without forcing a rigid response template.

**Architecture:** Keep the existing prompt-construction architecture unchanged. Add one regression test around the generated Product Owner system message, then minimally extend `PRODUCT_OWNER_EXAMPLE_PROMPT` with optional flow guidance and a non-repetitive follow-up rule.

**Tech Stack:** Python 3.10+, `unittest`, OpenAI Chat Completions request construction

---

### Task 1: Add lightweight prioritization guidance

**Files:**
- Modify: `tests/test_gpt_knowledge_integration.py`
- Modify: `live_caption_enter_toggle.py:306-340`

- [ ] **Step 1: Write the failing prompt-construction test**

Add this method to `GPTKnowledgeIntegrationTests`:

```python
def test_product_owner_prompt_uses_light_prioritization_guidance(self):
    client = FakeClient()
    processor = GPTProcessor(
        client=client,
        knowledge_base=FakeKnowledgeBase(""),
    )

    processor.process(
        "How do you prioritize a product backlog?",
        domain="product_owner",
    )

    system_message = client.completions.last_request["messages"][0]["content"]
    self.assertIn("light flow when useful, not a mandatory template", system_message)
    self.assertIn("user problem and evidence -> decision", system_message)
    self.assertIn("one useful new decision detail", system_message)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m unittest tests.test_gpt_knowledge_integration.GPTKnowledgeIntegrationTests.test_product_owner_prompt_uses_light_prioritization_guidance -v
```

Expected: `FAIL` because the current system message does not contain the new lightweight guidance.

- [ ] **Step 3: Add the minimal prompt guidance**

Insert the following text into `PRODUCT_OWNER_EXAMPLE_PROMPT` after the existing instruction to answer the actual question first:

```python
" For prioritization questions, use this as a light flow when useful, not a mandatory template: "
"user problem and evidence -> decision -> trade-off or expected result. Omit any "
"point that does not help answer the current question. For a specific example, "
"prefer one concrete feature, the choice made, and why; do not force every possible "
"detail or metric. For follow-ups asking for more specificity or an example, add "
"one useful new decision detail instead of paraphrasing the previous answer. "
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```powershell
python -m unittest tests.test_gpt_knowledge_integration.GPTKnowledgeIntegrationTests.test_product_owner_prompt_uses_light_prioritization_guidance -v
```

Expected: `OK` with one passing test.

- [ ] **Step 5: Run the full test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass with no errors or failures.

- [ ] **Step 6: Inspect the final diff and commit**

Run:

```powershell
git diff --check
git diff -- live_caption_enter_toggle.py tests/test_gpt_knowledge_integration.py
git add -- live_caption_enter_toggle.py tests/test_gpt_knowledge_integration.py
git commit -m "fix: guide product prioritization answers"
```

Expected: whitespace check exits successfully and the commit contains only the prompt and regression-test changes.
