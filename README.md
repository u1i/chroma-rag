# Document Q&A System

An educational RAG (Retrieval-Augmented Generation) application that allows students to upload documents and understand how different components (ChromaDB, OpenAI, etc.) interact to provide answers. The system features detailed request/response logging for learning purposes.

## Features

- Upload and process PDF, TXT, and Markdown files
- Document chunking and embedding using ChromaDB
- Question answering using configurable OpenAI models (GPT-4, GPT-4-turbo, etc.)
- Interactive web interface with drag-and-drop support
- Source citations in answers
- Detailed system logs showing all interactions between components
- Knowledge base management (view, delete, reset)
- Educational insights into RAG system architecture

## Setup

1. Clone this repository
2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file from `.env.example` and configure your settings:
```bash
cp .env.example .env
# Edit .env and add:
# - OPENAI_API_KEY: Your OpenAI API key
# - OPENAI_MODEL: Model to use (e.g., gpt-4, gpt-4-1106-preview)
```

5. Start the ChromaDB container:
```bash
docker-compose up -d
```

6. Run the Flask application:
```bash
./restart.sh  # This will handle killing any existing process and starting the app
```

7. Open your browser and visit `http://localhost:5001`

## Usage

### Document Management
1. Upload documents using drag-and-drop or file selection
2. View uploaded documents in the Knowledge Base tab
3. Delete individual documents or reset the entire knowledge base

### Asking Questions
1. Switch to the Q&A tab
2. Type your question in the text area
3. Click "Ask Question" to get an answer
4. View the detailed system logs to understand:
   - How the frontend sends requests to the backend
   - How ChromaDB finds relevant document chunks
   - How OpenAI generates answers using the context
   - The complete request/response flow

### System Logs
The system logs panel shows:
- Client requests to the backend
- Backend processing steps
- ChromaDB document retrieval
- OpenAI model interactions
- Response generation

Click on any log entry to view the detailed request/response data.

## Architecture

### Core Components
- `app.py`: Flask application handling HTTP endpoints and file uploads
- `document_processor.py`: Document parsing, text extraction, and chunking
- `rag_engine.py`: RAG pipeline with ChromaDB integration and OpenAI interaction
- `templates/index.html`: Interactive web interface with system logging

### Key Files
- `.env`: Configuration for OpenAI API key and model selection
- `docker-compose.yml`: ChromaDB container configuration
- `requirements.txt`: Python dependencies
- `restart.sh`: Utility script for managing the Flask application

### Directories
- `uploads/`: Temporary storage for uploaded documents
- `chroma_db/`: ChromaDB persistent storage
- `templates/`: HTML templates

### Technology Stack
- Backend: Python, Flask
- Database: ChromaDB (vector store)
- AI: OpenAI API (configurable models)
- Frontend: HTML, JavaScript, Tailwind CSS
- Container: Docker (for ChromaDB)

## Educational Notes

### System Design
- Documents are chunked into smaller pieces (default 1000 characters)
- ChromaDB handles document embedding and similarity search
- The system uses semantic search to find relevant context
- Answers include citations to help verify information

### Configuration
- Maximum file size: 16MB
- Supported formats: PDF, TXT, Markdown
- Default model: GPT-4o (configurable via .env)
- ChromaDB uses the default embedding model

### Best Practices
- Keep documents focused and well-structured
- Use clear, specific questions
- Review system logs to understand the RAG process
- Monitor token usage through the OpenAI response logs

### Security Notes
- API keys should never be committed to version control
- The .env file is excluded via .gitignore
- This is a development server, not for production use
- No authentication is implemented (add if needed)
