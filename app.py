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

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="documents")

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
            chunks = process_document(filepath)
            
            # Generate document ID
            doc_id = f"doc_{int(time.time())}"
            
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
            
            # Update registry
            document_registry[doc_id] = {
                "filename": filename,
                "path": filepath,
                "chunk_ids": chunk_ids
            }
            with open(REGISTRY_FILE, 'w') as f:
                json.dump(document_registry, f)
            
            return jsonify({'message': 'File successfully uploaded and processed'}), 200
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
    data = request.json
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        response = rag_engine.get_response(data['question'])
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_knowledge_base():
    try:
        global collection
        print("Starting knowledge base reset...")
        
        # Delete all documents from ChromaDB
        print("Deleting ChromaDB collection...")
        try:
            collection.delete(ids=collection.get()['ids'])
        except Exception as e:
            print(f"Error deleting ChromaDB documents: {e}")
            # If delete fails, try to delete the collection and recreate it
            chroma_client.delete_collection(name="documents")
            collection = chroma_client.get_or_create_collection(name="documents")
        
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
