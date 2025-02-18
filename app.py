from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import time
import json
import chromadb
from chromadb.config import Settings
from document_processor import process_document
from rag_engine import RAGEngine
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create documents registry file
REGISTRY_FILE = os.path.join(app.config['UPLOAD_FOLDER'], 'registry.json')
if os.path.exists(REGISTRY_FILE):
    with open(REGISTRY_FILE, 'r') as f:
        document_registry = json.load(f)
else:
    document_registry = {}

# Initialize ChromaDB client and collection
chroma_client = chromadb.PersistentClient(path="./chroma_db")
COLLECTION_NAME = "documents"

def get_or_create_collection():
    """Get or create the ChromaDB collection, ensuring it exists."""
    try:
        # Try to get existing collection
        return chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"Collection not found: {e}")
        try:
            # Try to create new collection
            return chroma_client.create_collection(name=COLLECTION_NAME)
        except Exception as e:
            print(f"Error creating collection: {e}")
            # If creation fails, delete and recreate
            try:
                chroma_client.delete_collection(name=COLLECTION_NAME)
                return chroma_client.create_collection(name=COLLECTION_NAME)
            except Exception as e:
                print(f"Fatal error with collection: {e}")
                raise

# Initialize collection
collection = get_or_create_collection()

# Initialize RAG engine
rag_engine = RAGEngine(collection)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'md'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process and add document to ChromaDB
            chunks, processing_logs = process_document(filepath)
            
            # Generate document ID
            doc_id = f"doc_{int(time.time())}"
            
            # Log ChromaDB operation start
            chroma_request_log = {
                "system": "ChromaDB",
                "type": "request",
                "operation": "add_chunks",
                "data": {
                    "chunk_count": len(chunks),
                    "average_chunk_size": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0,
                    "doc_id": doc_id
                }
            }
            processing_logs.append(chroma_request_log)
            
            # Add chunks to ChromaDB with metadata
            chunk_ids = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_ids.append(chunk_id)
                collection.add(
                    documents=[chunk],
                    metadatas=[{"source": filename, "chunk": i, "doc_id": doc_id}],
                    ids=[chunk_id]
                )
                
                # Log each chunk addition
                processing_logs.append({
                    "system": "ChromaDB",
                    "type": "info",
                    "operation": "chunk_added",
                    "data": {
                        "chunk_id": chunk_id,
                        "chunk_size": len(chunk),
                        "chunk_number": i + 1,
                        "total_chunks": len(chunks)
                    }
                })
            
            # Log successful ChromaDB operation
            processing_logs.append({
                "system": "ChromaDB",
                "type": "response",
                "operation": "add_chunks",
                "data": {
                    "status": "success",
                    "chunks_added": len(chunks),
                    "doc_id": doc_id
                }
            })
            
            # Update registry
            document_registry[doc_id] = {
                "filename": filename,
                "path": filepath,
                "chunk_ids": chunk_ids
            }
            with open(REGISTRY_FILE, 'w') as f:
                json.dump(document_registry, f)
            
            return jsonify({
                'message': 'File successfully uploaded and processed',
                'document_id': doc_id,
                'logs': processing_logs
            }), 200
        except Exception as e:
            # Clean up file if there was an error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/documents', methods=['GET'])
def list_documents():
    try:
        documents = [{
            "id": doc_id,
            "filename": info["filename"]
        } for doc_id, info in document_registry.items()]
        return jsonify(documents)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    try:
        if doc_id not in document_registry:
            return jsonify({'error': 'Document not found'}), 404
        
        # Get document info
        doc_info = document_registry[doc_id]
        
        # Remove chunks from ChromaDB
        collection.delete(ids=doc_info['chunk_ids'])
        
        # Delete file
        if os.path.exists(doc_info['path']):
            os.remove(doc_info['path'])
        
        # Update registry
        del document_registry[doc_id]
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(document_registry, f)
        
        return jsonify({'message': 'Document deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/query', methods=['POST'])
def query():
    global collection, rag_engine
    data = request.json
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # First check if we have any documents
        try:
            doc_count = len(collection.get()['ids'])
            if doc_count == 0:
                return jsonify({
                    'error': 'No documents found in the knowledge base. Please upload some documents first.',
                    'logs': [{
                        'system': 'Backend',
                        'type': 'error',
                        'operation': 'query',
                        'data': {'message': 'Empty knowledge base'}
                    }]
                }), 400
        except Exception as e:
            print(f"Error checking collection: {e}")
            # If collection doesn't exist, recreate it
            collection = get_or_create_collection()
            rag_engine = RAGEngine(collection)
            return jsonify({
                'error': 'Knowledge base was reset. Please upload documents and try again.',
                'logs': [{
                    'system': 'Backend',
                    'type': 'error',
                    'operation': 'query',
                    'data': {'message': 'Collection recreated'}
                }]
            }), 400
        
        # Process the question
        response = rag_engine.get_response(data['question'])
        return jsonify(response), 200
    except Exception as e:
        error_message = str(e)
        return jsonify({
            'error': error_message,
            'logs': [{
                'system': 'Backend',
                'type': 'error',
                'operation': 'query',
                'data': {'message': error_message}
            }]
        }), 500

@app.route('/reset', methods=['POST'])
def reset_knowledge_base():
    try:
        global collection, rag_engine
        print("Starting knowledge base reset...")
        
        # Recreate ChromaDB collection
        print("Resetting ChromaDB collection...")
        try:
            # Try to delete existing collection
            try:
                chroma_client.delete_collection(name=COLLECTION_NAME)
            except Exception as e:
                print(f"Error deleting collection (may not exist): {e}")
            
            # Create new collection
            collection = chroma_client.create_collection(name=COLLECTION_NAME)
            # Update RAG engine with new collection
            rag_engine = RAGEngine(collection)
        except Exception as e:
            print(f"Error recreating collection: {e}")
            # Last resort: try to clear existing collection
            try:
                collection = chroma_client.get_collection(name=COLLECTION_NAME)
                existing_ids = collection.get()['ids']
                if existing_ids:
                    collection.delete(ids=existing_ids)
                # Update RAG engine with cleared collection
                rag_engine = RAGEngine(collection)
            except Exception as inner_e:
                print(f"Fatal error resetting collection: {inner_e}")
                raise
        
        print("Deleting uploaded files...")
        # Delete all files in upload directory except registry.json
        for doc_info in document_registry.values():
            try:
                if os.path.exists(doc_info['path']):
                    os.remove(doc_info['path'])
                    print(f"Deleted file: {doc_info['path']}")
            except Exception as e:
                print(f"Error deleting file {doc_info['path']}: {e}")
        
        print("Clearing registry...")
        # Clear the registry
        document_registry.clear()
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(document_registry, f)
        
        print("Reset completed successfully")
        return jsonify({'message': 'Knowledge base reset successfully'})
    except Exception as e:
        print(f"Error during reset: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
