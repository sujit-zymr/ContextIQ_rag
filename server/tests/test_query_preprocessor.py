import unittest
from unittest.mock import patch

from app.retrieval.query_preprocessor import normalize_query


class QueryPreprocessorTests(unittest.TestCase):

    def test_normalizes_misspelled_query(self):
        fake_vocab = frozenset(["attendance", "discipline", "examination", "principal", "admission"])
        fake_dict = frozenset(["what", "is", "the", "policy", "for", "students"])

        with patch("app.retrieval.query_preprocessor.get_corpus_vocabulary", return_value=fake_vocab), \
             patch("app.retrieval.query_preprocessor.get_system_dictionary", return_value=fake_dict):

            # "attendence" -> "attendance"
            result = normalize_query("What is attendence policy?")
            self.assertEqual(result, "What is attendance policy?")

            # "princpal" -> "principal"
            result2 = normalize_query("Who is the princpal?")
            self.assertEqual(result2, "Who is the principal?")

            # "admisson" -> "admission"
            result3 = normalize_query("What is the admisson procedure?")
            self.assertEqual(result3, "What is the admission procedure?")

    def test_preserves_correct_queries(self):
        fake_vocab = frozenset(["attendance", "policy"])
        fake_dict = frozenset(["what", "is", "the", "policy"])

        with patch("app.retrieval.query_preprocessor.get_corpus_vocabulary", return_value=fake_vocab), \
             patch("app.retrieval.query_preprocessor.get_system_dictionary", return_value=fake_dict):

            result = normalize_query("What is attendance policy?")
            self.assertEqual(result, "What is attendance policy?")

    def test_handles_empty_or_whitespace_query(self):
        self.assertEqual(normalize_query(""), "")
        self.assertEqual(normalize_query("   "), "   ")
        self.assertIsNone(normalize_query(None))

    def test_preserves_casing(self):
        fake_vocab = frozenset(["attendance"])
        fake_dict = frozenset(["what", "is", "policy"])

        with patch("app.retrieval.query_preprocessor.get_corpus_vocabulary", return_value=fake_vocab), \
             patch("app.retrieval.query_preprocessor.get_system_dictionary", return_value=fake_dict):

            self.assertEqual(normalize_query("Attendence Policy"), "Attendance Policy")
            self.assertEqual(normalize_query("ATTENDENCE POLICY"), "ATTENDANCE POLICY")


if __name__ == "__main__":
    unittest.main()
