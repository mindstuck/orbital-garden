"use strict";

const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
const ws = new WebSocket(`${wsScheme}://${window.location.host}/ws`);
ws.binaryType = "arraybuffer";

const button = document.getElementById("recordButton");
const textInput = document.getElementById("textInput");
const sendButton = document.getElementById("sendButton");
const messages = document.getElementById("messages");
const statusEl = document.getElementById("status");

let mediaRecorder = null;
let mediaStream = null;
let activeTurnId = null;
let recording = false;

let playing = false;
let currentAudio = null;
let currentUrl = null;
const playBuffer = [];

function newTurnId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function addMessage(text, cls) {
    const li = document.createElement("li");
    li.textContent = text;
    if (cls) li.className = cls;
    messages.appendChild(li);
}

function setStatus(text) { statusEl.textContent = text || ""; }

function safeSend(payload) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(payload);
        return true;
    }
    return false;
}

ws.onmessage = function(event) {
    if (typeof event.data === "string") {
        handleEvent(event.data);
    } else {
        playOrQueue(event.data);
    }
};

function handleEvent(raw) {
    let msg;
    try { msg = JSON.parse(raw); } catch (e) { return; }
    if (msg.type === "status") {
        setStatus(msg.state || "");
    } else if (msg.type === "transcript") {
        addMessage("You: " + msg.text, "transcript");
    } else if (msg.type === "error") {
        setStatus("");
        addMessage("Error (" + msg.code + "): " + msg.message, "error");
    }
}

ws.onclose = function() {
    setStatus("Disconnected");
    cleanupRecording();
    stopPlayback();
};

ws.onerror = function() { setStatus("Connection error"); };

button.onclick = async function() {
    if (recording) {
        stopRecording();
    } else {
        await startRecording();
    }
};

sendButton.onclick = sendText;
textInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter") sendText();
});

function sendText() {
    const text = textInput.value.trim();
    if (!text) return;
    const turnId = newTurnId();
    if (safeSend(JSON.stringify({ type: "text", turn_id: turnId, text: text }))) {
        addMessage("You: " + text, "transcript");
        textInput.value = "";
    }
}

async function startRecording() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
        addMessage("Microphone error: " + err.message, "error");
        return;
    }

    activeTurnId = newTurnId();
    if (!safeSend(JSON.stringify({
        type: "audio_start",
        turn_id: activeTurnId,
        mime: "audio/webm"
    }))) {
        cleanupRecording();
        return;
    }

    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.ondataavailable = function(event) {
        if (event.data && event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(event.data);
        }
    };
    mediaRecorder.onstop = function() {
        if (activeTurnId) {
            safeSend(JSON.stringify({ type: "audio_end", turn_id: activeTurnId }));
        }
        activeTurnId = null;
        cleanupRecording();
    };

    mediaRecorder.start(250);
    recording = true;
    button.textContent = "Press to Send";
    setStatus("recording");
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        recording = false;
        button.textContent = "Press to Talk";
        setStatus("");
        mediaRecorder.stop();
    }
}

function cleanupRecording() {
    recording = false;
    if (mediaStream) {
        mediaStream.getTracks().forEach(function(track) { track.stop(); });
        mediaStream = null;
    }
    mediaRecorder = null;
    activeTurnId = null;
    button.textContent = "Press to Talk";
}

function playOrQueue(data) {
    if (playing) {
        playBuffer.push(data);
    } else {
        playWav(data);
    }
}

function playWav(rawData) {
    playing = true;
    const blob = rawData instanceof Blob
        ? rawData
        : new Blob([rawData], { type: "audio/wav" });

    currentUrl = URL.createObjectURL(blob);
    const audio = new Audio(currentUrl);
    currentAudio = audio;

    const finish = function() {
        if (currentUrl) URL.revokeObjectURL(currentUrl);
        currentUrl = null;
        currentAudio = null;
        const next = playBuffer.shift();
        if (next) {
            playWav(next);
        } else {
            playing = false;
        }
    };

    audio.onended = finish;
    audio.onerror = finish;
    audio.play().catch(function(error) {
        console.error("Failed to play audio:", error);
        finish();
    });
}

function stopPlayback() {
    playBuffer.length = 0;
    if (currentAudio) {
        try { currentAudio.pause(); } catch (e) { /* ignore */ }
    }
    if (currentUrl) URL.revokeObjectURL(currentUrl);
    currentAudio = null;
    currentUrl = null;
    playing = false;
}

window.addEventListener("beforeunload", function() {
    stopPlayback();
    cleanupRecording();
    try { ws.close(); } catch (e) { /* ignore */ }
});
