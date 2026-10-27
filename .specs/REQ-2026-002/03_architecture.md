# L2 アーキテクチャ: txt2speech

## 1. 型と設定(`config.py`、`models.py`)
```python
@dataclass(frozen=True)
class Settings:
    engine_url: str = "http://127.0.0.1:50021"
    speaker: int = 1
    speed_scale: float = 1.1          # 1.05〜1.20
    pitch_scale: float = 0.0
    intonation_scale: float = 1.0
    volume_scale: float = 1.0         # 固定
    max_chunk_chars: int = 80
    min_chunk_chars: int = 4          # 半減再送の下限
    retries: int = 3
    retry_wait_seconds: float = 0.5   # 指数: 0.5, 1.0, 2.0
    request_timeout_seconds: float = 60.0
    pause_ms: Mapping[str, int]       # paragraph 900, sentence 450, comma 200, other 100
    ffmpeg_path: str = "ffmpeg"
    loudness_lufs: float = -16.0
    true_peak_dbfs: float = -1.0
    loudness_range: float = 11.0
    sample_rate_hz: int = 44100
    bitrate: str = "128k"
    voice_name: str = "VOICEVOX"
    genre: str = "Audiobook"
    album: str | None = None          # None なら入力ファイルの語幹
    cover: Path | None = None
    dictionaries: tuple[Path, ...] = ()
    work_dir_name: str = ".txt2speech_work"
    progress_file_name: str = ".txt2speech_progress.json"

@dataclass(frozen=True)
class Chapter: title: str; body: str
@dataclass(frozen=True)
class Chunk: text: str; boundary: Literal["paragraph", "sentence", "comma", "other"]
```
`InputError`、`EngineError` は `errors.py`。`config.load_settings(path: Path | None, overrides: Mapping[str, object]) -> Settings`: YAML を読み(未知のキーは `InputError`)、`overrides` で上書きする。検証: `speed_scale` は 0.5〜2.0、`max_chunk_chars` は `min_chunk_chars` 以上、`retries` は 0 以上、`pause_ms` のキーは 4 種そろっている、エンジンの URL はループバック(F11。違えば `InputError`)、カバー画像・辞書の CSV・設定ファイルが存在する。

## 2. 純粋な関数
| モジュール | 関数 | 契約 |
|---|---|---|
| `preprocess` | `normalize(text) -> str` | F02 の (a)〜(f)。ページ表記と区切り線は行ごと消える。読みの表で置換(長い語を先に)。章分割の後に各章の本文へ適用する |
| `structure` | `split_chapters(text) -> list[Chapter]` | 見出し(`#`/`##`、`第N章`、`第N節`、`1.1` の形)で分ける。見出しがなければ題なしの 1 章 |
| `structure` | `chapter_filename(index, title, width) -> str` | `NN_題.mp3`。使えない文字は `_`。題が空なら `NN.mp3`。題は 80 文字まで |
| `chunking` | `split_chunks(body, max_chars) -> list[Chunk]` | F05 |
| `chunking` | `halve(text, min_chars) -> tuple[str, str] | None` | 半減再送用。文字種が変わる位置のうち中央に最も近い位置で 2 つに分ける。`min_chars` 未満になる、または分けられなければ `None` |
| `audio` | `pause_frames(boundary, settings, sample_rate) -> int` | ポーズのフレーム数 |
| `dictionary` | `parse_dictionary(text, source) -> list[DictEntry]` | CSV(表記、カタカナ読み、アクセント核位置)。先頭行は見出し。誤りは `InputError(source:行番号)` |

## 3. 境界
| モジュール | 契約 |
|---|---|
| `text_io.read_text(path) -> str` | UTF-8(BOM 可)→ CP932 の順。失敗は `InputError(ファイル名)`。ファイルがなければ `InputError` |
| `voicevox.VoicevoxClient(settings, transport=None, sleep=time.sleep)` | `check() -> None`(`GET /version`。失敗は `EngineError(URL)`)、`register(entry)`(`POST /user_dict_word`、query: surface, pronunciation, accent_type)、`synthesize(text) -> bytes`(WAV。F06 の再試行と 500 の扱い)。`synthesize` は 500 を受けたとき `ResourceExhausted` を投げ、半減再送は `pipeline` が行う |
| `audio.concat_wav_bytes(parts) -> bytes`(ポーズなしの単純連結。形式が違えば `EngineError`)、`audio.write_wav(path, data)` / `audio.join_wav_files(paths, boundaries, settings, out_path)` | ファイルから順に読み、区切りに応じた無音を挟んで `out_path` に書く。形式が違えば `EngineError`。メモリに持つのは 1 チャンク分 |
| `mp3.check(settings)` | ffmpeg の存在を確かめる(`-version`)。なければ `EngineError(案内)` |
| `mp3.encode(wav_path, out_path, title, album, track, settings)` | 2 パスのラウドネス正規化 + LAME + ID3v2.4 + カバー |
| `progress.Progress(progress_path, work_dir, fingerprint)` | JSON。`load() -> state`、`mark_chapter_done(index)`、`clear()`。`fingerprint` が違えば空の状態を返す |
| `pipeline.run(input_path, out_dir, settings, client, encoder, progress_cb) -> list[Path]` | 起動時の確認 → 辞書の登録 → 章ごとの処理(チャンクを順に合成してディスクへ、結合、MP3 化、一時ファイルの削除、章の完了を記録)。完了済みの章は飛ばし、作成済みのチャンクは再合成しない |
| `cli.main(argv) -> int` | 引数 `INPUT -o OUTDIR --config --speaker --engine-url --speed-scale --max-chars --ffmpeg --cover --album --voice-name --dictionary`。`InputError` は 2、`EngineError` は 3、成功は 0 |

## 4. 依存の向き
`cli → pipeline → (voicevox, mp3, audio, text_io, dictionary, progress, chunking, structure, preprocess) → (config, models, errors)`。`preprocess`/`structure`/`chunking` は I/O をしない。
実行時の依存に `httpx`、`pyyaml`、`tqdm` を加える。

## 5. テスト構造
単体 `tests/unit/txt2speech/`(純粋な関数)、結合 `tests/integration/txt2speech/`(`voicevox` を `MockTransport` で、`mp3` と `audio` を実 FFmpeg・実ファイルで)、E2E `tests/e2e/txt2speech/`(実プロセスと偽 HTTP サーバー)。
