# L1 全体設計: txt2speech

## 1. 構成
```
 INPUT(.txt/.md) → text_io → structure(章) → preprocess → chunking → voicevox(合成) → [チャンクの WAV をディスクへ]
                                                                   ↘ audio(順に結合+ポーズ) → mp3(ffmpeg 2 パス+タグ) → OUTDIR/NN_見出し.mp3
 起動時: config → 疎通(/version)・ffmpeg の確認 → dictionary(/user_dict_word) → progress(再開の判定)
```
`src/txt2speech/` に置く。外部との境界は 3 つ: VOICEVOX Engine(HTTP)、FFmpeg(サブプロセス)、ファイルシステム。ほかは純粋な関数。
- **純粋**: `preprocess`、`structure`、`chunking`、ポーズの計算、`config` の検証。
- **境界**: `voicevox`(`httpx`。転送を差し替え可能にしてテストする)、`mp3`(ffmpeg)、`audio`(WAV のファイル読み書き)、`text_io`、`dictionary`(CSV と HTTP)、`progress`(JSON)、`cli`(引数、進捗、出力、終了コード)。
- 調整値(上限文字数、ポーズ、再試行、話者、URL、ラウドネス、ビットレートなど)は、`config.py` の 1 つの設定にまとめ、設定ファイル(YAML)から与えられる。コードに数値を散らさない。

## 2. 主な判断
- **D1 形態素解析を使わない**: 文字種の連続を単語の近似とする(F05)。依存を増やさない。
- **D2 チャンクの WAV はディスクに置き、結合はファイルから順に読む**: 章全体をメモリに持たない。再開(F09)の根拠にもなる。
- **D3 ラウドネスは 2 パス**: 1 パス目で測り、2 パス目で測定値を使って適用する。目標 ±1.0 LUFS(F08)を、短い音声でも満たすため。
- **D4 文字コードは UTF-8(BOM 可)→ CP932 の順に試す**: 検出ライブラリを足さない。
- **D5 読みの表はコードの中のデータ**(`reading_table.py`)。専門用語は辞書(F03)で補う。
- **D6 エラーは型で分ける**: `InputError`(入力・設定。終了コード 2)、`EngineError`(VOICEVOX・FFmpeg。終了コード 3)。
- **D7 起動時に前提を確かめる**: 設定の検証、ループバック(F11)、`/version`、FFmpeg の存在。1 つでも駄目なら、何も作らずに失敗する。
- **D8 メモリ不足の対処**: エンジンが 500 を返したら、チャンクを半分に分けて再送する(再帰。下限あり)。

## 3. 検証方針
- 偽の VOICEVOX(`httpx.MockTransport`、E2E では実プロセスの偽 HTTP サーバー)で、合成の全経路を自動テストする。FFmpeg は実物を使う(なければテストは失敗させる)。ラウドネスは ffmpeg の `ebur128` で測る。
- 実機の合成品質・速度・VRAM は手動確認。
