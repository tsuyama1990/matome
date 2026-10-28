# L3 テスト計画(単体): summarize

| ID | 対象 | 入力 | 期待 | 要件 |
|---|---|---|---|---|
| SUM-U01 | `target_chars` | 本文 1,000 字・ratio 0.2・min 300 / 本文 10,956 字 / 本文 100 字 | 300 / 2191 / 100(本文が上限) | F02 |
| SUM-U02 | `target_chars` 境界 | ratio 1.0 で本文 200 字、min 300 / 本文 300 字 / 本文 301 字・ratio 0.2 | 200 / 300 / 301 は 300 | F02 |
| SUM-U03 | `draft_prompt` | 題・本文・target 300 | 「約 300 字」、題、本文、`STYLE_RULES` の各条件を含み、本文は最後の区切りの後ろにある | F02、F04 |
| SUM-U04 | `density_prompt` | current に固有の文字列 | current と本文の両方を含み、current が本文より前にある。「約 N 字」が target | F03 |
| SUM-U05 | `STYLE_RULES` | — | 本文だけ/話し言葉/記号を使わない/英語の読み/構成/本文のみ、の 6 条件が別々の行にある | F04 |
| SUM-U06 | `cache_key` | 題・本文・ratio・min・rounds・command・書式の条件・書き直しの依頼文のそれぞれ 1 つだけを変える | 8 通りとも鍵が変わる。同じ入力は同じ鍵。`llm_retries` などを変えても鍵は変わらない | F06 |
| SUM-U07 | 保存のファイル名 | index 6、鍵 `abc` | `06_abc.txt` | F06 |
| SUM-U08 | `render` | 2 章 | `# 題1\n\n要約1\n\n# 題2\n\n要約2\n`(日本語、末尾の改行 1 つ) | F05 |
| SUM-U17 | `render` | 題 `# 第1章\n続き`、要約の行 `# 見出し風`・`## 二段`・`### 三段`・`本文 # 途中` | 題は `第1章 続き`。行頭の連続する `#` と後ろの空白だけが消え(`二段`、`三段`)、`本文 # 途中` は残る | F05 |
| SUM-U09 | `render` と txt2speech の `split_chapters` | render の結果 | 同じ題・同じ本文の 2 章に戻る | F05 |
| SUM-U10 | 設定の検証 | ratio 0 / 1.1 / min 0 / rounds -1 / retries -1 / wait 0 / timeout 0 / max_prompt 0 | すべて `InputError`。メッセージにキー名 | F08 |
| SUM-U11 | 設定の検証 | `llm_command` が [] / 文字列 / [""] | `InputError` | F08 |
| SUM-U12 | 設定の検証 | 未知のキー / `chapters` が `5-2` | `InputError` | F08 |
| SUM-U13 | 設定の既定 | 空の設定 | 要件 F02・F08 に書いた既定と一致 | F02、F08 |
| SUM-U14 | `summarize_chapter` | 偽の `run`(呼び出しを記録)・rounds 0 / 1 / 3 | 呼び出し 1 / 2 / 4 回。戻り値は最後の応答の `strip()` | F03 |
| SUM-U15 | プロンプトの大きさの検査 | 日本語 40,000 字の本文(約 120 KB) / 本文は小さいが `llm_command` の引数が長く合計が上限を超える | どちらも `InputError`(章の題)。3 バイト文字をバイト数で数え、コマンドの引数を含める | F07 |
| SUM-U16 | `chapters.select_chapters` | `None` / `"2"` / `"2-3"` / `"2-"` / `"-2"` | txt2speech の既存の範囲指定と同じ | F01 |
