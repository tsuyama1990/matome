# L2 テスト計画(結合): txt2speech

| ID | 確認内容 | 期待 | 要件 |
|---|---|---|---|
| T2S-I01 | `VoicevoxClient.synthesize`: 偽の転送で `/audio_query` → `/synthesis` の順に呼ばれる | 受け取る WAV が返る。話者 ID と話速などが問い合わせに入っている | F05 |
| T2S-I02 | 接続失敗が 2 回、3 回目に成功(`retries=2`) | 成功する。呼び出し回数 3 | F05 |
| T2S-I03 | 5xx が続く(`retries` を超える) | `EngineError`。メッセージにエンジンの URL | F05 |
| T2S-I04 | 4xx | 再試行せず `EngineError`(呼び出し 1 回) | F05 |
| T2S-I05 | `mp3.encode` に実際の WAV(1 秒の無音)を渡す | MP3 ができ、ffprobe で題名、アルバム、トラック、形式(mp3)が確認できる | F07 |
| T2S-I06 | `mp3.encode`: FFmpeg の実行ファイル(`ffmpeg_path`)が見つからない | `EngineError`(不在) | F07 |
| T2S-I07 | `mp3.encode`: 壊れた WAV | `EngineError`(標準エラーを含む) | F07 |
| T2S-I08 | `pipeline.run`: 2 章、偽クライアント、偽のエンコーダー | 章ごとに `encode` が呼ばれ、ファイル名が `01_…`、`02_…`。進捗が章ごとに通知される | F03、F08 |
| T2S-I09 | `pipeline.run`: 偽クライアントが受け取る文字列 | 前処理済みで、各 80 文字以内 | F02、F04 |
| T2S-I10 | `text_io.read_text`: UTF-8(BOM あり・なし)、CP932、どちらでもないバイト列、存在しない | 先の 3 つは同じ日本語を返す。後の 2 つは `InputError` | F01 |
| T2S-I11 | `cli.main`: 引数の誤り、入力なし、エンジンなし | 終了コード 2、2、3 | F08 |
