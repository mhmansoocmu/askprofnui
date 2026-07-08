import json
import os
import re

from vector_store import index_chunks

DOCUMENTS_DIR = "documents"
OUTPUT_FILE = "chunks.json"
CHUNK_SIZE = 800
OVERLAP = 100


def _split_long_section(text: str, source: str, base_index: int) -> list[dict]:
    chunks = []
    start = 0
    sub_index = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({
                "text": chunk,
                "source": source,
                "chunk_index": base_index + sub_index,
            })
            sub_index += 1
        start += CHUNK_SIZE - OVERLAP
    return chunks


def chunk_text(text: str, source: str) -> list[dict]:
    """Chunk by document sections (---) first, then by size for long sections."""
    chunks: list[dict] = []
    sections = re.split(r"\n---\n", text)
    index = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= CHUNK_SIZE:
            chunks.append({
                "text": section,
                "source": source,
                "chunk_index": index,
            })
            index += 1
        else:
            sub_chunks = _split_long_section(section, source, index)
            chunks.extend(sub_chunks)
            index += len(sub_chunks)
    return chunks


def load_all_chunks() -> list[dict]:
    all_chunks: list[dict] = []
    if not os.path.isdir(DOCUMENTS_DIR):
        print(f"Directory '{DOCUMENTS_DIR}/' not found.")
        return all_chunks

    txt_files = sorted(
        f for f in os.listdir(DOCUMENTS_DIR) if f.endswith(".txt")
    )
    if not txt_files:
        print(f"No .txt files found in '{DOCUMENTS_DIR}/'")
        return all_chunks

    for filename in txt_files:
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        print(f"Reading: {filename}")
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text, filename)
        all_chunks.extend(chunks)
        print(f"  → {len(chunks)} chunks")
    return all_chunks


def main() -> None:
    all_chunks = load_all_chunks()
    if not all_chunks:
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_chunks)} chunks to {OUTPUT_FILE}")

    print("Building Chroma vector index…")
    indexed = index_chunks(all_chunks)
    print(f"Indexed {indexed} chunks into chroma_db/")
    print("Done.")


if __name__ == "__main__":
    main()
