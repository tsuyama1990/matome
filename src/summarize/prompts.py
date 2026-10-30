from src.summarize.settings import SummarySettings
from src.txt2speech.errors import InputError

BODY_SEPARATOR = "--- 本文 ---"
CURRENT_SEPARATOR = "--- 現在の要約 ---"

STYLE_RULES = (
    "本文に書かれている内容だけを使い、推測や一般知識で補わない。",
    "聞いて分かる話し言葉で、1文を短くする。",
    "箇条書き・記号・括弧書き・見出し記号(#や*)は使わない。",
    "英語の理論名は初出で日本語の読みを添える(例: 「SCP理論、つまり構造・行動・成果の理論」)。",
    "構成は「この章の問い」、主要な理論・概念・主張とその根拠・事例、「この章のまとめ」の順にする。",
    "出力は要約の本文のみ。前置きや説明は書かない。",
)
_RULES_TEXT = "\n".join(f"- {rule}" for rule in STYLE_RULES)

DRAFT_TEMPLATE = (
    "以下は書籍の1章の本文です。耳で聞く音声(読み上げ)用に、要約を日本語で書いてください。\n"
    "条件:\n"
    "- 長さは約{target}字。\n" + _RULES_TEXT + "\n" + BODY_SEPARATOR + "\n{title}\n\n{body}"
)

DENSITY_TEMPLATE = (
    "以下は書籍の1章の本文と、その要約です。要約を書き直してください。\n"
    "- 本文にあって要約にない重要な固有名詞・用語・数字・事例を1〜3個足す。\n"
    "- 文字数は約{target}字を保つ。冗長な言い回しを削って場所を作る。\n" + _RULES_TEXT + "\n"
    f"{CURRENT_SEPARATOR}\n{{current}}\n" + BODY_SEPARATOR + "\n{title}\n\n{body}"
)


def target_chars(body: str, settings: SummarySettings) -> int:
    wanted = max(settings.summary_min_chars, round(len(body) * settings.summary_ratio))
    return min(len(body), wanted)


def draft_prompt(title: str, body: str, target: int) -> str:
    return DRAFT_TEMPLATE.format(target=target, title=title, body=body)


def density_prompt(title: str, body: str, current: str, target: int) -> str:
    return DENSITY_TEMPLATE.format(target=target, title=title, body=body, current=current)


def check_prompt_size(title: str, settings: SummarySettings, prompt: str) -> None:
    size = sum(len(arg.encode("utf-8")) for arg in (*settings.llm_command, prompt))
    if size > settings.max_prompt_bytes:
        msg = (
            f"章「{title}」のプロンプトが大きすぎます ({size} バイト > {settings.max_prompt_bytes})"
        )
        raise InputError(msg)
