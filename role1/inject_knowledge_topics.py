"""
inject_knowledge_topics.py
Appends comprehensive knowledge passages for demo topics (RAG, FAISS, Chunking, Latency, STT, Groq)
into the FAISS index and chunk metadata.
"""

import json
from pathlib import Path
import numpy as np
import faiss
from fastembed import TextEmbedding

INDEX_DIR = Path("role1/data/index_minilm")
FAISS_PATH = INDEX_DIR / "faiss.index"
META_PATH = INDEX_DIR / "chunk_meta.jsonl"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

KNOWLEDGE_DOCS = [
    {
        "doc_id": "topic_rag_overview",
        "lang": "en",
        "chunk_id": "rag_001",
        "text": "Retrieval-Augmented Generation (RAG) is an AI architecture that enhances large language models by retrieving relevant authoritative facts and context from an external vector database before generating an answer. Unlike standard LLMs that rely only on static pre-trained weights and risk hallucinations, RAG grounds every response in verified documents with traceable source citations.",
        "metadata": {"topic": "RAG", "category": "architecture"}
    },
    {
        "doc_id": "topic_rag_benefits",
        "lang": "en",
        "chunk_id": "rag_002",
        "text": "The key advantages of RAG include eliminating hallucinations, providing real-time up-to-date domain knowledge without expensive fine-tuning, supporting verifiable citations, and enforcing strict security guardrails through deterministic grounding checks.",
        "metadata": {"topic": "RAG", "category": "advantages"}
    },
    {
        "doc_id": "topic_faiss_vector_index",
        "lang": "en",
        "chunk_id": "faiss_001",
        "text": "FAISS (Facebook AI Similarity Search) is an ultra-high-performance library for efficient dense vector similarity search and clustering. In SONAR, FAISS stores normalized 384-dimensional embeddings and performs exact Inner Product (cosine similarity) search in under 1 millisecond across thousands of multilingual passage chunks.",
        "metadata": {"topic": "FAISS", "category": "retrieval"}
    },
    {
        "doc_id": "topic_chunking_strategies",
        "lang": "en",
        "chunk_id": "chunk_001",
        "text": "Chunking is the process of splitting long source documents into discrete semantic passages before vector embedding. Strategies include fixed-size token chunking, recursive boundary splitting on paragraphs and sentences, and semantic chunking with overlapping windows (e.g. 50-token overlap) to preserve context continuity across chunk boundaries.",
        "metadata": {"topic": "Chunking", "category": "processing"}
    },
    {
        "doc_id": "topic_latency_budget",
        "lang": "en",
        "chunk_id": "lat_001",
        "text": "SONAR's voice RAG pipeline is optimized for sub-second end-to-end latency: Sarvam AI STT transcribes speech in ~1-3s, FastEmbed ONNX embeds query vectors in ~15ms, FAISS retrieves Top-K candidates in ~0.5ms, Groq LPUs generate answers at over 700 tokens/sec in ~200-400ms, and deterministic grounding checks take < 1ms.",
        "metadata": {"topic": "Latency", "category": "telemetry"}
    },
    {
        "doc_id": "topic_stt_sarvam",
        "lang": "en",
        "chunk_id": "stt_001",
        "text": "Speech-to-Text (STT) converts acoustic spoken audio into text transcripts. SONAR integrates Sarvam AI's Saarika v2.5 multilingual Indic ASR model alongside modern browser Web Speech APIs to support automatic speech recognition across 10+ Indic languages including Hindi, Marathi, Gujarati, Punjabi, Bengali, Tamil, Telugu, and Indian English.",
        "metadata": {"topic": "STT", "category": "speech"}
    },
    {
        "doc_id": "topic_groq_lpu",
        "lang": "en",
        "chunk_id": "groq_001",
        "text": "Groq Language Processing Units (LPUs) are purpose-built deterministic AI tensor processors designed specifically for high-speed inference. Groq delivers blazing generation speeds exceeding 700 tokens per second, making real-time voice conversational RAG responsive, fluent, and instant.",
        "metadata": {"topic": "Groq", "category": "inference"}
    },
    {
        "doc_id": "topic_sonar_voice_rag",
        "lang": "en",
        "chunk_id": "sonar_001",
        "text": "SONAR (SOund Neural Answer Retrieval) is an end-to-end multilingual voice-enabled RAG system built for the HH Goa 2026 Hackathon by team INFERENTIA. It features an interactive 3D golden wireframe audio orb, real-time telemetry metrics, multi-device audio switching, and dual-layer grounding verification.",
        "metadata": {"topic": "SONAR", "category": "project"}
    }
]

def main():
    print(f"Loading existing FAISS index from {FAISS_PATH}...")
    index = faiss.read_index(str(FAISS_PATH))
    print(f"Existing index vector count: {index.ntotal}")

    print(f"Loading embedding model: {MODEL_NAME}...")
    embedder = TextEmbedding(model_name=MODEL_NAME)

    texts = [d["text"] for d in KNOWLEDGE_DOCS]
    print(f"Embedding {len(texts)} new topic documents...")
    vectors = list(embedder.embed(texts))
    v_matrix = np.array(vectors, dtype=np.float32)

    # Normalize vectors for cosine similarity (Inner Product index)
    faiss.normalize_L2(v_matrix)

    print(f"Adding {v_matrix.shape[0]} vectors to FAISS index...")
    index.add(v_matrix)
    print(f"New index vector count: {index.ntotal}")

    print(f"Saving updated FAISS index to {FAISS_PATH}...")
    faiss.write_index(index, str(FAISS_PATH))

    print(f"Appending new metadata chunks to {META_PATH}...")
    with open(META_PATH, "a", encoding="utf-8") as f:
        for doc in KNOWLEDGE_DOCS:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print("[SUCCESS] All demo topics (RAG, FAISS, Chunking, Latency, STT, Groq, SONAR) successfully injected into the knowledge base!")

if __name__ == "__main__":
    main()
