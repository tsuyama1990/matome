# L1 全体設計: txt2speech

## 1. 構成
```
 INPUT(.txt/.md) → text_io → preprocess → structure(章) → chunking → voicevox(合成) → audio(結合+ポーズ) → mp3(ffmpeg) → OUTDIR/NN_見出し.mp3
```
`src/txt2speech/` に置く。外部との境界は 2 つだけ: VOICEVOX Engine(HTTP)と FFmpeg(サブプロセス)。ほかは純粋な関数。
- **純粋**: `preprocess`、`structure`、`chunking`、`audio` のポーズ計算と WAV の結合(標準の `wave`)。
- **境界**: `voicevox`(HTTP クライアント。`httpx`。転送を差し替え可能にしてテストする)、`mp3`(ffmpeg を呼ぶ)、`text_io`(ファイル)、`cli`(引数、出力、終了コード)。
- 調整値(上限文字数、ポーズの長さ、再試行回数、話者 ID、URL、ラウドネスの目標)は、`config.py` の 1 つの設定にまとめる。コードに数値を散らさない。

## 2. 主な判断
- **D1 形態素解析を使わない**: 文字種の連続(漢字、カタカナ、英数字)を単語の近似とする。依存を増やさず、MVP の「単語途中で切らない」を満たす。精度が足りなければ backlog で形態素解析を導入する。
- **D2 結合は WAV の段階で行い、MP3 化は章ごとに 1 回**: 再エンコードの劣化とタグ付けの手間を減らす。ラウドネスは、MP3 化と同じ ffmpeg の呼び出しで行う。
- **D3 文字コードは UTF-8(BOM 可)→ CP932 の順に試す**: 検出ライブラリを足さない。
- **D4 読みの表は、コードの中のデータ**(`reading_table.py` の辞書)。ユーザー辞書の CSV 同期(要求 3.1.3)は backlog。
- **D5 エラーは型で分ける**: `InputError`(入力・設定。終了コード 2)、`EngineError`(VOICEVOX・FFmpeg。終了コード 3)。

## 3. 検証方針
- 偽の VOICEVOX(`httpx.MockTransport`)で、合成の全経路を自動テストする。FFmpeg は実物を使う(ある環境のみ。なければテストを飛ばさず失敗させる)。
- 実機の合成品質(速度、音質)は手動確認。
