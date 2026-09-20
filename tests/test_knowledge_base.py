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
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"
            base = LocalKnowledgeBase(missing)

            self.assertEqual("", base.search("Kafka failure"))

    def test_limits_results_to_three_sections(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "topics.md").write_text(
                "\n\n".join(
                    f"## Kafka topic {index}\nKafka consumer message partition {index}"
                    for index in range(5)
                ),
                encoding="utf-8",
            )

            base = LocalKnowledgeBase(root)
            result = base.search("Kafka consumer message", limit=3)

            self.assertEqual(3, result.count("[Source:"))

    def test_respects_maximum_context_size(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "large.md").write_text(
                "## Kafka\n" + ("Kafka consumer message failure. " * 50),
                encoding="utf-8",
            )

            base = LocalKnowledgeBase(root)
            result = base.search("Kafka consumer failure", max_chars=180)

            self.assertLessEqual(len(result), 180)
            self.assertIn("Kafka", result)

    def test_repository_knowledge_contains_all_migrated_topics(self):
        root = Path(__file__).resolve().parents[1] / "knowledge"
        base = LocalKnowledgeBase(root)
        queries_and_titles = (
            ("When should I choose MongoDB for a farm sensor schema?", "MongoDB"),
            ("How do you scale a Spring Boot REST API?", "Spring Boot"),
            ("How do microservices CI/CD recover from production failure?", "Microservices"),
            ("How does Kafka handle IoT messages with consumer groups and DLQ?", "Kafka"),
            ("How do you balance MVP product ownership and technical debt?", "MVP"),
        )

        for query, expected_title in queries_and_titles:
            with self.subTest(query=query):
                self.assertIn(expected_title, base.search(query))

    def test_search_can_be_scoped_to_a_role_directory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = root / "backend"
            product_owner = root / "product-owner"
            backend.mkdir()
            product_owner.mkdir()
            (backend / "cases.md").write_text(
                "## Backend roadmap\nKafka platform roadmap and backlog.",
                encoding="utf-8",
            )
            (product_owner / "cases.md").write_text(
                "## Product roadmap\nPrioritize roadmap using user impact.",
                encoding="utf-8",
            )

            base = LocalKnowledgeBase(root)
            result = base.search(
                "How do you prioritize the roadmap?",
                domain="product-owner",
            )

            self.assertIn("Product roadmap", result)
            self.assertNotIn("Backend roadmap", result)
