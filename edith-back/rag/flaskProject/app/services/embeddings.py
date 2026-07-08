# embeddings.py
from langchain_chroma import Chroma
from app.services.codebert_model import get_code_embedding
from langchain.embeddings.base import Embeddings

# 래퍼 클래스 생성
class GraphCodeBERTEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, code_snippet):
        return get_code_embedding(code_snippet)

class CodeEmbeddingProcessor:
    def __init__(self, uuid):
        self.db = Chroma(
            embedding_function=GraphCodeBERTEmbeddings(),
            collection_name=f'code_embeddings_{uuid}',
            persist_directory=None
        )

    # Chunk 코드 임베딩
    def store_embeddings(self, code_snippets):
        try:
            texts = []
            metadatas = []
            for snippet in code_snippets:
                if isinstance(snippet, dict):
                    text = snippet.get('text') or snippet.get('code') or ''
                    if not text:
                        continue
                    texts.append(text)
                    metadatas.append({
                        'path': snippet.get('path', 'unknown'),
                        'language': snippet.get('language', 'unknown')
                    })
                else:
                    texts.append(str(snippet))
                    metadatas.append({'path': 'unknown', 'language': 'unknown'})

            if not texts:
                return True

            self.db.add_texts(
                texts=texts,
                metadatas=metadatas,
            )
            return True
        except Exception as e:
            print(f"Error storing embeddings: {e}")
            return False

    # 유사 코드 검색
    def query_similar_code(self, code_snippet, n_results=5):
        try:
            results = self.db.similarity_search_with_score(
                query=code_snippet,
                k=n_results
            )
            related_codes = [{
                'path': doc.metadata.get('path', 'unknown'),
                'language': doc.metadata.get('language', 'unknown'),
                'content': doc.page_content,
                'score': score
            } for doc, score in results]
            return related_codes
        except Exception as e:
            print(f"Error querying similar code: {e}")
            return []

    def cleanup(self):
        try:
            # 시스템 캐시 정리
            if hasattr(self.db, '_client'):
                self.db._client.clear_system_cache()

            # Collection 정리
            if hasattr(self.db, '_collection'):
                try:
                    # 모든 문서의 ID를 가져와서 삭제
                    all_ids = self.db._collection.get()['ids']
                    if all_ids:
                        self.db._collection.delete(ids=all_ids)
                except Exception as collection_error:
                    print(f"Warning during collection cleanup: {collection_error}")

            # 전체 컬렉션 삭제
            try:
                self.db.delete_collection()
            except Exception as delete_error:
                print(f"Warning during delete_collection: {delete_error}")

            # DB 객체 정리
            self.db = None

            return True
        except Exception as e:
            print(f"Critical error during cleanup: {e}")
            return False
