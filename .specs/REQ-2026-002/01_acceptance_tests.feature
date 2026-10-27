Feature: txt2speech 教科書テキストの音声化

  Scenario: F03 章ごとに MP3 ができる [REQ-2026-002-F03]
    Given 見出し「第1章」「第2章」を持つ UTF-8 のテキストと、動作中の(偽の)VOICEVOX Engine
    When  `python -m src.txt2speech INPUT -o OUTDIR` を実行する
    Then  OUTDIR に `01_第1章.mp3` と `02_第2章.mp3` ができ、終了コードは 0 である

  Scenario: F05 エンジンがなければ分かる形で失敗する [REQ-2026-002-F05]
    Given VOICEVOX Engine が動いていない
    When  コマンドを実行する
    Then  エンジンの URL を示すメッセージが出て、終了コードは 3 である

  Scenario: F01 Shift_JIS の入力を読める [REQ-2026-002-F01]
    Given Shift_JIS で保存したテキスト
    When  コマンドを実行する
    Then  文字化けせずに MP3 ができる

  Scenario: F02 ルビは読みだけが読み上げられる [REQ-2026-002-F02]
    Given 「漢字《かんじ》」を含むテキスト
    When  コマンドを実行する
    Then  偽の VOICEVOX が受け取った文字列は「かんじ」であり、「漢字」は含まれない

  Scenario: F04 単語の途中で切らない [REQ-2026-002-F04]
    Given 上限を超える長さの、改行も句読点もない文
    When  チャンクに分ける
    Then  どのチャンクも上限以内で、連結すると元の文に戻る

  Scenario: F07 MP3 にタグが付く [REQ-2026-002-F07]
    Given 変換が成功した MP3
    When  タグを読む
    Then  題名は見出し、トラック番号は連番である

  Scenario: F06 チャンクの間に区切りに応じた無音が入る [REQ-2026-002-F06]
    Given 段落の区切りと読点の区切りを含む章
    When  結合する
    Then  段落の後の無音は、読点の後の無音より長い

  Scenario: F08 入力の誤りは終了コード 2 で知らせる [REQ-2026-002-F08]
    Given 存在しない入力ファイル
    When  コマンドを実行する
    Then  ファイル名を示すメッセージが出て、終了コードは 2 である
