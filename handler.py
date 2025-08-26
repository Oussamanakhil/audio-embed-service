import base64
import io
import json
from typing import Dict, Any, Optional

import numpy as np
import requests
import librosa
import runpod


def _load_audio(input_obj: Dict[str, Any], sr: int = 16000) -> np.ndarray:
    """
    Load audio from one of:
      - input_obj["audio_url"]: http(s) URL to an audio file (mp3/wav/m4a/ogg…)
      - input_obj["audio_b64"]: base64-encoded audio bytes
    Returns mono float32 np.ndarray at target sample rate.
    """
    if "audio_url" in input_obj and input_obj["audio_url"]:
        url = input_obj["audio_url"]
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        audio_bytes = io.BytesIO(resp.content)
        y, _ = librosa.load(audio_bytes, sr=sr, mono=True)
        return y.astype(np.float32)

    if "audio_b64" in input_obj and input_obj["audio_b64"]:
        raw = base64.b64decode(input_obj["audio_b64"])
        audio_bytes = io.BytesIO(raw)
        y, _ = librosa.load(audio_bytes, sr=sr, mono=True)
        return y.astype(np.float32)

    raise ValueError("Provide either 'audio_url' or 'audio_b64' in input.")


def _compute_embedding(
    y: np.ndarray,
    sr: int = 16000,
    n_mfcc: int = 40,
) -> np.ndarray:
    """
    Lightweight audio embedding using classic features (MFCC + stats).
    Output is a fixed-length vector suitable for quick similarity tasks.
    """
    # MFCCs (T x n_mfcc) -> mean & std across time
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    mfcc_mu = mfcc.mean(axis=1)
    mfcc_sd = mfcc.std(axis=1)

    # Add a couple extra summary stats for a bit more signal
    zcr = librosa.feature.zero_crossing_rate(y=y).mean()
    spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
    spec_bw = librosa.feature.spectral_bandwidth(y=y, sr=sr).mean()

    emb = np.concatenate([mfcc_mu, mfcc_sd, np.array([zcr, spec_centroid, spec_bw])])
    return emb.astype(np.float32)


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod Serverless handler.

    Expected event["input"] keys:
      - audio_url: str (optional)
      - audio_b64: str (optional, base64)
      - sample_rate: int (optional, default 16000)
      - n_mfcc: int (optional, default 40)

    Returns:
      {
        "embedding": [float, ...],
        "dim": int,
        "sr": int,
        "n_mfcc": int
      }
    """
    try:
        inp: Dict[str, Any] = event.get("input", {}) or {}

        sr = int(inp.get("sample_rate", 16000))
        n_mfcc = int(inp.get("n_mfcc", 40))

        y = _load_audio(inp, sr=sr)
        emb = _compute_embedding(y, sr=sr, n_mfcc=n_mfcc)

        return {
            "embedding": emb.tolist(),
            "dim": int(emb.shape[0]),
            "sr": sr,
            "n_mfcc": n_mfcc,
        }

    except Exception as e:
        return {"error": str(e)}


# Start the RunPod queue worker
runpod.serverless.start({"handler": handler})
