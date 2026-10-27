# L2 アーキテクチャ: txt2speech

## 1. 型と設定(`config.py`、`models.py`)
```python
@dataclass(frozen=True)
class Settings:
    engine_url: str = "http://127.0.0.1:50021"
    speaker: int = 1
    speed_scale: float = 1.0
    intonation_scale: float = 1.0
    volume_scale: float = 1.0
    max_chunk_chars: int = 80
    retries: int = 2
    retry_wait_seconds: float = 0.5
    request_timeout_seconds: float = 60.0
    pause_ms: Mapping[str, int] = {"paragraph": 700, "sentence": 400, "comma": 200, "other": 100}
    ffmpeg_path: str = "ffmpeg"
    loudness_target_lufs: float = -16.0
    mp3_quality: int = 2            # libmp3lame -q:a
    drop_figure_references: bool = True

@dataclass(frozen=True)
class Chapter: title: str; body: str
@dataclass(frozen=True)
class Chunk: text: str; boundary: Literal["paragraph", "sentence", "comma", "other"]   # このチャンクの後の区切り
```
`InputError`、`EngineError` は `errors.py`。

## 2. 関数の契約(純粋)
| モジュール | 関数 | 契約 |
|---|---|---|
| `preprocess` | `normalize(text, settings) -> str` | F02 の (a)〜(e)。ルビは読みだけ。ページ表記と区切り線の行は行ごと消える。`drop_figure_references` が真なら図表の参照符を消す。英数字と単位は読みの表で置換(長い語を先に)。Markdown の装飾を消す(見出しの `#` は `structure` が先に使うので、`normalize` は章分割の後に各章の本文へ適用する) |
| `structure` | `split_chapters(text) -> list[Chapter]` | 見出し(`#`/`##`、`第N章`、`第N節`、`1.1` の形)で分ける。見出しの前の本文は、題名が空の章にせず最初の章に含める。見出しがなければ題名なしの 1 章 |
| `structure` | `chapter_filename(index, title, width) -> str` | `NN_題.mp3`。使えない文字(`/ \ : * ? " < > |` と制御文字)は `_`。題が空なら `NN.mp3`。長さは 80 文字まで |
| `chunking` | `split_chunks(body, max_chars) -> list[Chunk]` | F04。優先順位は 段落 > 文末 > 読点 > 強制。強制でも文字種の連続の途中で切らない(連続が `max_chars` を超えるときだけ切る)。空のチャンクは作らない。`"".join(c.text for c in chunks)` は、改行を除いた入力に等しい |
| `audio` | `pause_frames(boundary, settings, sample_rate) -> int` | ポーズの長さ(フレーム数) |
| `audio` | `join_wavs(wavs: list[bytes], boundaries, settings) -> bytes` | 同じ形式(サンプルレート、チャンネル、幅)の WAV を、区切りに応じた無音を挟んで結合。形式が違えば `EngineError` |

## 3. 境界
| モジュール | 契約 |
|---|---|
| `text_io.read_text(path) -> str` | UTF-8(BOM 可)→ CP932 の順。どちらも失敗なら `InputError(ファイル名)`。ファイルがなければ `InputError` |
| `voicevox.VoicevoxClient(settings, transport=None)` | `synthesize(text) -> bytes`(WAV)。`/audio_query?text=..&speaker=..`(POST)の結果に `speedScale`、`intonationScale`、`volumeScale` を設定して `/synthesis?speaker=..`(POST)へ。接続の失敗と 5xx は `retries` 回まで再試行(間は `retry_wait_seconds`)。4xx は再試行せず `EngineError`。最終的な失敗は `EngineError(エンジンの URL)` |
| `mp3.encode(wav, out_path, title, album, track, settings)` | `settings.ffmpeg_path` を引数のリストで呼ぶ(シェルを使わない)。`loudnorm`、`libmp3lame`、`-id3v2_version 4`、`-metadata`。FFmpeg がなければ `EngineError`。終了コードが 0 でなければ標準エラーを添えて `EngineError` |
| `pipeline.run(input_path, out_dir, settings, client, encoder) -> list[Path]` | `out_dir` がなければ作る(親も)。読み → 章に分割 → 章ごとに(`normalize` → `split_chunks` → 各チャンクを `client` → `join_wavs` → `encoder`)。進捗は `progress(chapter_index, total_chapters, done_chunks, total_chunks)` コールバック |
| `cli.main(argv) -> int` | 引数 `INPUT -o OUTDIR --speaker --engine-url --speed-scale --max-chars --ffmpeg`(`--speed-scale` は話速の倍率で、1.0 が標準)。`InputError` は 2、`EngineError` は 3、成功は 0。進捗は標準エラー、出力ファイルは標準出力 |

## 4. 依存の向き
`cli → pipeline → (voicevox, mp3, text_io, audio, chunking, structure, preprocess) → (config, models, errors)`。`preprocess`/`structure`/`chunking`/`audio` は I/O をしない。
`httpx` を実行時の依存に加える(いまは dev のみ)。

## 5. テスト構造
単体 `tests/unit/txt2speech/`(純粋な関数)、結合 `tests/integration/txt2speech/`(`voicevox` を `MockTransport` で、`mp3` を実 FFmpeg で)、E2E `tests/e2e/txt2speech/`(実プロセスと偽 HTTP サーバー)。
