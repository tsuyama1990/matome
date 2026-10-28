# L3 詳細設計: txt2speech

## 1. 方針
データは `frozen` のデータクラス。純粋な関数は I/O をしない。数値と文字列の定数は `config.py` / `reading_table.py` に置く。

## 2. `preprocess.normalize(text) -> str`
順に適用する。
1. 改行を `\n` にそろえる。
2. ルビ: 青空文庫 `([一-龥々〆ヶ]+)《([^》]+)》` → `\2`(`|親《読み》` の明示形は `\|[^《\n|]+《([^》]+)》` → `\1`。親文字が漢字でなくても `|` ごと消して読みだけ。この明示形を先に適用する)。Markdown `\[([^\]]+)\]\(([ぁ-ゟ゠-ヿー]+)\)` → `\2`(括弧の中がかなだけのときだけ。URL のリンクは対象外)。`<ruby>親<rt>読み</rt></ruby>` → `読み`(`<rp>…</rp>` は消す)。
3. 行を単位に、次の行を消す: `^[-=_*─—\s]{3,}$` の区切り線、`^[-—–\s]*\d+\s*ページ[-—–\s]*$`、`^\s*-?\s*\d+\s*-?\s*$`(数字だけの行)。
4. 図表の参照符: `[図表](?:\d+[-－]\d+|\d+)` の `図1-1`、`表2-3`、`図3` と、`\[写真\]`、`※[^\n]*`(行末まで)を消す。消した後の連続した空白を 1 つにする。
5. 読みの表(`reading_table.READINGS`、長いキーを先に): `CO2→シーオーツー`、`km/h→キロメートル毎時`、`pH→ペーハー`、`kg→キログラム`、`%→パーセント` など。
6. `\d{1,3}(,\d{3})+` のカンマを除く(`1,000` → `1000`)。
7. 箇条書き: 行頭の `^\s*(?:[-*+・]|[①-⑳]|\d+[.)])\s+` を除き、その行の末尾が文末記号(`。！？!?`)でなければ `。` を足す。
8. Markdown の装飾: 行頭の `#+\s`、`**`、`__`、`` ` ``、行頭の `>\s` を消す。
9. 3 つ以上の連続する改行を 2 つにし、前後の空白を除く。

## 3. `structure`
- 見出し行: `^#{1,2}\s+(.+)$`(題=キャプチャ)、`^(\d+(?:\.\d+)+)\s+(\S.*)$`(題=番号 + 空白 + 続き。`1.` のように点が 1 つで後ろに数字がないものは対象外)、`^(第[0-9０-９一二三四五六七八九十百]+[章節])(?:\s+(.*))?$`(題=`第N章` + 空白 + 続き。続きがなければ `第N章`。章・節の直後が空白(全角を含む)でも行末でもない行、例えば本文の `第1章でも簡単に触れたが、…` は見出しにしない。実データの試用で、本文の文頭の「第1章でも…」が見出しと誤認された [DEC: 実機の試用])。
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
- `register(entry)`: `POST /user_dict_word` (params: `surface`, `pronunciation`, `accent_type`)。成功は 2xx(実際のエンジンは 204 を返す)。それ以外は `EngineError`。
- `synthesize(text)`: `POST /audio_query` (params `text`, `speaker`) → JSON。`speedScale`、`pitchScale`、`intonationScale`、`volumeScale` を設定の値で上書き。`POST /synthesis` (params `speaker`, JSON=問い合わせ) → `response.content`。
- 再試行: `httpx.TransportError` と 500 以外の 5xx のとき、最大 `retries` 回(合計 `retries + 1` 回の試行)。待ちは `retry_wait_seconds * 2 ** n`(`n` は 0 から)。`sleep` は注入できる。4xx は即 `EngineError`。500 は再試行せず `ResourceExhausted`(`EngineError` の子)を投げる。
- 最終失敗の `EngineError` のメッセージに `engine_url` を含める。

## 7. `mp3`
- `check(settings)`: `[ffmpeg_path, "-version"]` を実行。出力の最初の行 `ffmpeg version <N>…` のメジャーバージョンが 5 未満なら、同じ形式で `EngineError`(バージョンを示す。`N-12345-g…` のように数字で始まらない版は通す)。`FileNotFoundError` または終了コード非 0 は `EngineError(f"ffmpeg が見つかりません: {ffmpeg_path}。FFmpeg 5 以上をインストールして PATH に通すか、--ffmpeg で指定してください")`。
- `encode(wav_path, out_path, title, album, track, settings)`:
  1. 測定: `[ffmpeg_path, "-hide_banner", "-nostats", "-i", wav, "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"]`。標準エラーの最後の `{...}` を JSON として読み、`input_i`、`input_tp`、`input_lra`、`input_thresh`、`target_offset` を得る。失敗は `EngineError(stderr)`。
  2. 変換: `[ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error", "-i", wav, ("-i", cover)?, "-map", "0:a", ("-map", "1:v", "-c:v", "copy", "-disposition:v:0", "attached_pic")?, "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}:linear=true", "-ar", rate, "-ac", "1", "-codec:a", "libmp3lame", "-b:a", bitrate, "-id3v2_version", "4", "-metadata", f"title={title}", "-metadata", f"artist={voice_name}", "-metadata", f"album={album}", "-metadata", f"track={track}", "-metadata", f"genre={genre}", out]`。終了コード非 0 は `EngineError(stderr)`。

## 8. `progress`
- `fingerprint(input_bytes, dictionary_texts, cover_bytes, settings) -> str`: 入力のバイト列、辞書の CSV の中身、カバー画像のバイト列(なければ空)、最終の MP3 までに影響するすべての設定(話者、話速、音高、抑揚、音量、チャンクの上限、ポーズ、ラウドネス、サンプルレート、ビットレート、音声モデル名、書名、ジャンル)の JSON の SHA-256。ファイルのパス自体は含めない(中身が同じなら同じ)。
- `Progress(progress_path, work_dir, fingerprint)`。`load()`: ファイルがなく、または `fingerprint` が違えば、`work_dir` を消して空の状態(`done_chapters=[]`)にする。
- `mark_chapter_done(index)`: `done_chapters` に足して書く(一時ファイルに書いてから置き換える)。`clear()`: 進捗ファイルと作業ディレクトリを消す。

## 9. `pipeline.run`
1. 入力の確認と読み込み: 拡張子が `.pdf` なら `pdf_input.read_pdf_chapters`、それ以外なら `read_text`(なければ `InputError`。終了コード 2 を、エンジンの確認より先に保証する)と `split_chapters`。さらに、辞書の CSV の読み込みと `parse_dictionary`、カバー画像の読み込み(`InputError` はここで出る)。
2. 前提の確認: `mp3.check`、`client.check()`。どちらかが失敗したら、何も作らずに例外。その後 `out_dir.mkdir(parents=True, exist_ok=True)`。
3. `fingerprint` を求め、`Progress` を読む。辞書: 読み込み済みのエントリを `client.register` で順に登録する(再開時も毎回)。
4. 章 `i`(1 から)ごと: `done_chapters` に含まれ、MP3 が存在すれば飛ばす。`normalize(body)` → `split_chunks`。チャンク `j` の WAV は `work/chNN/JJJJ.wav`。存在すれば再合成しない。なければ `synthesize_with_halving(text) -> bytes`(WAV のバイト列を返す。`ResourceExhausted` なら `halve` で分けて、前半・後半を順に(それぞれ再帰的に)合成し、`audio.concat_wav_bytes` で**ポーズなしに**つないで 1 つの WAV にして返す。`halve` が `None` なら `EngineError`)。
5. `join_wav_files` で `work/chNN/joined.wav` → `encoder(joined, out_dir/chapter_filename(...), title, album, track)` → 成功したら `work/chNN` を消し、`mark_chapter_done`。`title` は章の題(空なら入力ファイルの語幹)、`album` は設定か入力ファイルの語幹。前処理の後に本文が空になる章は飛ばす。
6. 全章が終わったら `progress.clear()`。作った MP3 のパスのリストを返す。進捗コールバックは `(章の番号, 章の総数, 終えたチャンク, チャンクの総数)` を通知する。

## 9a. 章の範囲(`chapters`)
`config.parse_chapter_range` で `(first, last)` を得る。`pipeline.run` は、章を検出した後(PDF もテキストも)、番号 `i`(1 から)が範囲内の章だけを処理する。ファイル名の `NN` は、元の番号 `i`、幅は検出した章の総数から決める。進捗の通知の章の総数は、範囲内の章の数。`fingerprint` に `chapters` の文字列を含める。範囲内に章がなければ、起動時の確認の前に `InputError("指定した範囲に章がありません (…章中 …)")`。

## 10. `cli.main`
`argparse`(`--chapters` は文字列で、`overrides` の `chapters` に入れる。`--speaker` は `int`、`--speed-scale` と `--max-chars` は `float`/`int`、`--cover`/`--dictionary`/`--config` は `Path` として型変換する。指定のない引数は `overrides` に入れない)。`load_settings`(引数を `overrides` に)。`tqdm` で章とチャンクの進みを標準エラーに表示する(標準エラーが端末でないときも動く)。`InputError` → 標準エラーにメッセージ、2。`EngineError` → 3。成功時は MP3 のパスを 1 行ずつ標準出力に出す。

## 11. `pdf_input`(F12、F13)
境界(`pdfminer.six`): `read_outline(path) -> list[OutlineEntry]`、`extract_lines(path, pages) -> Iterator[LineRecord]`。壊れた PDF、暗号化された PDF は `InputError(ファイル名)`。
```python
@dataclass(frozen=True) class OutlineEntry: level: int; title: str; page: int      # page は 1 から
@dataclass(frozen=True) class LineRecord: page: int; text: str; x0: float; y0: float; size: float   # size は行の文字サイズの最頻値
```
- `read_outline`: `PDFDocument.get_outlines()` の `(level, title, dest, action, se)` を読み、`dest`(なければ `action` の `D`)の先頭要素のページ ID をページ番号にする。解決できない項目は飛ばす。
- `clean_title(raw: str) -> str`: (1) 最初の「文字化け」文字(Unicode の一般カテゴリが `Cc`、`Co`、`Cn`、または `U+FFFD`)より後ろを切る。 (2) 空白の両側が、どちらも ASCII の英数字のときだけ 1 つの空白を残し、それ以外(日本語や ASCII 記号の隣、複数の空白)の空白は除く。 (3) 前後の空白と、末尾の開き括弧(`(`、`（`)を除く。 (4) 空なら空文字を返す(呼び出し側が語幹などで補う)。
- `read_pdf_chapters(path, settings)`: (1) `read_outline`。`level <= pdf_outline_level` の項目を、ページ順(同じページは後を残す)に並べる。しおりがなければ全ページを 1 章(題は PDF のメタデータの Title、なければ入力ファイルの語幹)。 (2) 各章のページ範囲 = 開始ページ ..(次の項目の開始ページ - 1)。最後の章は最終ページまで。最初の項目より前のページは読まない。 (3) 本文の文字サイズの中央値(`median_body_size`)を、章に使う全ページの行の `size` の中央値として求める。 (4) ヘッダー・フッター: 章に使うページの行の `text`(前後の空白を除く)のうち、`pdf_repeat_min_pages` 以上のページがあり、`pdf_repeat_page_ratio` 以上のページに現れるものを、繰り返す行とする。 (5) 章ごとに `drop_noise` → `assemble_paragraphs` → `strip_note_markers` → `collapse_spaces`。 (6) 題は `reconcile_title(clean_title(title), 開始ページの先頭の行(drop_noise の後、`assemble` の前の行を上から `pdf_title_lines` 行の `text`))`。空なら空のまま(`chapter_filename` が空の題を扱う)。本文が空白だけの章は作らない。
- `drop_noise(lines, body_size, repeated, settings)`: 次の行を除く: `size < body_size * pdf_footnote_size_ratio`、`text.strip()` が数字だけ(全角を含む)、`text.strip()` が `repeated` に含まれる。
- `assemble_paragraphs(lines, settings) -> str`: ページごとに、行を `y0` の降順(上から下)、同じ `y0` は `x0` の昇順に並べる。ページ内の左端 `margin` = 行の `x0` の最小値(最頻値が望ましいが、字下げの行が多い PDF は最小値で足りる)。通常の行間 `leading` = ページ内の隣り合う行の `y0` の差の中央値。行 `i` を前の行に連結する条件: 同じページで、`x0 <= margin + pdf_indent_tolerance_pt`、かつ前の行との `y0` の差が `leading * pdf_paragraph_gap_ratio` 以下。条件を満たさなければ新しい段落(空行で区切る)。前の行が文末記号(`。！？!?」』）`)で終わり、かつ現在の行が字下げされていれば新しい段落。連結するとき、前の行の最後の文字と現在の行の最初の文字が、どちらも ASCII の英数字なら空白 1 つ、それ以外は空白なし。ページをまたぐ段落は、前のページの最後の段落が文末記号で終わらず、次のページの最初の行が字下げされていなければ連結する。
- `strip_note_markers(text) -> str`: 正規表現 `注[0-9０-９]+(?:[・，、,][0-9０-９]+)*(?!を参照|参照|を見|のとおり|の通り)` を除く(脚注の参照記号。「注意」「注文」は数字が続かないので対象外。「注４を参照」は文の一部なので残す)。
- `collapse_spaces(text) -> str`: `[ 　]{2,}` を半角の空白 1 つにする(改行は変えない)。
- `reconcile_title(outline_title: str, first_lines: Sequence[str], settings) -> str`: 比較用の正規化は、空白をすべて除き、NFKC にした文字列。`first_lines` の各行を、上から順に連結して比較する。`outline_title` の正規化と、連結したページ先頭の行の正規化とを先頭から比べ、一致する文字数 `n` を求める。`n >= pdf_title_min_match` なら、ページの側の元の文字列(空白を含む)のうち、その `n` 文字に対応する部分を取り、`clean_title` を適用して返す。そうでなければ `outline_title` を返す。`outline_title` が空なら空を返す。
