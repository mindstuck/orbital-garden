import uvicorn
import logging
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from stt import transcribe_audio
from llm import get_response
from tts import generate_audio
from text_chunker import chunk_text

app = FastAPI()
logger = logging.getLogger(__name__)

html = """
<!DOCTYPE html>
<html>
<head>
    <title>Assistant</title>
</head>
<body>
    <h1>Assistant</h1>

    <button style="width: 200px; height: 50px;" id="recordButton">Press to Talk</button>
    
    <input type="text" id="textInput" placeholder="Type a message..." style="width: 300px; height: 30px;">
    <input type="button" value="Send" onclick="sendText()" style="height: 36px;">

    <ul id="messages"></ul>

    <script>
        const ws = new WebSocket(`wss://${window.location.host}/ws`);
        ws.binaryType = "arraybuffer"

        const button = document.getElementById("recordButton");
        const textInput = document.getElementById("textInput");
        const messages = document.getElementById("messages");

        let mediaRecorder;
        let playBuffer = [];

        ws.onmessage = function(event) {
            if (event.data instanceof ArrayBuffer) {
                
                if (!playing) {
                    playWav(event.data);
                } else {
                    playBuffer.push(event.data);
                }
            }
        };

        button.onclick = async function() {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                stopRecording();
            } else {
                await startRecording();
            }
        };
        
        function sendText() {
            const text = textInput.value;
            if (text) {
                ws.send(text);
                textInput.value = "";
            }
        }
        
        async function startRecording() {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: true
            });

            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = function(event) {
                if (event.data.size > 0) {
                    console.log("Event data: ", event.data);
                    ws.send(event.data);
                }
            };

            mediaRecorder.start();
            button.textContent = "Press to Send";
        }

        function stopRecording() {
            if (mediaRecorder) {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                button.textContent = "Press to Talk";
            }
        }
        
        var playing = false;
        function playWav(rawData) {
            playing = true;

            const blob = rawData instanceof Blob
                ? rawData
                : new Blob([rawData], { type: "audio/wav" });

            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);

            audio.onended = () => {
                URL.revokeObjectURL(url);

                if (playBuffer.length) {
                    playWav(playBuffer.shift());
                } else {
                    playing = false;
                }
            };

            audio.play().catch(error => {
                URL.revokeObjectURL(url);
                playing = false;
                console.error("Failed to play audio:", error);
            });
        }
    </script>
</body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            message = await websocket.receive()

            if "text" in message:
                logger.info('Websocket received text')
                stream = get_response(message["text"])
                
                for chunk in chunk_text(stream):
                    audio_response = generate_audio(chunk)
                    await websocket.send_bytes(audio_response)
                # await websocket.send_text(
                #     f"Message text was: {message['text']}; LLM response: {response}"
                # )

            elif "bytes" in message:
                audio = message["bytes"]

                with open("voice.webm", "wb") as f:
                    f.write(audio)

                text = transcribe_audio("voice.webm")

                if text is None:
                    await websocket.send_text("Transcription failed (see server logs).")
                else:
                    responseStream = get_response(text)
                    for chunk in chunk_text(responseStream):
                        audio_response = generate_audio(chunk)
                        await websocket.send_bytes(audio_response)
                    # await websocket.send_text(f"Transcribed audio: {text}; LLM response: {response}")

    except Exception as e:
        print(f"WebSocket closed or error: {e}")


if __name__ == "__main__":
  # Must bind to 0.0.0.0 inside the container
  uvicorn.run(app, host="0.0.0.0", port=8000)