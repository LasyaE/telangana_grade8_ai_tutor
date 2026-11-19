"""Retrieve and generate exam-ready answers from Telangana Class 8 textbooks."""

import requests
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

from config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    TOP_K,
)

_embedder = None
_collection = None

REFUSAL = (
    "I couldn't find enough supporting information in the selected "
    "Class 8 textbook to prepare a reliable answer. Please try another "
    "question or check the selected subject."
)

MARK_SETTINGS = {

    2: {"num_predict": 220, "length": "very short"},
    4: {"num_predict": 500, "length": "moderate"},
    8: {"num_predict": 1000, "length": "detailed"},

}


def get_resources():
    global _embedder, _collection

    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)

    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = client.get_collection(COLLECTION_NAME)

    return _embedder, _collection


def retrieve(question: str, subject: str = "All subjects", top_k: int = TOP_K):
    embedder, collection = get_resources()

    query_vector = embedder.encode(
        [question],
        normalize_embeddings=True
    ).tolist()[0]

    kwargs = {
        "query_embeddings": [query_vector],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }

    if subject != "All subjects":
        kwargs["where"] = {"subject": subject}

    result = collection.query(**kwargs)
    hits = []

    if not result["documents"] or not result["documents"][0]:
        return hits

    for i, doc in enumerate(result["documents"][0]):
        hits.append({
            "text": doc,
            "metadata": result["metadatas"][0][i],
            "distance": result["distances"][0][i],
        })

    return hits


def call_ollama(messages, temperature=0.1, num_predict=350):
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        },
        timeout=300,
    )

    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def answer_question(
    question: str,
    subject: str = "All subjects",
    marks: int = 4,
):
    question = question.strip()

    if not question:
        return "Please enter a question.", []

    if marks not in MARK_SETTINGS:
        marks = 4


    hits = retrieve(question, subject)

    # Save retrieved textbook passages in the project folder
    debug_file = Path(__file__).resolve().parent / "retrieval_debug.txt"

    with open(debug_file, "a", encoding="utf-8") as f:
        f.write("\n\n========== RETRIEVAL DEBUG ==========\n")
        f.write(f"Question: {question}\n")
        f.write(f"Selected subject: {subject}\n")
        f.write(f"Retrieved passages: {len(hits)}\n")

        for i, hit in enumerate(hits, start=1):
            f.write(f"\n--- Retrieved Passage {i} ---\n")
            f.write(f"Subject: {hit['metadata'].get('subject')}\n")
            f.write(f"Page: {hit['metadata'].get('page')}\n")
            f.write(f"Distance: {hit['distance']}\n")
            f.write(f"Text:\n{hit['text']}\n")

        f.write("====================================\n")


    if not hits:
        return REFUSAL, []

    context_parts = []
    for n, hit in enumerate(hits, start=1):
        metadata = hit["metadata"]
        context_parts.append(
            f"[Passage {n} | Subject: {metadata.get('subject')} | "
            f"Textbook: {metadata.get('source_file')} | "
            f"Page: {metadata.get('page')}]\n{hit['text']}"
        )

    context = "\n\n".join(context_parts)
    settings = MARK_SETTINGS[marks]

    system_prompt = f"""
You are an experienced Telangana State Board Class VIII examination tutor.

Prepare a clear, correct, well-organised answer suitable for a student to
write in a public examination.

SOURCE AND ACCURACY RULES:
1. Use only information supported by the supplied textbook passages.
2. First decide whether the passages are relevant and contain enough
   information to answer the question at the requested mark level.
3. If the passages are irrelevant or insufficient, do not guess. Say:
   "{REFUSAL}"
4. You may explain, paraphrase, organise and combine supported information.
5. Preserve important textbook terms, definitions, names and scientific
   vocabulary. Do not replace precise terms with vague wording.
6. Do not add facts from general knowledge, even if they are scientifically
   correct, unless the supplied passages support them.
7. Do not repeat the same point in different words.
8. Use complete, grammatically correct sentences and clear headings or
   numbered points where appropriate.
9. Do not mention retrieval, AI, prompts or the passages in the answer.
10. Do not invent examples, diagrams, equations or page references.
11. Identify every relevant type, method, category, step or component
    explicitly described in the supplied textbook information.

12. When the question asks for "types", "methods" or "kinds",
    include all relevant types supported by the supplied information.
    Do not arbitrarily omit a type.

13. Do not classify related information as a type unless the textbook
    explicitly identifies it as one. For example, water-lifting devices
    and ancient agricultural practices must not automatically be
    presented as types of irrigation.

14. Never invent advantages, disadvantages, popularity, efficiency,
    recommendations or uses that are not supported by the textbook.

15. Do not repeat the same explanation under multiple headings.

16. For 8-mark answers, explain each relevant textbook type separately
    and include its definition and working method wherever available.

17. Before completing the answer, check that all relevant textbook
    points have been covered and that no unsupported claims are included.

MARK-WISE FORMAT:

2 MARKS:
- Give a direct and concise answer.
- If the question asks for types, list their names.
- Add a single-line definition for each relevant type.
- Avoid lengthy introductions and conclusions.
- Include only the essential textbook information.

4 MARKS:
- Start with a brief introduction or definition.
- Explain the important points in short, clear sentences.
- Include all relevant types or steps when asked.
- Avoid unnecessary repetition.

8 MARKS:
- Give a clear introduction.
- Explain every relevant textbook point under separate headings.
- Include definitions, working methods, features and textbook examples
  wherever the supplied information supports them.
- Give a short conclusion when appropriate.

GENERAL RULES:
- Match the answer length to the marks.
- Never omit an important textbook point merely to shorten the answer.
- Never add unsupported information to make an answer longer.
- Do not repeat the same information under different headings.
- Prioritise correctness, completeness and clarity.

    """


    user_prompt = f"""
Selected subject: {subject}
Required answer length: {marks} marks ({settings["length"]})

Student's question:
{question}

Textbook information:
{context}

Write the exam-ready answer for {marks} marks. If the textbook information
does not adequately support an answer at this level, say so clearly rather
than filling gaps with outside knowledge.
"""

    try:
        answer = call_ollama(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            num_predict=settings["num_predict"],
        )
        return answer, hits

    except requests.RequestException as error:
        return (
            f"Could not generate an answer because Ollama encountered an error: {error}",
            [],
        )
