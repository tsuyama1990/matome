# L3 詳細設計: txt2speech

## 1. 方針
データは `frozen` のデータクラス。純粋な関数は I/O をしない。数値と文字列の定数は `config.py` / `reading_table.py` に置く。

## 2. `preprocess.normalize(text, settings) -> str`
順に適用する。
1. 改行を `\n` にそろえる。
2. ルビ: 青空文庫 `([一-龥々〆ヶ]+)《([^》]+)》` → `\2`(親文字は、直前の連続した漢字・々・〆・ヶだけ。`|` で始まる明示形 `|親《読み》` は、親文字が漢字でなくても読みだけにする)。Markdown `\[([^\]]+)\]\(([ぁ-ゟ゠-ヿー]+)\)` → `\2`(括弧の中がかなだけのときだけルビとみなす。URL のリンクは対象外)。`<ruby>親<rt>読み</rt></ruby>` → `読み`(`<rp>` は消す)。
3. 行を単位に、次の行を消す: 前後が `-`/`=`/`_` の連続だけの区切り線、`--- 124 ページ ---` 形(`^[-—–\s]*\d+\s*ページ[-—–\s]*$`)、`^\s*-?\s*\d+\s*-?\s*$` の数字だけの行。
4. 図表の参照符: `drop_figure_references` が真なら `[図表](?:\d+[-－]\d+|\d+)` の `図1-1`、`表2-3`、`図3` と、`[写真]`、`※[^\n]*`(行末まで)を消す。消した後の連続した空白を 1 つにする。
5. 読みの表(`reading_table.READINGS`): 長いキーを先に、そのまま置換する。例 `CO2→シーオーツー`、`km/h→キロメートル毎時`、`pH→ペーハー`、`kg→キログラム`、`%→パーセント`。
6. 3 桁区切りの数 `\d{1,3}(,\d{3})+` はカンマを除く(`1,000` → `1000`)。数字の読み(`1000` → `せん`)は MVP では行わない(VOICEVOX に任せる)。
7. Markdown の装飾: 行頭の `#+\s`、`**`、`__`、`` ` ``、行頭の `>\s`、箇条書きの `^\s*[-*+]\s+` を消す(箇条書きの項目の後は改行を残す)。
8. 3 つ以上の連続する改行を 2 つにする。前後の空白を除く。

## 3. `structure`
- 見出し行: `^#{1,2}\s+(.+)$`(題=キャプチャ)、`^(\d+(?:\.\d+)+)\s+(\S.*)$`(題=番号 + 空白 + 続き。番号が 1 つの `1.` は対象外)、`^(第[0-9０-９一二三四五六七八九十百]+[章節])\s*(.*)$`(題=`第N章` + 空白 + 続き。続きがなければ `第N章`)。
- `split_chapters`: 行を走査し、見出し行ごとに新しい章を始める。最初の見出しより前の本文が空白だけなら捨て、そうでなければ題が空の最初の章にする。見出し行そのものは本文に含めない(題として使う)。見出しがなければ `[Chapter("", text)]`。本文が空白だけの章は作らない(ただし見出しだけの章も作らない)。
- `chapter_filename(index, title, width)`: `f"{index:0{width}d}"` + `_` + 題(使えない文字を `_` に。前後の空白と `.` を除く。80 文字まで)+ `.mp3`。題が空なら `f"{index:0{width}d}.mp3"`。`width = max(2, len(str(章の数)))`。連番は 1 から。

## 4. `chunking.split_chunks(body, max_chars) -> list[Chunk]`
1. 本文を空行で段落に分ける。各段落を前後の空白を除き、空なら飛ばす。
2. 段落を文末(`。！？!?` の直後。連続する文末記号と閉じ括弧 `」』）)` は前の文に含める)で文に分ける。
3. 文が `max_chars` 以下ならそのまま 1 チャンク。超える文は読点(`、，,`)の直後で分け、貪欲に詰めて `max_chars` 以下にする。
4. 読点で分けても超える断片は強制分割する。切る位置は `max_chars` 文字目から手前へ戻り、文字種(漢字/ひらがな/カタカナ/英数字/その他)が変わる最初の位置。戻っても見つからないとき(連続が `max_chars` を超える)は `max_chars` 文字目で切る。
5. 強制分割の位置は、(a) 文字種の連続が `max_chars` を超えない場合は、その連続の手前(文字種が変わる位置)、(b) 超える場合は `max_chars` 文字目。
6. `boundary`: 段落の最後のチャンクは `"paragraph"`、文末で終わるものは `"sentence"`、読点で終わるものは `"comma"`、それ以外(強制)は `"other"`。
7. 保証: どのチャンクも 1 文字以上で `max_chars` 以下。段落内で、チャンクを連結すると、(段落の)前後の空白を除いた元の文字列に戻る。

## 5. `audio`
- `pause_frames(boundary, settings, sample_rate) = pause_ms[boundary] * sample_rate // 1000`。
- `join_wavs`: 標準の `wave` で読む。各 WAV の `(nchannels, sampwidth, framerate)` が先頭と違えば `EngineError`。チャンク `i` の後(最後のチャンクの後を除く)に `pause_frames(boundaries[i])` フレームの無音(0 のバイト列)を入れる。出力は同じ形式の WAV。

## 6. `voicevox.VoicevoxClient`
- `httpx.Client(base_url=engine_url, transport=transport, timeout=...)`。
- `synthesize(text)`: `POST /audio_query` (params `text`, `speaker`) → JSON。`speedScale`、`intonationScale`、`volumeScale` を設定の値で上書き。`POST /synthesis` (params `speaker`, JSON=問い合わせ) → `response.content`。
- 再試行: `httpx.TransportError` と 5xx のとき、最大 `retries` 回(合計 `retries + 1` 回の試行)。待ちは `retry_wait_seconds`。`time.sleep` は注入できるようにする(テストのため)。4xx は即 `EngineError`。
- 最終失敗の `EngineError` のメッセージに `engine_url` を含める。

## 7. `mp3.encode`
`[ffmpeg_path, "-y", "-loglevel", "error", "-f", "wav", "-i", "pipe:0", "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11", "-codec:a", "libmp3lame", "-q:a", str(q), "-id3v2_version", "4", "-metadata", f"title={title}", "-metadata", f"album={album}", "-metadata", f"track={track}", str(out)]` を `subprocess.run(input=wav)` で呼ぶ。`FileNotFoundError` は `EngineError("ffmpeg が見つかりません: <ffmpeg_path>")`。終了コードが 0 でなければ `EngineError(stderr)`。

## 8. `pipeline.run` と `cli.main`
- `run`: `out_dir.mkdir(parents=True, exist_ok=True)`、`read_text` → `split_chapters` → 章ごとに `normalize(body)` → `split_chunks` → 各チャンクを `client.synthesize` → `join_wavs` → `encoder(wav, path, title, album, track)`。`title` は章の題(空なら入力ファイルの語幹)、`album` は入力ファイルの語幹、`track` は連番。前処理の後に本文が空になる章は飛ばす。
- `cli.main`: `argparse`。`InputError` → 標準エラーにメッセージ、2。`EngineError` → 3。`ファイル名の一覧` は成功時に 1 行 1 ファイルで標準出力。
