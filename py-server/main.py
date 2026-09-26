import uvicorn
from fastapi import FastAPI
from stt import transcribe_audio

app = FastAPI()


@app.get("/")
def read_root():
  return {"status": "ok"}

@app.post("/voice")
def process_voice(voice):
    segments, info = transcribe_audio(voice)
    return {"segments": segments, "info": info}
  


if __name__ == "__main__":
  # Must bind to 0.0.0.0 inside the container
  uvicorn.run(app, host="0.0.0.0", port=8000)