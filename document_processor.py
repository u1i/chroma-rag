from pypdf import PdfReader
import markdown
import re

def process_document(filepath):
    """Process different document types and return chunks of text with processing logs."""
    logs = []
    extension = filepath.split('.')[-1].lower()
    
    logs.append({
        "system": "DocumentProcessor",
        "type": "info",
        "operation": "file_detection",
        "data": {
            "file": filepath,
            "detected_type": extension
        }
    })
    
    if extension == 'pdf':
        chunks, pdf_logs = process_pdf(filepath)
        logs.extend(pdf_logs)
        return chunks, logs
    elif extension == 'md':
        chunks, md_logs = process_markdown(filepath)
        logs.extend(md_logs)
        return chunks, logs
    elif extension == 'txt':
        chunks, txt_logs = process_text(filepath)
        logs.extend(txt_logs)
        return chunks, logs
    else:
        raise ValueError(f"Unsupported file type: {extension}")

def process_pdf(filepath, chunk_size=1000):
    """Extract text from PDF and split into chunks."""
    chunks = []
    logs = []
    reader = PdfReader(filepath)
    
    logs.append({
        "system": "DocumentProcessor",
        "type": "info",
        "operation": "pdf_processing",
        "data": {
            "total_pages": len(reader.pages),
            "chunk_size": chunk_size
        }
    })
    
    current_chunk = ""
    total_words = 0
    
    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        words = text.split()
        total_words += len(words)
        
        for word in words:
            if len(current_chunk) + len(word) + 1 > chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = word + " "
            else:
                current_chunk += word + " "
                
        logs.append({
            "system": "DocumentProcessor",
            "type": "info",
            "operation": "page_processed",
            "data": {
                "page_number": page_num,
                "words_on_page": len(words)
            }
        })
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    logs.append({
        "system": "DocumentProcessor",
        "type": "info",
        "operation": "pdf_complete",
        "data": {
            "total_words": total_words,
            "chunks_created": len(chunks),
            "average_chunk_size": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0
        }
    })
    
    return chunks, logs

def process_markdown(filepath, chunk_size=1000):
    """Convert markdown to text and split into chunks."""
    logs = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    logs.append({
        "system": "DocumentProcessor",
        "type": "info",
        "operation": "markdown_processing",
        "data": {
            "content_length": len(md_content),
            "chunk_size": chunk_size
        }
    })
    
    # Convert markdown to HTML and then strip HTML tags
    html_content = markdown.markdown(md_content)
    text_content = re.sub('<[^<]+?>', '', html_content)
    
    chunks, split_logs = split_text(text_content, chunk_size)
    logs.extend(split_logs)
    
    logs.append({
        "system": "DocumentProcessor",
        "type": "info",
        "operation": "markdown_complete",
        "data": {
            "original_length": len(md_content),
            "processed_length": len(text_content),
            "chunks_created": len(chunks)
        }
    })
    
    return chunks, logs

def process_text(filepath, chunk_size=1000):
    """Process plain text file and split into chunks."""
    logs = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logs.append({
        "system": "DocumentProcessor",
        "type": "info",
        "operation": "text_processing",
        "data": {
            "content_length": len(content),
            "chunk_size": chunk_size
        }
    })
    
    chunks, split_logs = split_text(content, chunk_size)
    logs.extend(split_logs)
    
    return chunks, logs

def split_text(text, chunk_size=1000):
    """Split text into chunks of approximately equal size."""
    chunks = []
    logs = []
    current_chunk = ""
    
    # Split by sentences (simple approach)
    sentences = re.split('(?<=[.!?])\s+', text)
    
    logs.append({
        "system": "DocumentProcessor",
        "type": "info",
        "operation": "text_splitting",
        "data": {
            "total_length": len(text),
            "sentence_count": len(sentences),
            "target_chunk_size": chunk_size
        }
    })
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
        else:
            current_chunk += sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    logs.append({
        "system": "DocumentProcessor",
        "type": "info",
        "operation": "splitting_complete",
        "data": {
            "chunks_created": len(chunks),
            "average_chunk_size": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0
        }
    })
    
    return chunks, logs
