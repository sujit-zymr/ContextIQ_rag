"""Tests for chunking, context passages and the full-text query (no database)."""

import unittest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.ingestion.chunker import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    chunk_documents,
    join_pages,
)
from app.retrieval import similarity_search
from app.retrieval.passages import (
    build_passage,
    join_overlapping,
    select_hits,
    window_indexes,
)


def hit(index, doc="d1", score=1.0, page=None):
    return {"document_id": doc, "chunk_index": index, "content": f"chunk {index}",
            "metadata": {}, "page": page, "rerank_score": score}


def row(text, page=None, section_path=None):
    metadata = {"page": page}
    if section_path:
        metadata["section_path"] = section_path
    return {"content": text, "metadata": metadata}


class PassageTests(unittest.TestCase):

    def test_nearby_hits_merge_and_do_not_take_extra_slots(self):
        groups = select_hits([hit(10), hit(11), hit(30), hit(12), hit(50)], top_k=2, window=1)
        self.assertEqual([[h["chunk_index"] for h in g] for g in groups], [[10, 11, 12], [30]])

    def test_groups_do_not_chain_across_the_document(self):
        # 10 -> 12 -> 14 -> 16 would chain if distance were measured from any member.
        groups = select_hits([hit(10), hit(12), hit(14), hit(16)], top_k=5, window=1)
        self.assertEqual([[h["chunk_index"] for h in g] for g in groups], [[10, 12], [14, 16]])

    def test_window_is_capped_around_the_best_hit(self):
        self.assertEqual(window_indexes([hit(10)], 1), [9, 10, 11])
        self.assertEqual(window_indexes([hit(10), hit(12)], 1), [9, 10, 11, 12])
        self.assertEqual(window_indexes([hit(0)], 1), [0, 1])

    def test_join_overlapping_removes_repeated_overlap(self):
        self.assertEqual(join_overlapping("alpha beta gamma", "beta gamma delta"), "alpha beta gamma delta")
        self.assertEqual(join_overlapping("one", "two"), "one\ntwo")

    def test_passage_uses_only_its_own_window(self):
        # Chunks loaded for another passage of the same document must not leak in.
        neighbours = {i: row(f"text {i}", page=i) for i in (9, 10, 11, 29, 30, 31)}
        passage = build_passage([hit(10, page=11)], neighbours, window=1)
        self.assertEqual(passage["chunk_indexes"], [9, 10, 11])
        self.assertNotIn("text 30", passage["content"])
        self.assertEqual(passage["pages"], [10, 11, 12])

    def test_section_header_appears_once_per_passage(self):
        neighbours = {
            1: row("Leave > Planned\n\nfirst part of the rule", section_path="Leave > Planned"),
            2: row("Leave > Planned\n\nthe rule continues", section_path="Leave > Planned"),
        }
        passage = build_passage([hit(1)], neighbours, window=1)
        self.assertEqual(passage["content"].count("Leave > Planned"), 1)
        self.assertIn("the rule continues", passage["content"])

    def test_expansion_falls_back_to_hits_when_loading_fails(self):
        with patch.object(similarity_search, "get_chunks_by_index", side_effect=RuntimeError("db down")):
            passages = similarity_search.expand_to_passages([hit(1), hit(20)], top_k=2, window=1)
        self.assertEqual([p["chunk_index"] for p in passages], [1, 20])

    def test_expansion_requests_each_window_once(self):
        found = {"d1": {i: row(f"text {i}") for i in range(0, 40)}}
        with patch.object(similarity_search, "get_chunks_by_index", return_value=found) as loader:
            passages = similarity_search.expand_to_passages([hit(10), hit(30)], top_k=2, window=1)
        requested = sorted(index for _, index in loader.call_args.args[0])
        self.assertEqual(requested, [9, 10, 11, 29, 30, 31])
        self.assertEqual([p["chunk_indexes"] for p in passages], [[9, 10, 11], [29, 30, 31]])


class ChunkingTests(unittest.TestCase):

    def test_defaults_fit_the_embedding_model(self):
        self.assertEqual((DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP), (1000, 150))

    def test_every_chunk_carries_its_section_path(self):
        body = " ".join(f"Sentence number {i} about planned leave." for i in range(60))
        doc = Document(page_content=body, metadata={"section": "Planned", "section_path": "Leave > Planned"})
        chunks = chunk_documents([doc], chunk_size=300, overlap=50)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(c.page_content.startswith("Leave > Planned\n\n") for c in chunks))

    def test_pdf_pages_are_joined_and_chunks_keep_their_start_page(self):
        pages = [Document(page_content=("Page %d text. " % n) * 30, metadata={"page": n, "source": "x.pdf"})
                 for n in range(3)]
        joined = join_pages(pages)
        self.assertEqual(len(joined), 1)
        chunks = chunk_documents(joined, chunk_size=200, overlap=20)
        self.assertEqual({c.metadata["page"] for c in chunks}, {0, 1, 2})
        self.assertTrue(all("page_starts" not in c.metadata for c in chunks))
        for chunk in chunks:
            self.assertIn(f"Page {chunk.metadata['page']} text", chunk.page_content)


class FullTextQueryTests(unittest.TestCase):

    def test_full_text_query_uses_or_semantics_and_parameters(self):
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []
        connection = MagicMock()
        connection.__enter__.return_value = conn
        with patch.object(similarity_search, "get_connection", return_value=connection), \
             patch.object(similarity_search, "normalize_query", side_effect=lambda q: q):
            similarity_search.search_full_text_chunks("how does authentication work", top_k=5)
        sql, params = conn.execute.call_args.args
        self.assertIn("replace(", sql)
        self.assertIn("' & ', ' | '", sql)
        self.assertEqual(params, ("how does authentication work", 5))


class ApiDefaultsTests(unittest.TestCase):

    def test_send_message_default_top_k_is_five_passages(self):
        from app.api.schemas import SendMessageRequest
        self.assertEqual(SendMessageRequest(content="hi").top_k, 5)


if __name__ == "__main__":
    unittest.main()
