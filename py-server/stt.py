import time
from faster_whisper import WhisperModel

model = WhisperModel(
    "small", 
    device="cuda", 
    compute_type="int8_float16"
)


def transcribe_audio(audio_file):
    start_time = time.time()
    segments, info = model.transcribe(
        audio_file,
        beam_size=5,
        language="en",
        vad_filter=True
    )
    print(f"\nDetected Language: '{info.language}' (Probability: {info.language_probability:.2%})")
    print(f"Audio Duration: {info.duration:.2f}s\n")
    print("--- Transcription ---")
    
    for segment in segments:
        print(f"[{segment.start:05.2f}s -> {segment.end:05.2f}s] {segment.text}")

    print(f"\nCompleted in {time.time() - start_time:.2f} seconds.")
    return segments, info
