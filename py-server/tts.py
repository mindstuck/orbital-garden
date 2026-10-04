import wave
from piper import PiperVoice

def generate_audio(text):
    if not text:
        return
    
    voice = PiperVoice.load("./voices/en_US-danny-low.onnx")
    with wave.open("test.wav", "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
        
    with open("test.wav", "rb") as audio_file:
        return audio_file.read()
        

if __name__ == "__main__":
    generate_audio("Welcome to the world of speech synthesis you dumb fuck!")