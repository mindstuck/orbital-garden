import re

def chunk_text(llm_stream):
    buffer = ""
    
    for chunk in llm_stream:
        content = chunk.choices[0].delta.content
        if content is None:
            continue
        
        buffer += content
        
        if should_flush(buffer):
            text = clean_text(buffer)
            
            if text:
                yield text
            
            buffer = ""
            
    if buffer.strip():
        yield clean_text(buffer)
            
def should_flush(buffer: str) -> bool:
    if len(buffer) < 15:
        return False
    
    return any(char in buffer for char in ".!?")

def clean_text(text):
     # Strip single asterisks and everything inside them: *text*
    return re.sub(r'\*.*?\*', '', text, flags=re.DOTALL).strip()
    

# docker exec -it py-server python3 text_chunker.py
if __name__ == "__main__":
    from llm import get_response

    stream = get_response("What is your religion?.")
    for chunk in chunk_text(stream):
        print(chunk)