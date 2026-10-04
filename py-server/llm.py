import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="http://host.docker.internal:8300/v1",  # from another container on the same compose network: http://llama-server:8000/v1
    api_key="not-needed",                 # required by the SDK, ignored by llama-server
)

def get_response(message):
    messages = [
        {"role": "system", "content": "You are angry servant"},
        {"role": "user", "content": message},
    ]
    
    resp = client.chat.completions.create(
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
    )
    
    return resp.choices[0].message.content


if __name__ == "__main__":
    print(get_response("Sing."))