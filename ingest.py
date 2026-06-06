import os
import json

DOCUMENTS_DIR = "documents"
OUTPUT_FILE = "chunks.json"
CHUNK_SIZE = 500
OVERLAP = 50


def chunk_text(text, source):
    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        chunks.append({
            "text": chunk,
            "source": source,
            "chunk_index": index,
        })
        index += 1
        start += CHUNK_SIZE - OVERLAP
    return chunks


def main():
    all_chunks = []
    txt_files = [f for f in os.listdir(DOCUMENTS_DIR) if f.endswith(".txt")]

    if not txt_files:
        print(f"No .txt files found in '{DOCUMENTS_DIR}/'")
        return

    for filename in sorted(txt_files):
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        print(f"Reading: {filename}")
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text, filename)
        all_chunks.extend(chunks)
        print(f"  → {len(chunks)} chunks")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(all_chunks)} total chunks saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
