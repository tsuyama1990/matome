# L2 アーキテクチャ: summarize

## 1. 設定(`src/summarize/settings.py`)
```python
@dataclass(frozen=True)
class SummarySettings:
    llm_command: tuple[str, ...] = ("agy-cli", "--model", "Gemini 4 Argon (High)", "--print-timeout", "600s", "-p")
    summary_ratio: float = 0.2         # (0, 1]
    summary_min_chars: int = 300       # >= 1
    density_rounds: int = 1            # >= 0
    llm_retries: int = 2               # >= 0
    llm_retry_wait_seconds: float = 2.0   # 倍々
    llm_timeout_seconds: float = 900.0    # > 0
    max_prompt_bytes: int = 100_000       # 1 つの引数の上限(131,072)に余裕を持たせる
    chapters: str | None = None
```
`load_summary_settings(path, overrides) -> SummarySettings`: YAML を読み(`txt2speech.config` と同じ読み方)、未知のキー・範囲外・空の `llm_command` は `InputError`。`chapters` の書式は `txt2speech.config.parse_chapter_range` で検証する。数値の既定は定数にし、`settings.py` の 1 か所に置く。

## 2. 共有する章の読み込み(`src/txt2speech/chapters.py`、新設)
```python
def load_chapters(input_path: Path, settings: Settings) -> list[Chapter]: ...
def select_chapters(chapters: list[Chapter], spec: str | None) -> list[tuple[int, Chapter]]: ...
```
`pipeline.py` の `_load_inputs`(PDF か text か)と `_select_in_range_chapters` を、そのまま移す。`pipeline.py` はここから使う(挙動は変えない。REQ-2026-002 の既存テストが保証する)。summarize は `Settings()`(既定)で呼ぶ。

## 3. モジュール(`src/summarize/`)
| モジュール | 種類 | 内容 |
|---|---|---|
| `settings.py` | 純粋 | 上記 |
| `prompts.py` | 純粋 | `target_chars(body, settings)`、`draft_prompt(title, body, target)`、`density_prompt(title, body, current, target)`。文面は定数。 |
| `llm.py` | 境界 | `run_llm(settings, prompt) -> str`: `subprocess.Popen([*llm_command, prompt], start_new_session=True)`。タイムアウトではプロセスグループを終了。失敗と再試行。 |
| `store.py` | 境界 | `cache_key(...)`、`load(work_dir, index, key) -> str | None`、`save(...)`、`render(chapters_with_summaries) -> str`(題と要約の行頭の `#` を除く)、`write_summary(path, text)`(一時ファイル → 置き換え)。 |
| `pipeline.py` | 流れ | `run(input_path, out_dir, settings, run_llm=run_llm, progress_cb=...) -> Path` |
| `cli.py`、`__main__.py` | 境界 | 引数、通知、終了コード。 |

## 4. 流れ(`pipeline.run`)
1. `load_chapters` → `select_chapters`。選ばれた章がなければ `InputError`。
2. 各章の目標の文字数とプロンプトを作り、大きさ(`llm_command` の各引数 + プロンプトの UTF-8 バイト数の合計)が `max_prompt_bytes` を超える章があれば、題を示して `InputError`(LLM は呼ばない)。`density_rounds` が 1 以上のときは、書き直しのプロンプトも、現在の要約が目標の 2 倍あるとして検査する(0 のときは書き直しがないので検査しない)。呼び出しの直前にも、実際のプロンプトで同じ検査をする。
3. 章ごとに: 保存があれば使う。なければ draft → `density_rounds` 回の書き直し → 保存。
4. すべて成功したら `summary.md` を書く。

## 5. エラーと終了コード
`InputError` → 2、`EngineError`(LLM の失敗。メッセージに章の題と、コマンドの先頭の語)→ 3。標準エラーに 1 行で出す。

## 6. 依存
追加なし(標準ライブラリの `subprocess`、`hashlib`、`json`、既存の PyYAML)。
