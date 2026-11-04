# ContextIQ_rag

## Evaluate the RAG pipeline with Ragas

Install the project dependencies (Ragas is included in `requirements.txt`):

```bash
pip install -r requirements.txt
```

Add `NVIDIA_API_KEY` to `.env`. Ragas uses the configured NVIDIA OpenAI-compatible
chat endpoint as its evaluator and the same local `all-MiniLM-L6-v2` model as the
pipeline for embedding-based scores. Set `RAGAS_MODEL` in `.env` if you want a
different model for evaluation; otherwise it uses `NVIDIA_MODEL`.

Run the complete evaluation against the questions in
`app/evaluation_data/policy_questions.json`:

```bash
python -m app.main evaluate
```

This retrieves the top five chunks and generates an answer for each question
before scoring. Use `--top-k` to change the number of retrieved chunks. To score
an already collected dataset without rerunning retrieval and generation, pass it
with `--dataset`:

```bash
python -m app.main evaluate --dataset evaluation_data/ragas_dataset.json
```

Each run writes a CSV with scores for every question and a JSON summary of the
average scores under `evaluation_data/ragas_results/`. The evaluation reports:

- **Context precision**: whether relevant retrieved chunks rank near the top.
- **Context recall**: whether the retrieved chunks contain information needed
  by the reference answer.
- **Context entity recall**: whether important entities from the reference are
  present in retrieved chunks.
- **Faithfulness**: whether the generated answer is supported by retrieved
  context.
- **Noise sensitivity**: how often irrelevant context leads to incorrect
  claims; lower is better for this metric.
- **Answer relevancy**: whether the answer addresses the question.
- **Factual correctness**: whether the answer's claims match the reference.
- **Semantic similarity**: how closely the answer's meaning matches the
  reference.

Ragas uses the NVIDIA model for LLM-judged metrics, so evaluation makes extra
model API calls and may incur usage charges. The embedding-based metrics run
locally using the same sentence-transformer as retrieval.

Evaluation runs with four concurrent metric workers and a five-minute request
timeout to reduce evaluator overload. Override these defaults with
`RAGAS_MAX_WORKERS` and `RAGAS_TIMEOUT_SECONDS` in `.env`. If an individual
metric request still times out, the run continues and records that score as
missing while preserving successful scores.
