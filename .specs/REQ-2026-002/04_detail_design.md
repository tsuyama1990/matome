# L3 詳細設計: txt2speech

## 1. 方針
データは `frozen` のデータクラス。純粋な関数は I/O をしない。数値と文字列の定数は `config.py` / `reading_table.py` に置く。

## 2. `preprocess.normalize(text) -> str`
順に適用する。
1. 改行を `\n` にそろえる。
2. ルビ: 青空文庫 `([一-龥々〆ヶ]+)《([^》]+)》` → `\2`(`|親《読み》` の明示形は、親文字が漢字でなくても読みだけ)。Markdown `\[([^\]]+)\]\(([ぁ-ゟ゠-ヿー]+)\)` → `\2`(括弧の中がかなだけのときだけ。URL のリンクは対象外)。`<ruby>親<rt>読み</rt></ruby>` → `読み`(`<rp>…</rp>` は消す)。
3. 行を単位に、次の行を消す: `^[-=_*─—\s]{3,}$` の区切り線、`^[-—–\s]*\d+\s*ページ[-—–\s]*$`、`^\s*-?\s*\d+\s*-?\s*$`(数字だけの行)。
4. 図表の参照符: `[図表](?:\d+[-－]\d+|\d+)` の `図1-1`、`表2-3`、`図3` と、`\[写真\]`、`※[^\n]*`(行末まで)を消す。消した後の連続した空白を 1 つにする。
5. 読みの表(`reading_table.READINGS`、長いキーを先に): `CO2→シーオーツー`、`km/h→キロメートル毎時`、`pH→ペーハー`、`kg→キログラム`、`%→パーセント` など。
6. `\d{1,3}(,\d{3})+` のカンマを除く(`1,000` → `1000`)。
7. 箇条書き: 行頭の `^\s*(?:[-*+・]|[①-⑳]|\d+[.)])\s+` を除き、その行の末尾が文末記号(`。！？!?`)でなければ `。` を足す。
8. Markdown の装飾: 行頭の `#+\s`、`**`、`__`、`` ` ``、行頭の `>\s` を消す。
9. 3 つ以上の連続する改行を 2 つにし、前後の空白を除く。

## 3. `structure`
- 見出し行: `^#{1,2}\s+(.+)$`(題=キャプチャ)、`^(\d+(?:\.\d+)+)\s+(\S.*)$`(題=番号 + 空白 + 続き。`1.` のように点が 1 つで後ろに数字がないものは対象外)、`^(第[0-9０-９一二三四五六七八九十百]+[章節])\s*(.*)$`(題=`第N章` + 空白 + 続き。続きがなければ `第N章`)。
- `split_chapters`: 行を走査し、見出し行ごとに新しい章を始める。最初の見出しより前の本文が空白だけなら捨て、そうでなければ題が空の最初の章にする。見出し行は本文に含めない。見出しがなければ `[Chapter("", text)]`。本文が空白だけの章は作らない。
- `chapter_filename(index, title, width)`: `f"{index:0{width}d}"` + `_` + 題(使えない文字 `/ \ : * ? " < > |` と制御文字を `_` に。前後の空白と `.` を除く。80 文字まで)+ `.mp3`。題が空なら `f"{index:0{width}d}.mp3"`。`width = max(2, len(str(章の数)))`。連番は 1 から。

## 4. `chunking`
`split_chunks(body, max_chars)`:
1. 本文を空行で段落に分ける。各段落の前後の空白を除き、空なら飛ばす。
2. 段落を文末(`。！？!?` の直後。連続する文末記号と閉じ括弧 `」』）)` は前の文に含める)で文に分ける。
3. 文が `max_chars` 以下ならそのまま 1 チャンク。超える文は読点(`、，,`)の直後で分け、貪欲に詰めて `max_chars` 以下にする。
4. 読点で分けても超える断片は強制分割する。位置は、(a) `max_chars` 文字目から手前へ戻り、文字種(漢字/ひらがな/カタカナ/英数字/その他)が変わる最初の位置、(b) 戻っても見つからない(連続が `max_chars` を超える)ときは `max_chars` 文字目。
5. `boundary`: 段落の最後のチャンクは `"paragraph"`、文末で終わるものは `"sentence"`、読点で終わるものは `"comma"`、それ以外(強制)は `"other"`。
6. 保証: どのチャンクも 1 文字以上で `max_chars` 以下。段落内で、チャンクを連結すると、(段落の)前後の空白を除いた元の文字列に戻る。

`halve(text, min_chars)`: `len(text) < 2 * min_chars` なら `None`。中央の位置に最も近い「文字種が変わる位置」(なければ中央)で 2 つに分ける。どちらかが `min_chars` 未満になるなら、中央で分ける。

## 5. `audio`
- `pause_frames(boundary, settings, rate) = pause_ms[boundary] * rate // 1000`。
- `write_wav(path, data)`: バイト列(WAV)をファイルに書く。
- `join_wav_files(paths, boundaries, settings, out_path)`: 標準の `wave`。1 つ目の `(nchannels, sampwidth, framerate)` と違う WAV があれば `EngineError`。`i` 番目の WAV のフレームを書き、最後以外は `pause_frames(boundaries[i])` フレームの無音(0 のバイト列)を書く。読むのは常に 1 ファイル。

## 6. `voicevox.VoicevoxClient`
- `httpx.Client(base_url=engine_url, transport=transport, timeout=request_timeout_seconds)`。
- `check()`: `GET /version`。`httpx.TransportError` または 200 以外は `EngineError(f"VOICEVOX Engine に接続できません: {engine_url}")`。
- `register(entry)`: `POST /user_dict_word` (params: `surface`, `pronunciation`, `accent_type`)。200 以外は `EngineError`。
- `synthesize(text)`: `POST /audio_query` (params `text`, `speaker`) → JSON。`speedScale`、`pitchScale`、`intonationScale`、`volumeScale` を設定の値で上書き。`POST /synthesis` (params `speaker`, JSON=問い合わせ) → `response.content`。
- 再試行: `httpx.TransportError` と 500 以外の 5xx のとき、最大 `retries` 回(合計 `retries + 1` 回の試行)。待ちは `retry_wait_seconds * 2 ** n`(`n` は 0 から)。`sleep` は注入できる。4xx は即 `EngineError`。500 は再試行せず `ResourceExhausted`(`EngineError` の子)を投げる。
- 最終失敗の `EngineError` のメッセージに `engine_url` を含める。

## 7. `mp3`
- `check(settings)`: `[ffmpeg_path, "-version"]` を実行。`FileNotFoundError` または終了コード非 0 は `EngineError(f"ffmpeg が見つかりません: {ffmpeg_path}。FFmpeg 5 以上をインストールして PATH に通すか、--ffmpeg で指定してください")`。
- `encode(wav_path, out_path, title, album, track, settings)`:
  1. 測定: `[ffmpeg_path, "-hide_banner", "-nostats", "-i", wav, "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"]`。標準エラーの最後の `{...}` を JSON として読み、`input_i`、`input_tp`、`input_lra`、`input_thresh`、`target_offset` を得る。失敗は `EngineError(stderr)`。
  2. 変換: `[ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error", "-i", wav, ("-i", cover)?, "-map", "0:a", ("-map", "1:v", "-c:v", "copy", "-disposition:v:0", "attached_pic")?, "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}:linear=true", "-ar", rate, "-ac", "1", "-codec:a", "libmp3lame", "-b:a", bitrate, "-id3v2_version", "4", "-metadata", f"title={title}", "-metadata", f"artist={voice_name}", "-metadata", f"album={album}", "-metadata", f"track={track}", "-metadata", f"genre={genre}", out]`。終了コード非 0 は `EngineError(stderr)`。

## 8. `progress`
- `fingerprint(input_bytes, settings) -> str`: 入力のバイト列と、合成に影響する設定(話者、話速、音高、抑揚、音量、チャンクの上限、辞書の中身、ポーズ、ラウドネス、ビットレート)の JSON の SHA-256。
- `Progress.load()`: ファイルがなく、または `fingerprint` が違えば、作業ディレクトリ(`OUTDIR/.txt2speech_work`)を消して空の状態(`done_chapters=[]`)にする。
- `mark_chapter_done(index)`: `done_chapters` に足して書く(一時ファイルに書いてから置き換える)。`clear()`: 進捗ファイルと作業ディレクトリを消す。

## 9. `pipeline.run`
1. `settings`、`out_dir` の確認(`out_dir.mkdir(parents=True, exist_ok=True)` は、確認の後)。`mp3.check`、`client.check()` を呼ぶ。どちらかが失敗したら、何も作らずに例外。
2. `read_text` → `split_chapters`。`fingerprint` を求め、`Progress` を読む。
3. 辞書: 設定の CSV を `parse_dictionary` で読み、`client.register` を順に呼ぶ(進捗の再開時も毎回)。
4. 章 `i`(1 から)ごと: `done_chapters` に含まれ、MP3 が存在すれば飛ばす。`normalize(body)` → `split_chunks`。チャンク `j` の WAV は `work/chNN/JJJJ.wav`。存在すれば再合成しない。なければ `synthesize_with_halving(text)`(`ResourceExhausted` なら `halve` で分けて、前半・後半を順に合成し、WAV を結合して返す。`halve` が `None` なら `EngineError`)。
5. `join_wav_files` で `work/chNN/joined.wav` → `encoder(joined, out_dir/chapter_filename(...), title, album, track)` → 成功したら `work/chNN` を消し、`mark_chapter_done`。`title` は章の題(空なら入力ファイルの語幹)、`album` は設定か入力ファイルの語幹。前処理の後に本文が空になる章は飛ばす。
6. 全章が終わったら `progress.clear()`。作った MP3 のパスのリストを返す。進捗コールバックは `(章の番号, 章の総数, 終えたチャンク, チャンクの総数)` を通知する。

## 10. `cli.main`
`argparse`。`load_settings`(引数を `overrides` に)。`tqdm` で章とチャンクの進みを標準エラーに表示する(標準エラーが端末でないときも動く)。`InputError` → 標準エラーにメッセージ、2。`EngineError` → 3。成功時は MP3 のパスを 1 行ずつ標準出力に出す。
