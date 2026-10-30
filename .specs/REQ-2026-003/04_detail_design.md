# L3 詳細設計: summarize

## 1. `settings.py`
- 定数: `DEFAULT_LLM_COMMAND`、`DEFAULT_SUMMARY_RATIO = 0.2`、`DEFAULT_SUMMARY_MIN_CHARS = 300`、`DEFAULT_DENSITY_ROUNDS = 1`、`DEFAULT_LLM_RETRIES = 2`、`DEFAULT_LLM_RETRY_WAIT_SECONDS = 2.0`、`DEFAULT_LLM_TIMEOUT_SECONDS = 900.0`、`DEFAULT_MAX_PROMPT_BYTES = 100_000`。
- 検証: `0 < summary_ratio <= 1`、`summary_min_chars >= 1`、`density_rounds >= 0`、`llm_retries >= 0`、`llm_retry_wait_seconds > 0`、`llm_timeout_seconds > 0`、`max_prompt_bytes >= 1`、`llm_command` は空でなく、各要素が空でない文字列。`chapters` は `parse_chapter_range` を通す。違反は `InputError`(キーの名前を含む)。
- YAML の `llm_command` は文字列の並び。文字列 1 つなら `InputError`(分割の曖昧さを避ける)。

## 2. `prompts.py`
- `target_chars(body, settings) -> int`: `min(len(body), max(settings.summary_min_chars, round(len(body) * settings.summary_ratio)))`。
- 共通の条件文 `STYLE_RULES`(定数。F04 の各条件を 1 行ずつ)。
- `draft_prompt(title, body, target)`: 依頼文 + 目標「約 {target} 字」+ `STYLE_RULES` + `--- 本文 ---` + 題 + 本文。
- `density_prompt(title, body, current, target)`: 依頼文(足りない重要語を 1〜3 個足す/文字数は約 {target} 字を保つ/冗長な言い回しを削る)+ `STYLE_RULES` + `--- 現在の要約 ---` + current + `--- 本文 ---` + 題 + 本文。
- 文面は定数で、鍵に含める(`PROMPT_VERSION` を別に持たず、文面の連結そのものをハッシュする)。

## 3. `llm.py`
```
def run_llm(settings, prompt, sleep=time.sleep) -> str
```
- 試行は `1 + llm_retries` 回。1 回ごとに `subprocess.Popen([*settings.llm_command, prompt], stdout=一時ファイル, stderr=一時ファイル, start_new_session=True)` の `wait(timeout=settings.llm_timeout_seconds)`。出力は一時ファイルで受ける(パイプだと、子孫プロセスが書き口を握ったままのとき、終了済みのコマンドやタイムアウトの回収が止まるため)。
- `TimeoutExpired` では `os.killpg(proc.pid, SIGKILL)` の後に `wait()` で回収する。
- 出力は一時ファイルから `bytes` で読み、`decode("utf-8")` が失敗すれば失敗の試行とする。
- 成功の条件: 終了コード 0 かつ `stdout.strip()` が空でない。成功したら `stdout` をそのまま返す。
- `FileNotFoundError`(コマンドなし)は再試行せず `EngineError`(コマンド名)。`TimeoutExpired`、非 0、空出力、デコード失敗は再試行。`OSError`(引数が長すぎるなど)も再試行せず `EngineError`。待ちは `sleep(llm_retry_wait_seconds * 2**n)`(n は 0 から)。
- 尽きたら `EngineError`(コマンドの先頭の語、最後の理由、標準エラーの末尾 200 字)。`shell=True` は使わない。

## 4. `store.py`
- `cache_key(draft_prompt, density_template, settings) -> str`: `sha256(json.dumps({"draft_prompt": draft_prompt, "density_template": density_template, "rounds": settings.density_rounds, "command": list(settings.llm_command)}, sort_keys=True, ensure_ascii=False).encode("utf-8"))` の先頭 16 桁。`draft_prompt` に題、本文、目標、書式の条件が入っているので、それらの変更はすべて鍵に出る。`density_template` は書き直しの依頼文の定数。
- ファイル名: `f"{index:02d}_{key}.txt"`(`index` は元の章番号。`--chapters` でも変わらない)。
- `load` はなければ `None`。`save` は一時ファイルに書いて置き換える。
- `render(items) -> str`: 各章は `f"# {title}\n\n{summary}"` とし、章どうしは `"\n\n"` で連結し、最後に改行を 1 つ付ける。題は改行を空白にして `^#+\s*` を除き、要約は各行から `^#+\s*` を除く(連続する `#` とその後ろの空白をまとめて)。
- `write_summary(path, text)`: 同じ階層の一時ファイル → `os.replace`。例外時は一時ファイルを消す。

## 5. `pipeline.py`
- `summarize_chapter(title, body, settings, run, store...) -> str`: draft → `density_rounds` 回の書き直し。`run` の `EngineError` は捕捉し、章の題を付けた `EngineError`(元の例外を `from` で連鎖)にして送出する。各結果は `strip()`。呼び出しの直前に、実際のプロンプトの大きさを検査する(超えれば `InputError`、章の題)。
- `run(input_path, out_dir, settings, run_llm=run_llm, progress_cb=...) -> Path`: 「アーキテクチャ 4」の流れ。`progress_cb(i, total, title)` は章ごと(保存を使う章も)に呼ばれ、cli が標準エラーに `要約 i/N: 題` を出す。

## 6. `cli.py`
- 引数: `INPUT`、`-o/--out-dir`(必須)、`--config`、`--chapters`。設定 = YAML + `--chapters` の上書き。
- 最初に標準エラーへ F09 の 1 行。続いて `run`。成功したら summary.md のパスを標準出力へ。
- `InputError` → 2、`EngineError` → 3(メッセージは標準エラー)。

## 7. `txt2speech/chapters.py`(移設)
- `_load_inputs` のうち章を作る部分(PDF/text の判定、`read_pdf_chapters`/`read_text`+`split_chapters`)を `load_chapters`、`_select_in_range_chapters` を `select_chapters` として出す。`pipeline.py` は両方を使う。移設以外は変えない。
