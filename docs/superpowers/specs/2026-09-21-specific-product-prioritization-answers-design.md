# Specific Product Prioritization Answers

## Goal

Make Product Owner interview answers about prioritization concrete and useful,
especially across short follow-up questions, without inventing personal history
or measured outcomes.

## Considered approaches

1. **Prompt-only behavior rule (selected).** Extend the existing Product Owner
   example prompt with an explicit prioritization answer contract. This is the
   smallest change and applies to both initial questions and follow-ups.
2. **Add a hard-coded WWE Champions case to the knowledge base.** This could
   produce more specific answers, but it risks presenting an unverified case as
   the user's real experience.
3. **Post-process generated answers.** This could enforce structure after model
   generation, but it would add complexity and could damage otherwise natural
   interview wording.

## Design

Add instructions to `PRODUCT_OWNER_EXAMPLE_PROMPT` requiring prioritization
answers to identify the user problem, evidence, expected business impact,
effort or dependencies, the decision, and a relevant trade-off. When the user
asks for an example, the answer must name one concrete feature and its competing
alternative, explain why one was selected, and state how success would be
measured without claiming fabricated results.

For follow-ups such as "Please, more specific" or "Give me a specific example",
the response must add new decision detail instead of paraphrasing the prior
answer. Existing language matching, role selection, retrieval, and response
length behavior remain unchanged.

## Testing

Add an integration-level prompt construction test that runs `GPTProcessor` with
a fake OpenAI client in Product Owner mode and verifies that the system message
contains the new prioritization and follow-up requirements. Run the complete
unit test suite after the focused test passes.

## Success criteria

- Product prioritization prompts explicitly demand concrete decision inputs.
- Example prompts demand a competing option, rationale, trade-off, and success
  measurement.
- Follow-up prompts explicitly forbid repeating generic prioritization language.
- No unverified personal experience or measured result is added.
- All automated tests pass.
