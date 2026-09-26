import time
from faster_whisper import WhisperModel

# 1. Model Configuration
# Models available: "tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"
# Device options: "cuda" (for GPU) or "cpu"
# Compute types: "float16", "int8_float16", "int8", "float32"
model_size = "base"
device = "cpu"       # Change to "cuda" if using an NVIDIA GPU
compute_type = "int8" # Use "float16" or "int8_float16" for GPU

print(f"Loading '{model_size}' model on {device} ({compute_type})...")
model = WhisperModel(model_size, device=device, compute_type=compute_type)

# 2. Run Transcription
audio_path = "sample.mp3"  # Replace with your audio file path

start_time = time.time()
segments, info = model.transcribe(
    audio_path,
    beam_size=5,
    vad_filter=True  # Silero VAD filters out non-speech audio segments
)

print(f"\nDetected Language: '{info.language}' (Probability: {info.language_probability:.2%})")
print(f"Audio Duration: {info.duration:.2f}s\n")
print("--- Transcription ---")

# Note: `segments` is a generator. Processing starts as you iterate through it.
for segment in segments:
    print(f"[{segment.start:05.2f}s -> {segment.end:05.2f}s] {segment.text}")

print(f"\nCompleted in {time.time() - start_time:.2f} seconds.")