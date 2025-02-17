import openai
import os

class RAGEngine:
    def __init__(self, collection):
        self.collection = collection
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4')  # Default to gpt-4 if not specified
        
    def get_response(self, question, n_results=3):
        logs = []
        
        # Query ChromaDB for relevant documents
        chroma_request = {
            "query_texts": [question],
            "n_results": n_results
        }
        logs.append({
            "system": "ChromaDB",
            "type": "request",
            "operation": "query",
            "data": chroma_request
        })
        
        results = self.collection.query(**chroma_request)
        
        logs.append({
            "system": "ChromaDB",
            "type": "response",
            "operation": "query",
            "data": {
                "documents": results['documents'],
                "metadatas": results['metadatas'],
                "distances": results['distances']
            }
        })
        
        # Prepare context from results
        contexts = []
        for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
            source = metadata['source']
            contexts.append(f"[Source: {source}] {doc}")
        
        context = "\n\n".join(contexts)
        
        # Generate response using OpenAI
        system_prompt = """You are a helpful AI assistant that answers questions based on the provided context. 
        Always cite your sources using the format [Source: filename] when providing information.
        If the context doesn't contain relevant information to answer the question, say so.
        Keep your answers concise and to the point."""
        
        openai_request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\n\nPlease provide an answer based on the context above."}
            ],
            "temperature": 0
        }
        logs.append({
            "system": "OpenAI",
            "type": "request",
            "operation": "chat_completion",
            "data": {
                "model": openai_request["model"],
                "messages": openai_request["messages"],
                "temperature": openai_request["temperature"]
            }
        })
        
        response = openai.ChatCompletion.create(**openai_request)
        
        logs.append({
            "system": "OpenAI",
            "type": "response",
            "operation": "chat_completion",
            "data": {
                "choices": [{
                    "message": response['choices'][0]['message'],
                    "finish_reason": response['choices'][0]['finish_reason']
                }],
                "model": response['model'],
                "usage": response['usage']
            }
        })
        
        return {
            "answer": response['choices'][0]['message']['content'],
            "sources": list(set(meta['source'] for meta in results['metadatas'][0])),
            "logs": logs
        }
