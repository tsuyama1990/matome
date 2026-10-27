import contextlib
import io
import json
import math
import struct
import threading
import wave
from collections.abc import Iterator
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest

_HOST = "127.0.0.1"
_EPHEMERAL_PORT = 0
_POLL_INTERVAL_SECONDS = 0.02
_SHUTDOWN_TIMEOUT_SECONDS = 5.0
_ENGINE_VERSION = "0.14.0"

_HTTP_OK = 200
_HTTP_NO_CONTENT = 204
_HTTP_NOT_FOUND = 404
_HTTP_INTERNAL_SERVER_ERROR = 500
_HTTP_SERVICE_UNAVAILABLE = 503

_SAMPLE_RATE_HZ = 24000
_WAV_CHANNELS = 1
_WAV_SAMPLE_WIDTH_BYTES = 2
_SINE_FREQUENCY_HZ = 440.0
_SINE_AMPLITUDE_RATIO = 0.05
_INT16_MAX = 32767
_SINE_AMPLITUDE = int(_INT16_MAX * _SINE_AMPLITUDE_RATIO)
_SECONDS_PER_CHAR = 0.08
_FRAMES_PER_CHAR = int(_SAMPLE_RATE_HZ * _SECONDS_PER_CHAR)
# 24000 Hz / gcd(24000, 440) = 600 frames per 11 exact sine periods.
_SINE_CYCLE_FRAMES = 600

_DEFAULT_SPEED_SCALE = 1.0
_DEFAULT_PITCH_SCALE = 0.0
_DEFAULT_INTONATION_SCALE = 1.0
_DEFAULT_VOLUME_SCALE = 1.0


def _build_sine_cycle_bytes() -> bytes:
    samples = [
        int(
            _SINE_AMPLITUDE * math.sin(2.0 * math.pi * _SINE_FREQUENCY_HZ * index / _SAMPLE_RATE_HZ)
        )
        for index in range(_SINE_CYCLE_FRAMES)
    ]
    return struct.pack(f"<{_SINE_CYCLE_FRAMES}h", *samples)


_SINE_CYCLE_PCM = _build_sine_cycle_bytes()


def _build_sine_wav_bytes(text_length: int) -> bytes:
    effective_chars = max(1, text_length)
    total_frames = effective_chars * _FRAMES_PER_CHAR
    full_cycles, remainder_frames = divmod(total_frames, _SINE_CYCLE_FRAMES)
    pcm_data = (
        _SINE_CYCLE_PCM * full_cycles
        + _SINE_CYCLE_PCM[: remainder_frames * _WAV_SAMPLE_WIDTH_BYTES]
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(_WAV_CHANNELS)
        writer.setsampwidth(_WAV_SAMPLE_WIDTH_BYTES)
        writer.setframerate(_SAMPLE_RATE_HZ)
        writer.writeframes(pcm_data)
    return buf.getvalue()


@dataclass(frozen=True)
class RecordedRequest:
    method: str
    path: str
    query: dict[str, str]
    json_body: Any = None

    def __getitem__(self, key: str) -> Any:
        if key == "method":
            return self.method
        if key == "path":
            return self.path
        if key == "query":
            return self.query
        if key in {"json_body", "body"}:
            return self.json_body
        raise KeyError(key)


class FakeVoicevoxServer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests: list[RecordedRequest] = []
        self.synthesized_texts: list[str] = []
        self.max_in_flight: int = 0
        self._in_flight: int = 0
        self._synthesis_attempts: int = 0
        self._successful_syntheses: int = 0

        self.fail_synthesis_first: int = 0
        self.exhaust_above_chars: int | None = None
        self.always_500: bool = False
        self.fail_after_n_synthesis: int | None = None

        self._httpd = _VoicevoxHTTPServer((_HOST, _EPHEMERAL_PORT), _VoicevoxRequestHandler, self)
        port = self._httpd.server_address[1]
        self.url = f"http://{_HOST}:{port}"
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            kwargs={"poll_interval": _POLL_INTERVAL_SECONDS},
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=_SHUTDOWN_TIMEOUT_SECONDS)

    @contextlib.contextmanager
    def _track_in_flight(self) -> Iterator[None]:
        with self._lock:
            self._in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self._in_flight)
        try:
            yield
        finally:
            with self._lock:
                self._in_flight -= 1

    def _should_fail_with_500(self) -> bool:
        if self.always_500:
            return True
        return (
            self.fail_after_n_synthesis is not None
            and self._successful_syntheses >= self.fail_after_n_synthesis
        )

    def _handle_audio_query(self, query: dict[str, str]) -> tuple[int, str, bytes]:
        text = query.get("text", "")
        with self._lock:
            self.synthesized_texts.append(text)
            if self._should_fail_with_500():
                return (_HTTP_INTERNAL_SERVER_ERROR, "text/plain", b"internal server error")
            if self.exhaust_above_chars is not None and len(text) > self.exhaust_above_chars:
                return (_HTTP_INTERNAL_SERVER_ERROR, "text/plain", b"resource exhausted")

        payload = {
            "text": text,
            "speedScale": _DEFAULT_SPEED_SCALE,
            "pitchScale": _DEFAULT_PITCH_SCALE,
            "intonationScale": _DEFAULT_INTONATION_SCALE,
            "volumeScale": _DEFAULT_VOLUME_SCALE,
            "outputSamplingRate": _SAMPLE_RATE_HZ,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return (_HTTP_OK, "application/json", body)

    def _handle_synthesis(self, json_body: Any) -> tuple[int, str, bytes]:
        with self._lock:
            self._synthesis_attempts += 1
            if self._synthesis_attempts <= self.fail_synthesis_first:
                return (_HTTP_SERVICE_UNAVAILABLE, "text/plain", b"service unavailable")
            if self._should_fail_with_500():
                return (_HTTP_INTERNAL_SERVER_ERROR, "text/plain", b"internal server error")
            self._successful_syntheses += 1

        text = ""
        if isinstance(json_body, dict):
            raw_text = json_body.get("text", "")
            if isinstance(raw_text, str):
                text = raw_text
        return (_HTTP_OK, "audio/wav", _build_sine_wav_bytes(len(text)))

    def handle_request(
        self,
        method: str,
        raw_path: str,
        raw_body: bytes,
    ) -> tuple[int, str, bytes]:
        # Track concurrency inside handle_request so in_flight decrements before socket write.
        with self._track_in_flight():
            parsed = urlsplit(raw_path)
            route_path = parsed.path
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            json_body = json.loads(raw_body.decode("utf-8")) if raw_body else None

            with self._lock:
                self.requests.append(
                    RecordedRequest(
                        method=method,
                        path=route_path,
                        query=query,
                        json_body=json_body,
                    )
                )

            if method == "GET" and route_path == "/version":
                body = json.dumps(_ENGINE_VERSION).encode("utf-8")
                return (_HTTP_OK, "application/json", body)
            if method == "POST" and route_path == "/user_dict_word":
                return (_HTTP_NO_CONTENT, "text/plain", b"")
            if method == "POST" and route_path == "/audio_query":
                return self._handle_audio_query(query)
            if method == "POST" and route_path == "/synthesis":
                return self._handle_synthesis(json_body)
            return (_HTTP_NOT_FOUND, "text/plain", b"not found")


class _VoicevoxHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        state: FakeVoicevoxServer,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.state = state


class _VoicevoxRequestHandler(BaseHTTPRequestHandler):
    def _dispatch(self, method: str) -> None:
        assert isinstance(self.server, _VoicevoxHTTPServer)
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""
        status, content_type, resp_body = self.server.state.handle_request(
            method,
            self.path,
            raw_body,
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        if resp_body:
            self.wfile.write(resp_body)

    # BaseHTTPRequestHandler dispatches HTTP methods by uppercase verb name.
    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    # Parameter name must match BaseHTTPRequestHandler.log_message in typeshed.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return None


@pytest.fixture
def fake_voicevox() -> Iterator[FakeVoicevoxServer]:
    server = FakeVoicevoxServer()
    server.start()
    try:
        yield server
    finally:
        server.close()
