import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Internal Compose service DNS by default; override for a different endpoint.
LLM_API_URL = os.getenv("LLM_API_URL", "http://llama-server:8000/v1")

client = OpenAI(
    base_url=LLM_API_URL,  # e.g. http://llama-server:8000/v1 on the Compose network
    api_key="not-needed",                 # required by the SDK, ignored by llama-server
)

# TODO: get_response + get_response_stream functions
def get_response(message):
    messages = [
        {"role": "system", "content": "You are kuundere animer character"},
        {"role": "user", "content": message},
    ]
    
    stream = client.chat.completions.create(
        model="stheno",          # required by the SDK, ignored when the server has one model loaded
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        frequency_penalty=0.1,
        max_tokens=400,
        extra_body={
            "min_p": 0.05,
            "top_k": 0,
            "repeat_penalty": 1.05,
            "dry_multiplier": 0.8,
            "dry_base": 1.75,
            "dry_allowed_length": 2,
            # "xtc_probability": 0.5,
            # "xtc_threshold": 0.1,
        },
        stream=True
    )
    
    return stream


if __name__ == "__main__":
    print(get_response("What is your religion?."))