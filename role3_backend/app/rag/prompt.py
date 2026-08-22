"""
Prompt builder for the RAG harness.

Constructs the system prompt and user message injected into Groq.
Keeps prompt logic isolated so it can be iterated without touching orchestrator code.
"""

from app.schemas import DocumentChunk

# JSON schema that Groq must follow (JSON mode).
# Maps to app.schemas.LLMAnswer
RESPONSE_FORMAT_INSTRUCTION = """
Respond ONLY with a valid JSON object matching this exact schema, with no extra text:
{
  "answer": "<your answer string>",
  "confidence": <float between 0.0 and 1.0>,
  "citations": ["<doc_id_1>", "<doc_id_2>"],
  "grounded": <true or false>
}
"""

SYSTEM_PROMPT = f"""You are a helpful, intelligent, multilingual AI assistant for SONAR RAG.

Rules you MUST follow:
1. Answer EVERY user question clearly, accurately, and politely.
2. If the provided CONTEXT contains relevant facts, use them to ground your answer, set "grounded" to true, and list the doc_ids in "citations".
3. If the provided context is irrelevant or missing, answer using your general knowledge, set "grounded" to false, and leave "citations" as an empty list [].
4. ALWAYS respond in the SAME LANGUAGE as the user's question (e.g., Hindi for Hindi queries, Assamese for Assamese, Marathi for Marathi, English for English, etc.).
5. Keep your answer concise (2 to 4 sentences).

{RESPONSE_FORMAT_INSTRUCTION}"""


def build_prompt(query: str, chunks: list[DocumentChunk]) -> str:
    """
    Builds the user-turn message containing:
      - the retrieved context blocks (numbered, with doc_id and similarity)
      - the user's query

    Returns a single string to be sent as the user message to Groq.
    """
    context_block = "\n\n".join(
        f"[Context {i + 1}] (doc_id={chunk.doc_id}, similarity={chunk.effective_score:.2f})\n{chunk.text}"
        for i, chunk in enumerate(chunks)
    )

    return (
        f"CONTEXT:\n{context_block}\n\n"
        f"QUESTION: {query}\n\n"
        "Answer strictly from the context above and return valid JSON only."
    )
