# L2 テスト計画(結合): txt2speech

| ID | 確認内容 | 期待 | 要件 |
|---|---|---|---|
| T2S-I01 | `VoicevoxClient.synthesize`: 偽の転送で `/audio_query` → `/synthesis` の順 | WAV が返る。問い合わせに話者、話速、音高、抑揚、音量が入っている | F06 |
| T2S-I02 | 接続失敗が 3 回、4 回目に成功(`retries=3`)。待ち時間の記録 | 成功する。呼び出し 4 回。待ちは 0.5、1.0、2.0 秒(倍々) | F06 |
| T2S-I03 | 5xx が続く(`retries` を超える) | `EngineError`。メッセージにエンジンの URL | F06 |
| T2S-I04 | 4xx | 再試行せず `EngineError`(呼び出し 1 回) | F06 |
| T2S-I05 | 500(メモリ不足) | 再試行せず `ResourceExhausted` | F06 |
| T2S-I06 | `check()`: `/version` が応答 / 接続失敗 | 正常 / `EngineError(URL)` | F06 |
| T2S-I07 | `register`: 行ごとに `/user_dict_word` へ、表記、読み、アクセント核位置がクエリに入る / 4xx | 呼び出しの内容どおり / `EngineError` | F03 |
| T2S-I08 | `mp3.encode`: 実際の WAV(20 秒、低い音量の正弦波)を渡す | MP3 ができる。ffprobe で題名、アーティスト、アルバム、トラック、ジャンル、44100 Hz、モノラル、約 128 kbps。統合ラウドネスが -16 ±1.0 LUFS | F08 |
| T2S-I09 | `mp3.encode`: カバー画像あり / なし | あり: 画像のストリームが入る。なし: 入らない | F08 |
| T2S-I10 | `mp3.check` / `encode`: 実行ファイルが見つからない / 壊れた WAV | `EngineError`(不在の案内 / 標準エラーを含む) | F08 |
| T2S-I11 | `audio.join_wav_files`: 3 つの WAV(ファイル)と区切り | フレーム数 = 合計 + ポーズ。形式が違えば `EngineError`。読み込みは 1 つずつ | F07 |
| T2S-I12 | `text_io.read_text`: UTF-8(BOM あり・なし)、CP932、どちらでもないバイト列、存在しない | 先の 3 つは同じ日本語。後の 2 つは `InputError` | F01 |
| T2S-I13 | `pipeline.run`: 2 章、偽クライアント、偽のエンコーダー | 章ごとに `encode` が呼ばれ、ファイル名が `01_…`、`02_…`。進捗が通知される。成功後に一時ファイルと進捗ファイルがない | F04、F09 |
| T2S-I14 | `pipeline.run`: 偽クライアントが受ける文字列 | 前処理済みで、各 `max_chunk_chars` 以内。1 件ずつ(同時に 2 件にならない) | F02、F05、F06 |
| T2S-I15 | `pipeline.run`: 偽クライアントが長いチャンクに `ResourceExhausted` | 半分に分けて再送。分けられない長さなら `EngineError`。再送後も文字列を連結すると元に戻る | F06 |
| T2S-I16 | `pipeline.run` の再開: 1 章目の完了後に 2 章目で例外 → 再実行 | 1 章目のチャンクは再合成されない。2 章目の作成済みチャンクも再合成されない。完了後に一時ファイルがない | F09 |
| T2S-I17 | `progress`: 入力か設定が変わった(`fingerprint` が違う) | 空の状態に戻り、作業ディレクトリが空になる | F09 |
| T2S-I18 | `config.load_settings`: YAML、`overrides`、未知のキー、範囲外の値、外部ホストの URL、存在しないカバー | 引数が設定ファイルに優先。後ろの 4 つは `InputError` | F10、F11 |
| T2S-I19 | `cli.main`: 引数の誤り、入力なし、エンジンなし、外部ホスト、ffmpeg なし | 終了コード 2、2、3、2、3 | F10、F11 |
| T2S-I20 | `cli.main`: 進捗の表示 | 標準エラーに出て、標準出力は MP3 のパスの一覧だけ | F10 |
| T2S-I21 | `pipeline.run` の起動時の確認: エンジンなし / ffmpeg なし | 何も作らず(出力先に MP3、作業ディレクトリ、進捗ファイルがない)に失敗。辞書の登録も行わない | F06、F08 |
