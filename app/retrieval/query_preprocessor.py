"""Query preprocessing and spell-normalization for RAG retrieval."""

import difflib
import logging
import re
from functools import lru_cache
from pathlib import Path

from app.database.connection import get_connection

logger = logging.getLogger(__name__)

# Standard common English words that should never be replaced
_COMMON_ENGLISH_WORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "explain", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's",
    "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how",
    "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "tell", "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "describe", "details", "give", "list", "name",
    "policy", "rules", "rule", "guidelines", "procedure", "process",
})


@lru_cache(maxsize=1)
def get_system_dictionary() -> frozenset[str]:
    """Load standard system dictionary words if available."""
    dict_paths = [
        Path("/usr/share/dict/words"),
        Path("/usr/dict/words"),
    ]
    for p in dict_paths:
        if p.is_file():
            try:
                words = p.read_text(encoding="utf-8", errors="replace").lower().splitlines()
                return frozenset(w.strip() for w in words if w.strip())
            except Exception:
                pass
    return _COMMON_ENGLISH_WORDS


@lru_cache(maxsize=1)
def get_corpus_vocabulary() -> frozenset[str]:
    """Extract unique words from indexed document chunks in PostgreSQL."""
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT content FROM document_chunks").fetchall()
        vocab: set[str] = set()
        for row in rows:
            if row[0]:
                vocab.update(re.findall(r"[a-zA-Z]{3,}", row[0].lower()))
        return frozenset(vocab)
    except Exception as exc:
        logger.warning("Could not load corpus vocabulary from database: %s", exc)
        return frozenset()


def clear_vocabulary_cache() -> None:
    """Clear cached vocabulary (call after ingesting or reindexing documents)."""
    get_corpus_vocabulary.cache_clear()


def normalize_query(query: str, cutoff: float = 0.75) -> str:
    """Correct spelling mistakes in query using the corpus vocabulary.

    Words in standard English dictionaries or already in the corpus vocabulary
    are left unchanged. Only unrecognized words that closely match corpus terms
    are corrected.
    """
    if not query or not query.strip():
        return query

    corpus_vocab = get_corpus_vocabulary()
    if not corpus_vocab:
        return query

    system_dict = get_system_dictionary()
    known_words = system_dict | corpus_vocab

    tokens = re.findall(r"[a-zA-Z]+|[^\w\s]|\s+", query)
    corrected_tokens = []
    has_changes = False

    for token in tokens:
        lower = token.lower()
        if re.match(r"^[a-zA-Z]{3,}$", token) and lower not in known_words:
            matches = difflib.get_close_matches(lower, corpus_vocab, n=1, cutoff=cutoff)
            if matches:
                replacement = matches[0]
                if token.isupper():
                    replacement = replacement.upper()
                elif token.istitle():
                    replacement = replacement.title()
                corrected_tokens.append(replacement)
                has_changes = True
                continue
        corrected_tokens.append(token)

    normalized = "".join(corrected_tokens)
    if has_changes:
        logger.info("Normalized query from %r to %r", query, normalized)
    return normalized
