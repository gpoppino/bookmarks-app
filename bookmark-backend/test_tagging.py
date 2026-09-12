"""Unit tests for automatic tag configuration and OpenAI integration."""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from tagging import (
    DEFAULT_OPENAI_MODEL,
    MAX_AUTOMATIC_TAGS,
    OpenAITagSuggester,
    TagSuggestions,
    TaggingContext,
    build_tag_suggester,
    merge_tags,
)


class AutomaticTaggingTests(unittest.TestCase):
    def test_disabled_by_default(self):
        suggester = build_tag_suggester({})
        self.assertFalse(suggester.enabled)
        self.assertEqual(
            suggester.suggest(TaggingContext("example.com", "Title", "", ())),
            [],
        )

    def test_enabled_mode_requires_valid_configuration(self):
        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY is required"):
            build_tag_suggester({"AUTO_TAGGING_ENABLED": "true"})
        with self.assertRaisesRegex(RuntimeError, "must be true or false"):
            build_tag_suggester({"AUTO_TAGGING_ENABLED": "sometimes"})
        with self.assertRaisesRegex(RuntimeError, "positive number"):
            build_tag_suggester(
                {
                    "AUTO_TAGGING_ENABLED": "true",
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_TAGGING_TIMEOUT_SECONDS": "0",
                }
            )

    def test_manual_tags_are_preserved_and_existing_suggestions_are_preferred(self):
        merged = merge_tags(
            [" Manual ", "PYTHON", "manual", "#explicit"],
            ["new-one", "#Python", "new-two", "new-three", "FastAPI"],
            ["python", "fastapi"],
        )
        self.assertEqual(
            merged,
            ["manual", "python", "#explicit", "fastapi", "new-one", "new-two"],
        )

    def test_automatic_tags_are_normalized_and_bounded(self):
        suggestions = [f"  Tag {index}  " for index in range(10)]
        merged = merge_tags([], suggestions, suggestions)
        self.assertEqual(len(merged), MAX_AUTOMATIC_TAGS)
        self.assertEqual(merged[0], "tag 0")

    def test_openai_provider_uses_structured_non_stored_response(self):
        responses = Mock()
        responses.parse.return_value = SimpleNamespace(
            output_parsed=TagSuggestions(tags=["python"])
        )
        client = SimpleNamespace(responses=responses)
        suggester = OpenAITagSuggester("test-key", client=client)

        tags = suggester.suggest(
            TaggingContext(
                "example.com",
                "A title",
                "A description",
                ("python",),
            )
        )

        self.assertEqual(tags, ["python"])
        arguments = responses.parse.call_args.kwargs
        self.assertEqual(arguments["model"], DEFAULT_OPENAI_MODEL)
        self.assertFalse(arguments["store"])
        self.assertIs(arguments["text_format"], TagSuggestions)
        self.assertIn('"existing_tags": ["python"]', arguments["input"][1]["content"])


if __name__ == "__main__":
    unittest.main()
