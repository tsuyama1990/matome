Feature: summarize 本文の章ごとの要約(読み上げ用)

  Scenario: F05 章ごとの要約が summary.md になる [REQ-2026-003-F05]
    Given 見出し「第1章」「第2章」を持つ UTF-8 のテキストと、偽の LLM コマンド
    When  `python -m src.summarize INPUT -o OUTDIR --config config.yaml` を実行する
    Then  OUTDIR/summary.md に `# 第1章`、要約、`# 第2章`、要約 の順に入り、終了コードは 0 である

  Scenario: F02 要約の目標の文字数がプロンプトに入る [REQ-2026-003-F02]
    Given 本文が 1,000 字の章と、`summary_ratio` 0.2、`summary_min_chars` 300
    When  実行する
    Then  LLM に渡されたプロンプトに「約 300 字」が含まれる

  Scenario: F03 密度を上げる書き直しを指定の回数行う [REQ-2026-003-F03]
    Given `density_rounds` 2
    When  1 章を要約する
    Then  LLM は 3 回呼ばれ、2、3 回目のプロンプトに本文と直前の要約が含まれ、summary.md には 3 回目の結果が入る

  Scenario: F04 読み上げ向けの条件がプロンプトにある [REQ-2026-003-F04]
    Given 任意の章
    When  実行する
    Then  1 回目のプロンプトに、本文だけを使うこと、話し言葉、記号を使わないこと、英語の読み、構成、本文のみを出力すること、の条件が含まれる

  Scenario: F06 同じ入力の再実行では LLM を呼ばない [REQ-2026-003-F06]
    Given 一度成功した実行
    When  同じ入力・設定で再実行する
    Then  LLM は呼ばれず、summary.md は同じ内容である
    And   `summary_ratio` を変えて再実行すると、LLM が呼ばれる

  Scenario: F07 大きすぎる章は LLM を呼ぶ前に分かる [REQ-2026-003-F07]
    Given プロンプトが `max_prompt_bytes` を超える章
    When  実行する
    Then  終了コード 2、標準エラーにその章の題、LLM は一度も呼ばれない

  Scenario: F07 LLM が失敗し続けると、どの章かが分かる [REQ-2026-003-F07]
    Given 2 章目で必ず失敗する LLM コマンド
    When  実行する
    Then  終了コード 3、標準エラーに 2 章目の題、summary.md はなく、1 章目の保存は残る

  Scenario: F01 章の範囲を指定できる [REQ-2026-003-F01]
    Given 3 章のテキスト
    When  `--chapters 2` で実行する
    Then  summary.md には 2 章目だけが入る

  Scenario: F08 未知の設定キーは失敗する [REQ-2026-003-F08]
    Given 未知のキーを含む設定ファイル
    When  実行する
    Then  終了コード 2 で、そのキーの名前が標準エラーに出る

  Scenario: F09 外部送信を最初に知らせる [REQ-2026-003-F09]
    Given 任意の入力
    When  実行する
    Then  標準エラーの最初の行に、送り先のコマンドの名前が含まれる

  Scenario: F02 短い章では本文より長い要約を求めない [REQ-2026-003-F02]
    Given 本文が 100 字の章と、`summary_min_chars` 300
    When  実行する
    Then  プロンプトの目標は「約 100 字」である

  Scenario: F05 失敗した実行は既存の summary.md に触れない [REQ-2026-003-F05]
    Given 成功済みの summary.md があり、設定を変えて LLM が失敗する
    When  実行する
    Then  終了コード 3 で、summary.md は元のままである

  Scenario: F05 要約の行頭の # は見出しにならない [REQ-2026-003-F05]
    Given 要約の中に `# 見出しのような行` を返す LLM
    When  実行し、summary.md を txt2speech の章分割に通す
    Then  章の数は変わらない

  Scenario: F07 要約が伸びて送れなくなったら、その章の題で止まる [REQ-2026-003-F07]
    Given 1 回目で非常に長い要約を返し、書き直しのプロンプトが上限を超える LLM
    When  実行する
    Then  終了コード 2、標準エラーにその章の題

  Scenario: F07 タイムアウトでは子プロセスも残らない [REQ-2026-003-F07]
    Given 子プロセスを起こして眠り続ける LLM コマンドと、短い `llm_timeout_seconds`
    When  実行する
    Then  終了コード 3 で、子プロセスも終了している

  Scenario: F08 章ごとの進捗が出る [REQ-2026-003-F08]
    Given 2 章の入力
    When  実行する
    Then  標準エラーに `要約 1/2` と `要約 2/2` の行が出る

  Scenario: F08 コマンド行の --chapters は設定ファイルより優先する [REQ-2026-003-F08]
    Given 設定ファイルの `chapters` が 1 で、コマンド行が `--chapters 2`
    When  実行する
    Then  2 章目だけが入る
