Feature: txt2speech 教科書テキストの音声化

  Scenario: F04 章ごとに MP3 ができる [REQ-2026-002-F04]
    Given 見出し「第1章」「第2章」を持つ UTF-8 のテキストと、動作中の(偽の)VOICEVOX Engine
    When  `python -m src.txt2speech INPUT -o OUTDIR` を実行する
    Then  OUTDIR に `01_第1章.mp3` と `02_第2章.mp3` ができ、終了コードは 0 である

  Scenario: F06 エンジンがなければ何も始めずに分かる形で失敗する [REQ-2026-002-F06]
    Given VOICEVOX Engine が動いていない
    When  コマンドを実行する
    Then  エンジンの URL を示すメッセージが出て、終了コードは 3 で、出力先に MP3 はない

  Scenario: F01 Shift_JIS の入力を読める [REQ-2026-002-F01]
    Given Shift_JIS で保存したテキスト
    When  コマンドを実行する
    Then  文字化けせずに MP3 ができる

  Scenario: F02 ルビは読みだけが読み上げられる [REQ-2026-002-F02]
    Given 「漢字《かんじ》」を含むテキスト
    When  コマンドを実行する
    Then  偽の VOICEVOX が受け取った文字列は「かんじ」であり、「漢字」は含まれない

  Scenario: F03 専門用語の辞書が最初に登録される [REQ-2026-002-F03]
    Given 辞書の CSV を指定した設定
    When  コマンドを実行する
    Then  偽の VOICEVOX は、音声の合成より前に、辞書の登録を受け取る

  Scenario: F05 単語の途中で切らない [REQ-2026-002-F05]
    Given 上限を超える長さの、改行も句読点もない文
    When  チャンクに分ける
    Then  どのチャンクも上限以内で、連結すると元の文に戻る

  Scenario: F06 メモリ不足の応答にはチャンクを半分にして再送する [REQ-2026-002-F06]
    Given 長いチャンクに 500 を返し、短いチャンクには成功する偽のエンジン
    When  コマンドを実行する
    Then  最終的に MP3 ができ、偽のエンジンは半分の長さの文字列を受け取っている

  Scenario: F07 チャンクの間に区切りに応じた無音が入る [REQ-2026-002-F07]
    Given 段落の区切りと読点の区切りを含む章
    When  結合する
    Then  段落の後の無音は、読点の後の無音より長い

  Scenario: F08 音量が目標に均一化され、タグが付く [REQ-2026-002-F08]
    Given 変換が成功した MP3
    When  ラウドネスとタグを測る
    Then  統合ラウドネスは -16 LUFS ±1.0 で、題名は見出し、トラック番号は連番、ジャンルは Audiobook である

  Scenario: F09 異常終了した後に続きから再開できる [REQ-2026-002-F09]
    Given 2 章のうち 1 章を作った後で止まった実行
    When  同じ入力と設定で再実行する
    Then  完了した章のチャンクは再び合成されず、全章が完了し、一時ファイルは残らない

  Scenario: F10 入力の誤りは終了コード 2 で知らせる [REQ-2026-002-F10]
    Given 存在しない入力ファイル
    When  コマンドを実行する
    Then  ファイル名を示すメッセージが出て、終了コードは 2 である

  Scenario: F11 ローカル以外のエンジンには送らない [REQ-2026-002-F11]
    Given エンジンの URL が外部のホストである設定
    When  コマンドを実行する
    Then  通信せずに終了コード 2 で失敗する

  Scenario: F12 PDF を直接読み、しおりの項目ごとに MP3 ができる [REQ-2026-002-F12]
    Given しおりに「第1章」「第2章」を持つ PDF と、動作中の(偽の)VOICEVOX Engine
    When  `python -m src.txt2speech book.pdf -o OUTDIR` を実行する
    Then  OUTDIR に `01_第1章….mp3` と `02_第2章….mp3` ができ、最初の項目より前のページは読まれない

  Scenario: F13 脚注とページ番号は読まれず、折り返した行は 1 つの文になる [REQ-2026-002-F13]
    Given 脚注・ページ番号・折り返した行を含む PDF
    When  コマンドを実行する
    Then  偽の VOICEVOX が受け取った文字列に、脚注の本文とページ番号は含まれず、折り返しは文として連結されている
