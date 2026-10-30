# L2 テスト計画(結合): summarize

偽の LLM は、テストが書く Python スクリプト。`run_llm` を本物のサブプロセスで試す。

| ID | 確認内容 | 期待 | 要件 |
|---|---|---|---|
| SUM-I01 | `run_llm`: 偽の LLM が受け取った最後の引数を、標準出力に返す | 戻り値はその文字列(前後の空白は除かない。除くのは pipeline) | F03 |
| SUM-I02 | `run_llm`: プロンプトが日本語・改行・引用符・`$`・バッククォートを含む | 文字化けや展開がなく、そのまま渡る | F03 |
| SUM-I03 | `run_llm`: 終了コード 1 が 2 回、3 回目に成功(`llm_retries` 2) | 成功。呼び出し 3 回。待ちは 2.0、4.0 秒(待ちの関数を差し替えて記録) | F07 |
| SUM-I04 | `run_llm`: 標準出力が空(または空白だけ) | 失敗として再試行し、尽きたら `EngineError` | F07 |
| SUM-I05 | `run_llm`: `llm_timeout_seconds` を超える | 再試行し、尽きたら `EngineError`。残るプロセスがない | F07 |
| SUM-I06 | `run_llm`: コマンドが存在しない | 再試行せず `EngineError`(コマンド名を含む)。呼び出しの待ちが 0 回 | F07 |
| SUM-I15 | `run_llm`: 標準出力が UTF-8 として読めないバイト列 | 失敗として再試行し、尽きたら `EngineError` | F07 |
| SUM-I16 | `run_llm`: タイムアウト後、LLM が起こした子プロセス | 終了している(プロセスグループごと) | F07 |
| SUM-I07 | `run_llm`: `llm_retries` 0 で失敗 | 呼び出し 1 回、`EngineError` | F07 |
| SUM-I08 | `store`: 保存して読み戻す(日本語) | 同じ文字列。別の鍵では `None` | F06 |
| SUM-I09 | `store.write_summary`: 書き込み中に例外 | 既存の summary.md は壊れず、一時ファイルが残らない | F05 |
| SUM-I10 | `pipeline.run`: 偽の `run_llm`(関数)で 2 章 | 呼び出しは章ごとに `1 + density_rounds` 回。順序は draft → 書き直し | F03 |
| SUM-I11 | `pipeline.run`: 2 回目の実行 | 呼び出し 0 回。同じ summary.md | F06 |
| SUM-I12 | `pipeline.run`: 2 章目で `EngineError` | 例外が出る。メッセージに 2 章目の題。summary.md なし。1 章目の保存は残る | F07 |
| SUM-I18 | `pipeline.run`: `density_rounds` 0 で、書き直しのプロンプトなら上限を超えるが 1 回目は収まる章 | 失敗せず、呼び出し 1 回 | F07 |
| SUM-I13 | `load_chapters`(共有)に PDF、text、md | txt2speech の既存と同じ章(既存のテストが通る) | F01 |
| SUM-I17 | `pipeline.run`: 1 回目の応答が長く、書き直しのプロンプトが上限を超える | `InputError`(章の題)。2 回目の呼び出しはない | F07 |
| SUM-I14 | `load_summary_settings`: YAML を読む | キーが反映される。省略は既定 | F08 |
