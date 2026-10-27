import time
from collections.abc import Callable, Mapping
from types import TracebackType
from typing import Any, Self

import httpx

from src.txt2speech.config import Settings
from src.txt2speech.dictionary import DictEntry
from src.txt2speech.errors import EngineError, ResourceExhausted

_HTTP_OK = 200
_HTTP_SUCCESS_MIN = 200
_HTTP_SUCCESS_MAX = 299
_HTTP_INTERNAL_SERVER_ERROR = 500
_HTTP_SERVER_ERROR_MIN = 500
_HTTP_SERVER_ERROR_MAX = 599
_RETRY_BACKOFF_BASE = 2


class VoicevoxClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=settings.engine_url,
            transport=transport,
            timeout=settings.request_timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def check(self) -> None:
        try:
            response = self._client.get("/version")
        except httpx.TransportError as exc:
            msg = f"VOICEVOX Engine に接続できません: {self._settings.engine_url}"
            raise EngineError(msg) from exc

        if response.status_code != _HTTP_OK:
            msg = f"VOICEVOX Engine に接続できません: {self._settings.engine_url}"
            raise EngineError(msg)

    def register(self, entry: DictEntry) -> None:
        params: dict[str, str | int] = {
            "surface": entry.surface,
            "pronunciation": entry.pronunciation,
            "accent_type": entry.accent_type,
        }
        self._request_with_retry("POST", "/user_dict_word", params=params)

    def synthesize(self, text: str) -> bytes:
        query_params: dict[str, str | int] = {
            "text": text,
            "speaker": self._settings.speaker,
        }
        query_resp = self._request_with_retry("POST", "/audio_query", params=query_params)
        query_data = self._parse_query_json(query_resp)

        query_data["speedScale"] = self._settings.speed_scale
        query_data["pitchScale"] = self._settings.pitch_scale
        query_data["intonationScale"] = self._settings.intonation_scale
        query_data["volumeScale"] = self._settings.volume_scale

        synth_params: dict[str, str | int] = {"speaker": self._settings.speaker}
        synth_resp = self._request_with_retry(
            "POST",
            "/synthesis",
            params=synth_params,
            json_body=query_data,
        )
        return synth_resp.content

    def _parse_query_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            msg = f"VOICEVOX Engine の応答 JSON が不正です: {self._settings.engine_url}"
            raise EngineError(msg) from exc

        if not isinstance(data, dict):
            msg = f"VOICEVOX Engine の応答形式が不正です: {self._settings.engine_url}"
            raise EngineError(msg)
        return data

    def _sleep_for_attempt(self, attempt: int) -> None:
        wait_seconds = self._settings.retry_wait_seconds * (_RETRY_BACKOFF_BASE**attempt)
        self._sleep(wait_seconds)

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int],
        json_body: Any = None,
    ) -> httpx.Response:
        max_retries = self._settings.retries
        for attempt in range(max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    params=params,
                    json=json_body,
                )
            except httpx.TransportError as exc:
                if attempt < max_retries:
                    self._sleep_for_attempt(attempt)
                    continue
                msg = (
                    f"VOICEVOX Engine への通信に失敗しました ({path}): {self._settings.engine_url}"
                )
                raise EngineError(msg) from exc

            status = response.status_code
            if _HTTP_SUCCESS_MIN <= status <= _HTTP_SUCCESS_MAX:
                return response
            if status == _HTTP_INTERNAL_SERVER_ERROR:
                msg = (
                    f"VOICEVOX Engine で 500 エラーが発生しました ({path}): "
                    f"{self._settings.engine_url}"
                )
                raise ResourceExhausted(msg)
            if _HTTP_SERVER_ERROR_MIN <= status <= _HTTP_SERVER_ERROR_MAX and attempt < max_retries:
                self._sleep_for_attempt(attempt)
                continue

            msg = (
                f"VOICEVOX Engine がエラー ({status}) を返しました ({path}): "
                f"{self._settings.engine_url}"
            )
            raise EngineError(msg)

        msg = f"VOICEVOX Engine への要求が失敗しました ({path}): {self._settings.engine_url}"
        raise EngineError(msg)
