
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

model = None


def get_model():
    global model

    if model is None:
        model = SentenceTransformer(
            MODEL_NAME,
            device="cpu"
        )

    return model


def generate_embeddings(texts):

    embeddings = get_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    return embeddings


def generate_query_embedding(question):

    embedding = get_model().encode(
        question,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    return embedding
