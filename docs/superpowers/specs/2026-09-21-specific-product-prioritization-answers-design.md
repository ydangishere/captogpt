# Natural Product Prioritization Answers

## Goal

Keep Product Owner interview answers natural while giving the model a light
prioritization flow to follow. Improve specificity across short follow-up
questions without forcing a rigid template, inventing personal history, or
claiming measured outcomes.

## Considered approaches

1. **Light prompt guidance (selected).** Add a short prioritization flow to the
   existing Product Owner prompt while allowing the model to select only the
   details that help answer the question. This preserves natural wording and is
   the smallest change.
2. **Add a hard-coded WWE Champions case to the knowledge base.** This could
   produce more specific answers, but it risks presenting an unverified case as
   the user's real experience.
3. **Post-process generated answers.** This could enforce structure after model
   generation, but it would add complexity and could damage otherwise natural
   interview wording.

## Design

Add a short instruction to `PRODUCT_OWNER_EXAMPLE_PROMPT` suggesting this flow
when useful: user problem and evidence, decision, then trade-off or expected
result. These are guidance points rather than mandatory fields. The model may
omit a point when it does not help answer the current question.

When the user asks for an example, encourage one concrete feature, the choice
made, and why. Do not require a competing alternative, a metric, or a fixed
answer structure in every response. Existing instructions against fabricated
measurements and undocumented events continue to apply.

For follow-ups such as "Please, more specific" or "Give me a specific example",
ask the model to add one useful new detail instead of paraphrasing the prior
answer. Existing language matching, role selection, retrieval, and response
length behavior remain unchanged.

## Testing

Add an integration-level prompt construction test that runs `GPTProcessor` with
a fake OpenAI client in Product Owner mode and verifies that the system message
contains the new lightweight prioritization and follow-up guidance. Run the complete
unit test suite after the focused test passes.

## Success criteria

- Product prioritization prompts suggest a compact, natural decision flow.
- The prompt explicitly says the flow is guidance, not a mandatory template.
- Example prompts encourage a concrete feature, decision, and reason without
  requiring every possible detail.
- Follow-up prompts ask for one useful new detail instead of repetition.
- No unverified personal experience or measured result is added.
- All automated tests pass.
