# audio-embed-service

CPU-based audio embedding microservice for **RunPod Serverless**.  
Accepts an audio URL or base64 audio, computes a lightweight MFCC-based embedding, and returns a fixed-length vector.

## Features
- Public base image (`python:3.10-slim`) — no private registry issues
- Installs `ffmpeg` for decoding mp3/wav/m4a/ogg
- Queue worker via `runpod` (file: `handler.py`)
- No environment variables required

## Inputs
`POST /run` with body:
```json
{
  "input": {
    "audio_url": "https://example.com/sample.wav",
    "sample_rate": 16000,
    "n_mfcc": 40
  }
}
