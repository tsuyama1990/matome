import io
import json
import wave

import httpx
import pytest

from src.txt2speech.config import Settings
from src.txt2speech.dictionary import DictEntry
from src.txt2speech.errors import EngineError, ResourceExhausted
from src.txt2speech.voicevox import VoicevoxClient

_SAMPLE_RATE = 24000
_SAMPLE_WIDTH = 2
_CHANNELS = 1
_DEFAULT_FRAMES = 2400


def _make_wav_bytes(frames: int = _DEFAULT_FRAMES, rate: int = _SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(_CHANNELS)
        writer.setsampwidth(_SAMPLE_WIDTH)
        writer.setframerate(rate)
        writer.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


@pytest.mark.requirement("REQ-2026-002-F06")
def test_synthesize_orders_audio_query_then_synthesis() -> None:
    """T2S-I01: VoicevoxClient.synthesize calls /audio_query then /synthesis with configured scales."""
    expected_wav = _make_wav_bytes()
    recorded_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        if request.url.path == "/audio_query":
            return httpx.Response(
                200,
                json={
                    "accent_phrases": [],
                    "speedScale": 1.0,
                    "pitchScale": 0.0,
                    "intonationScale": 1.0,
                    "volumeScale": 1.0,
                },
            )
        if request.url.path == "/synthesis":
            return httpx.Response(200, content=expected_wav)
        return httpx.Response(404)

    settings = Settings(
        speaker=3,
        speed_scale=1.15,
        pitch_scale=0.05,
        intonation_scale=1.2,
        volume_scale=1.0,
    )
    transport = httpx.MockTransport(handler)
    with VoicevoxClient(settings, transport=transport, sleep=lambda _s: None) as client:
        wav_bytes = client.synthesize("こんにちは")

    assert wav_bytes == expected_wav
    assert [req.url.path for req in recorded_requests] == ["/audio_query", "/synthesis"]

    query_req, synth_req = recorded_requests
    assert query_req.method == "POST"
    assert query_req.url.params["text"] == "こんにちは"
    assert query_req.url.params["speaker"] == "3"

    assert synth_req.method == "POST"
    assert synth_req.url.params["speaker"] == "3"
    sent_query = json.loads(synth_req.content.decode("utf-8"))
    assert sent_query["speedScale"] == 1.15
    assert sent_query["pitchScale"] == 0.05
    assert sent_query["intonationScale"] == 1.2
    assert sent_query["volumeScale"] == 1.0


@pytest.mark.requirement("REQ-2026-002-F06")
def test_synthesize_retries_on_transport_error_with_exponential_backoff() -> None:
    """T2S-I02: VoicevoxClient retries 3 connection failures and succeeds on the 4th attempt."""
    expected_wav = _make_wav_bytes()
    query_attempts = 0
    waits: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal query_attempts
        if request.url.path == "/audio_query":
            query_attempts += 1
            if query_attempts <= 3:
                msg = "connection refused"
                raise httpx.ConnectError(msg)
            return httpx.Response(200, json={"accent_phrases": []})
        return httpx.Response(200, content=expected_wav)

    settings = Settings()
    transport = httpx.MockTransport(handler)
    with VoicevoxClient(settings, transport=transport, sleep=waits.append) as client:
        result = client.synthesize("再試行テスト")

    assert result == expected_wav
    assert query_attempts == 4
    assert waits == [0.5, 1.0, 2.0]


@pytest.mark.requirement("REQ-2026-002-F06")
def test_synthesize_raises_engine_error_when_5xx_exceeds_retries() -> None:
    """T2S-I03: VoicevoxClient raises EngineError containing engine_url when 5xx persists."""
    attempts = 0
    waits: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, text="service unavailable")

    settings = Settings()
    transport = httpx.MockTransport(handler)
    with (
        VoicevoxClient(settings, transport=transport, sleep=waits.append) as client,
        pytest.raises(EngineError) as exc_info,
    ):
        client.synthesize("失敗テスト")

    assert settings.engine_url in str(exc_info.value)
    assert attempts == 4
    assert waits == [0.5, 1.0, 2.0]


@pytest.mark.requirement("REQ-2026-002-F06")
def test_synthesize_raises_engine_error_immediately_on_4xx() -> None:
    """T2S-I04: VoicevoxClient does not retry on 4xx and raises EngineError on the first call."""
    attempts = 0
    waits: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(422, text="unprocessable entity")

    settings = Settings()
    transport = httpx.MockTransport(handler)
    with (
        VoicevoxClient(settings, transport=transport, sleep=waits.append) as client,
        pytest.raises(EngineError) as exc_info,
    ):
        client.synthesize("4xxテスト")

    assert not isinstance(exc_info.value, ResourceExhausted)
    assert settings.engine_url in str(exc_info.value)
    assert attempts == 1
    assert waits == []


@pytest.mark.requirement("REQ-2026-002-F06")
def test_synthesize_raises_resource_exhausted_without_retry_on_500() -> None:
    """T2S-I05: VoicevoxClient raises ResourceExhausted immediately without retry on HTTP 500."""
    attempts = 0
    waits: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, text="internal server error")

    settings = Settings()
    transport = httpx.MockTransport(handler)
    with (
        VoicevoxClient(settings, transport=transport, sleep=waits.append) as client,
        pytest.raises(ResourceExhausted) as exc_info,
    ):
        client.synthesize("メモリ不足テスト")

    assert settings.engine_url in str(exc_info.value)
    assert attempts == 1
    assert waits == []


@pytest.mark.requirement("REQ-2026-002-F06")
def test_check_version_success_and_connection_failure() -> None:
    """T2S-I06: VoicevoxClient.check succeeds on /version 200 and raises EngineError on failure."""
    recorded: list[httpx.Request] = []

    def ok_handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, json="0.14.0")

    settings = Settings()
    with VoicevoxClient(settings, transport=httpx.MockTransport(ok_handler)) as client:
        client.check()

    assert len(recorded) == 1
    assert recorded[0].method == "GET"
    assert recorded[0].url.path == "/version"

    def fail_handler(_request: httpx.Request) -> httpx.Response:
        msg = "engine unreachable"
        raise httpx.ConnectError(msg)

    with (
        VoicevoxClient(settings, transport=httpx.MockTransport(fail_handler)) as client,
        pytest.raises(EngineError) as exc_info,
    ):
        client.check()

    assert settings.engine_url in str(exc_info.value)


@pytest.mark.requirement("REQ-2026-002-F03")
def test_register_dictionary_word_success_and_4xx_error() -> None:
    """T2S-I07: VoicevoxClient.register sends surface, pronunciation, accent_type and handles 4xx."""
    recorded: list[httpx.Request] = []

    def ok_handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(204)

    settings = Settings()
    entries = [
        DictEntry(surface="CO2", pronunciation="シーオーツー", accent_type=5),
        DictEntry(surface="pH", pronunciation="ペーハー", accent_type=1),
    ]
    with VoicevoxClient(settings, transport=httpx.MockTransport(ok_handler)) as client:
        for entry in entries:
            client.register(entry)

    assert len(recorded) == 2
    assert recorded[0].method == "POST"
    assert recorded[0].url.path == "/user_dict_word"
    assert dict(recorded[0].url.params) == {
        "surface": "CO2",
        "pronunciation": "シーオーツー",
        "accent_type": "5",
    }
    assert dict(recorded[1].url.params) == {
        "surface": "pH",
        "pronunciation": "ペーハー",
        "accent_type": "1",
    }

    def bad_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="invalid pronunciation")

    with (
        VoicevoxClient(settings, transport=httpx.MockTransport(bad_handler)) as client,
        pytest.raises(EngineError) as exc_info,
    ):
        client.register(entries[0])

    assert settings.engine_url in str(exc_info.value)
