from types import SimpleNamespace
from unittest import TestCase

from live_caption_enter_toggle import EnterToggleController, GPTProcessor


class FakeCompletions:
    def __init__(self):
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        message = SimpleNamespace(content="A practical answer")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self):
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


class FakeKnowledgeBase:
    def __init__(self, context):
        self.context = context
        self.queries = []

    def search(self, query, domain=None):
        self.queries.append((query, domain))
        return self.context


class GPTKnowledgeIntegrationTests(TestCase):
    def test_process_adds_only_retrieved_knowledge_to_user_message(self):
        client = FakeClient()
        knowledge = FakeKnowledgeBase(
            "[Source: backend-interview.md > Kafka]\nUse a DLQ for failures."
        )
        processor = GPTProcessor(client=client, knowledge_base=knowledge)

        result = processor.process("How should Kafka handle message failure?")

        self.assertEqual("A practical answer", result)
        self.assertEqual(
            [("How should Kafka handle message failure?", "backend")],
            knowledge.queries,
        )
        user_message = client.completions.last_request["messages"][-1]["content"]
        self.assertIn("REFERENCE KNOWLEDGE", user_message)
        self.assertIn("Use a DLQ for failures.", user_message)

    def test_process_omits_reference_block_when_nothing_matches(self):
        client = FakeClient()
        processor = GPTProcessor(
            client=client,
            knowledge_base=FakeKnowledgeBase(""),
        )

        processor.process("How are you today?")

        user_message = client.completions.last_request["messages"][-1]["content"]
        self.assertNotIn("REFERENCE KNOWLEDGE", user_message)

    def test_detects_product_owner_questions_before_backend_fallback(self):
        self.assertEqual(
            "product_owner",
            GPTProcessor.detect_domain(
                "How do you prioritize a product roadmap and backlog?"
            ),
        )
        self.assertEqual(
            "backend_production",
            GPTProcessor.detect_domain(
                "How does a Kafka consumer handle duplicate messages?"
            ),
        )

    def test_product_owner_domain_switches_role_and_knowledge_scope(self):
        client = FakeClient()
        knowledge = FakeKnowledgeBase(
            "[Source: product-owner/cases.md > Roadmap]\nUse customer impact."
        )
        processor = GPTProcessor(client=client, knowledge_base=knowledge)

        processor.process(
            "How do you prioritize the roadmap?",
            domain="product_owner",
        )

        messages = client.completions.last_request["messages"]
        self.assertIn("Product Owner", messages[0]["content"])
        self.assertNotIn("Senior Backend Engineer", messages[0]["content"])
        self.assertEqual(
            [("How do you prioritize the roadmap?", "product-owner")],
            knowledge.queries,
        )

    def test_controller_keeps_product_owner_followup_context(self):
        controller = EnterToggleController()

        controller.remember_exchange(
            "How do you prioritize a roadmap?",
            "I start with user impact.",
            "product_owner",
        )

        context = controller.get_recent_context_text("product_owner")
        self.assertIn("prioritize a roadmap", context)

    def test_generic_followup_keeps_the_previous_product_owner_role(self):
        controller = EnterToggleController()
        controller.remember_exchange(
            "Which feature should we prioritize on the roadmap?",
            "Start with user impact.",
            "product_owner",
        )

        resolved = controller.resolve_domain_for_request(
            "general",
            True,
            "Why not build both?",
        )

        self.assertEqual("product_owner", resolved)

    def test_detects_short_product_followup_phrases(self):
        self.assertTrue(GPTProcessor.is_followup("Why not build both?"))
        self.assertTrue(
            GPTProcessor.is_followup("Tại sao không làm cả hai?")
        )
