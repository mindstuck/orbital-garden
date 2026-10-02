import time
from faster_whisper import WhisperModel

model = WhisperModel(
    "base",
    device="cuda",
    compute_type="float16"
)


def transcribe_audio(path: str) -> str | None:
    try:
        start_time = time.time()
        segments, info = model.transcribe(
            path,
            beam_size=5,
            language="en",
            vad_filter=True
        )

        print(f"\nDetected Language: '{info.language}' (Probability: {info.language_probability:.2%})")
        print(f"Audio Duration: {info.duration:.2f}s\n")
        print("--- Transcription ---")

        chunks = []
        for segment in segments:
            print(f"[{segment.start:05.2f}s -> {segment.end:05.2f}s] {segment.text}")
            chunks.append(segment.text)

        transcribed_text = "".join(chunks).strip()
        
        with open("transcribed_text.txt", "w", encoding="utf-8") as f:
            f.write(transcribed_text)

        print(f"\nCompleted in {time.time() - start_time:.2f} seconds.")
        return transcribed_text

    except Exception as e:
        print(f"transcribe_audio error: {e}")
        return None


if __name__ == "__main__":
    print(transcribe_audio("voice.wav"))