from pypdf import PdfReader
import markdown
import re

def process_document(filepath):
    """Process different document types and return chunks of text."""
    extension = filepath.split('.')[-1].lower()
    
    if extension == 'pdf':
        return process_pdf(filepath)
    elif extension == 'md':
        return process_markdown(filepath)
    elif extension == 'txt':
        return process_text(filepath)
    else:
        raise ValueError(f"Unsupported file type: {extension}")

def process_pdf(filepath, chunk_size=1000):
    """Extract text from PDF and split into chunks."""
    chunks = []
    reader = PdfReader(filepath)
    
    current_chunk = ""
    for page in reader.pages:
        text = page.extract_text()
        words = text.split()
        
        for word in words:
            if len(current_chunk) + len(word) + 1 > chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = word + " "
            else:
                current_chunk += word + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def process_markdown(filepath, chunk_size=1000):
    """Convert markdown to text and split into chunks."""
    with open(filepath, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert markdown to HTML and then strip HTML tags
    html_content = markdown.markdown(md_content)
    text_content = re.sub('<[^<]+?>', '', html_content)
    
    return split_text(text_content, chunk_size)

def process_text(filepath, chunk_size=1000):
    """Read text file and split into chunks."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return split_text(content, chunk_size)

def split_text(text, chunk_size=1000):
    """Split text into chunks of approximately equal size."""
    chunks = []
    current_chunk = ""
    
    # Split by sentences (simple approach)
    sentences = re.split('(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
        else:
            current_chunk += sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
