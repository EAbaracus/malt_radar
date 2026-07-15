import hashlib

class ChunkingEngine:
    def generate_chunk(self, book_id, page_num, text):
        chunk_hash = hashlib.sha256(f"{book_id}_{page_num}_{text}".encode('utf-8')).hexdigest()[:12]
        return {
            "chunk_id": f"chunk_{chunk_hash}",
            "book_id": book_id,
            "page": page_num,
            "text": text,
            "doc_hash": hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]
        }
