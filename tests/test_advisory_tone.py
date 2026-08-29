# -*- coding: utf-8 -*-
"""
Advisory-tone guard.

Every recommendation shown to the user (analysis screen, PDF report) must be
phrased as a suggestion ("bunu yapabilirsin"), never as an order ("bunu yap!")
and never as a guaranteed outcome ("CTR %40 artar").

Hard requirements such as login or form validation are intentionally out of
scope: they are not recommendations.
"""
import re
import subprocess
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "translations.xlsx"
APP_JS = ROOT / "static" / "App.js"
SERVER = ROOT / "server.pyw"
AI_SERVICE = ROOT / "app" / "services" / "ai_service.py"
ANALYSIS_ENGINE = ROOT / "app" / "services" / "analysis_engine.py"

LANGS = ("tr", "en", "es")

# ── Forbidden wording ────────────────────────────────────────────────────────

IMPERATIVE_PATTERNS = [
    (r"EMR[İI]\b", "Turkish 'EMRİ' (order) label"),
    (r"\bORDER\b", "English 'ORDER' label"),
    (r"\bORDEN\b", "Spanish 'ORDEN' label"),
    (r"mal[ıi]s[ıi]n", "Turkish obligation suffix '-malısın'"),
    (r"\bYou should\b", "English obligation 'You should'"),
    (r"\bDeber[íi]as\b", "Spanish obligation 'Deberías'"),
    (r"KES[İI]NL[İI]KLE", "Turkish 'KESİNLİKLE' (absolutely)"),
    (r"KES[İI]N EKLE", "Turkish 'KESİN EKLE'"),
    (r"\bDerhal\b", "Turkish 'Derhal' (immediately)"),
    (r"DEFINITELY ADD", "English 'DEFINITELY ADD'"),
    (r"AVOID COMPLETELY", "English 'AVOID COMPLETELY'"),
    (r"EVITAR COMPLETAMENTE", "Spanish 'EVITAR COMPLETAMENTE'"),
    (r"[Dd]elete immediately", "English 'delete immediately'"),
    (r"inmediatamente", "Spanish 'inmediatamente'"),
    (r"Şimdi şunları yap", "Turkish 'Şimdi şunları yap'"),
    (r"Do these now", "English 'Do these now'"),
    (r"Haz esto ahora", "Spanish 'Haz esto ahora'"),
    (r"\bacil", "Turkish 'acil' (urgent)"),
    (r"urgent", "English 'urgent'"),
    (r"urgentemente", "Spanish 'urgentemente'"),
]

GUARANTEE_PATTERNS = [
    (r"%\s*\d+\s*(?:daha\s+)?(?:art[ai]r|artacak|yükselir)", "Turkish '%N artar' promise"),
    (r"(?:increase|rise|grow)s?\s+by\s+\d+\s*%", "English 'increases by N%' promise"),
    (r"\d+\s*%\s*(?:more|extra)\s+(?:views?|view potential)", "English 'N% more views' promise"),
    (r"aumenta\s+(?:un\s+)?\d+\s*%", "Spanish 'aumenta un N%' promise"),
    (r"%\{?\w*\}?\s*more view potential", "'% more view potential' promise"),
    (r"garanti", "Turkish 'garanti' (guarantee) claim"),
    (r"\bguarantee", "English 'guarantee' claim"),
    (r"garantiz", "Spanish 'garantiz-' claim"),
]

FORBIDDEN = [(re.compile(p, re.UNICODE), why) for p, why in IMPERATIVE_PATTERNS + GUARANTEE_PATTERNS]

# ── Required advisory modality ───────────────────────────────────────────────

_ADVISORY = re.UNICODE | re.IGNORECASE
ADVISORY_MARKERS = {
    "tr": re.compile(r"abilir|ebilir|abilece|ebilece|öneri", _ADVISORY),
    "en": re.compile(r"\bcould\b|\bmay\b|\bmight\b|\bconsider\b|suggestion", _ADVISORY),
    "es": re.compile(r"podr[íi]a|puede|sugerencia", _ADVISORY),
}

# PDF keys that tell the user to change something -> must read as a suggestion.
PDF_ADVICE_KEYS = [
    "face_action",
    "retention_action",
    "tech_action",
    "seo_action",
    "urgent_actions",
    "title_longer",
    "concept_mismatch_warn",
    "seo_thumb_warn_msg",
    "thumb_seo_warn_msg",
    "fake_data_fix1",
    "fake_data_fix2",
    "perfect_match_tags",
    "inspiration_tags",
]

UI_ADVICE_KEYS = ["doThese"]

# Sample values for keys that carry .format() placeholders.
FORMAT_SAMPLES = {
    "viral_high_desc": dict(peaks=9, seo=8.1),
    "viral_low_pkg_desc": dict(peaks=9, seo=4.2, thumb=3.5),
    "viral_low": dict(peaks=2),
    "sector_std": dict(ctype="Gaming"),
    "retention_ok": dict(score=7.4),
    "tech_low": dict(peaks=3),
    "tech_ok": dict(peaks=11),
    "seo_low": dict(seo=4.2),
    "seo_thumb_warn_msg": dict(seo=8.0, thumb=3.1),
    "thumb_seo_warn_msg": dict(seo=4.0, thumb=8.2),
    "similarities_yes": dict(tags="gaming, funny"),
    "views_high": dict(views=120000),
    "views_low": dict(views=900),
    "duration_note": dict(dur="2 dakika 5 saniye", sec="125.0"),
    "duration_min": dict(m=2, s=5),
    "duration_sec": dict(s=42),
}


def _sheet(name):
    return pd.read_excel(XLSX, sheet_name=name, dtype=str).fillna("")


@pytest.fixture(scope="module")
def pdf_sheet():
    return _sheet("pdf")


@pytest.fixture(scope="module")
def ui_sheet():
    return _sheet("ui")


def _violations(text):
    return [why for rx, why in FORBIDDEN if rx.search(text)]


# ── Structural regressions ───────────────────────────────────────────────────

def test_workbook_still_has_expected_shape(pdf_sheet, ui_sheet):
    for name, df in (("pdf", pdf_sheet), ("ui", ui_sheet)):
        assert list(df.columns) == ["key", "tr", "en", "es"], f"{name} columns changed"
        assert len(df) > 100, f"{name} lost rows"
        assert df["key"].duplicated().sum() == 0, f"{name} has duplicate keys"
        for lang in LANGS:
            blank = df.loc[df[lang].str.strip() == "", "key"].tolist()
            assert not blank, f"{name}.{lang} has empty translations: {blank}"


def test_format_placeholders_survived(pdf_sheet):
    values = dict(zip(pdf_sheet["key"], pdf_sheet["tr"]))
    values_by_lang = {
        lang: dict(zip(pdf_sheet["key"], pdf_sheet[lang])) for lang in LANGS
    }
    for key, sample in FORMAT_SAMPLES.items():
        assert key in values, f"missing PDF key: {key}"
        for lang in LANGS:
            text = values_by_lang[lang][key]
            try:
                text.format(**sample)
            except (KeyError, IndexError, ValueError) as exc:
                pytest.fail(f"{key}.{lang} placeholder broken ({exc}): {text!r}")


def test_no_stray_placeholders(pdf_sheet):
    """A key with placeholders in one language must have them in all languages."""
    for _, row in pdf_sheet.iterrows():
        found = {lang: set(re.findall(r"\{(\w+)\}", row[lang])) for lang in LANGS}
        assert found["tr"] == found["en"] == found["es"], (
            f"{row['key']} placeholder mismatch across languages: {found}"
        )


# ── Tone: nothing may sound like an order or a guarantee ─────────────────────

def test_pdf_translations_are_advisory(pdf_sheet):
    problems = []
    for _, row in pdf_sheet.iterrows():
        for lang in LANGS:
            for why in _violations(row[lang]):
                problems.append(f"pdf/{row['key']}/{lang}: {why} -> {row[lang]!r}")
    assert not problems, "Imperative or guaranteed wording found:\n" + "\n".join(problems)


def test_ui_feedback_translations_are_advisory(ui_sheet):
    problems = []
    for _, row in ui_sheet.iterrows():
        for lang in LANGS:
            for why in _violations(row[lang]):
                problems.append(f"ui/{row['key']}/{lang}: {why} -> {row[lang]!r}")
    assert not problems, "Imperative or guaranteed wording found:\n" + "\n".join(problems)


@pytest.mark.parametrize("key", PDF_ADVICE_KEYS)
def test_pdf_advice_keys_offer_a_choice(pdf_sheet, key):
    row = pdf_sheet.loc[pdf_sheet["key"] == key]
    assert not row.empty, f"missing PDF key: {key}"
    for lang in LANGS:
        text = row.iloc[0][lang]
        assert ADVISORY_MARKERS[lang].search(text), (
            f"pdf/{key}/{lang} does not read as a suggestion: {text!r}"
        )


@pytest.mark.parametrize("key", UI_ADVICE_KEYS)
def test_ui_advice_keys_offer_a_choice(ui_sheet, key):
    row = ui_sheet.loc[ui_sheet["key"] == key]
    assert not row.empty, f"missing UI key: {key}"
    for lang in LANGS:
        text = row.iloc[0][lang]
        assert ADVISORY_MARKERS[lang].search(text), (
            f"ui/{key}/{lang} does not read as a suggestion: {text!r}"
        )


# ── Tone: the on-screen feedback builder ─────────────────────────────────────

def _feedback_block(path):
    src = path.read_text(encoding="utf-8")
    start = src.index("function getVideoSpecificFeedback(")
    end = src.index("\n}", start)
    return src[start:end]


def test_screen_feedback_strings_are_advisory():
    block = _feedback_block(APP_JS)
    problems = [f"{APP_JS.name}: {why}" for why in _violations(block)]
    assert not problems, "Imperative or guaranteed wording found:\n" + "\n".join(problems)


def test_screen_feedback_actions_offer_a_choice():
    """Every action pushed to the on-screen list must read as a suggestion."""
    block = _feedback_block(APP_JS)
    pushes = re.findall(r"actions\.push\((.*?)\);", block, re.DOTALL)
    assert pushes, "no actions.push(...) found - did the function change shape?"
    for push in pushes:
        literals = re.findall(r"`([^`]*)`", push)
        assert literals, f"no template literal in: {push[:80]}"
        for text in literals:
            assert any(rx.search(text) for rx in ADVISORY_MARKERS.values()), (
                f"action does not read as a suggestion: {text!r}"
            )


# ── Tone: strings embedded in the backend ────────────────────────────────────

def test_server_has_no_growth_promise():
    src = SERVER.read_text(encoding="utf-8", errors="ignore")
    problems = []
    for rx, why in [(re.compile(p, re.UNICODE), w) for p, w in GUARANTEE_PATTERNS]:
        for match in rx.finditer(src):
            line = src[: match.start()].count("\n") + 1
            problems.append(f"server.pyw:{line}: {why} -> {match.group(0)!r}")
    assert not problems, "Guaranteed-outcome wording found:\n" + "\n".join(problems)


# ── Nothing else broke ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "path",
    [APP_JS,
     ROOT / "chrome_extension" / "translations.js",
     ROOT / "chrome_extension" / "popup.js"],
    ids=["app", "ext-translations", "ext-popup"],
)
def test_app_js_still_parses(path):
    result = subprocess.run(
        ["node", "--check", str(path)],
        capture_output=True, text=True, shell=True,
    )
    assert result.returncode == 0, f"{path.name} syntax error:\n{result.stderr}"


def test_every_key_the_pdf_builder_asks_for_exists(pdf_sheet):
    """server.pyw looks keys up as L['...']; a missing one is a KeyError at export."""
    src = SERVER.read_text(encoding="utf-8", errors="ignore")
    referenced = set(re.findall(r"""L\[['"](\w+)['"]\]""", src))
    assert referenced, "no L['...'] lookups found - did the PDF builder change?"
    available = {str(k).strip() for k in pdf_sheet["key"]}
    # comparison_headers is assembled at load time from the *_headers_* keys.
    referenced.discard("comparison_headers")
    missing = sorted(referenced - available)
    assert not missing, f"PDF builder references keys absent from translations.xlsx: {missing}"


# ── Tone: the prompts we send to the model ───────────────────────────────────
#
# Static templates can be checked word by word; model output cannot. The next
# best guarantee is that every prompt which produces user-facing advice carries
# the shared wording rule, and that the rule itself says the right thing.

RULE = "ADVISORY_TONE_RULE"
RULE_CREATIVE = "ADVISORY_TONE_RULE_CREATIVE"

# A snippet unique to each prompt -> the rule that prompt must inject.
# Creative endpoints (titles, hooks, thumbnail copy) keep the asset punchy and
# soften only the surrounding guidance, so they carry the creative variant.
PROMPT_SITES = {
    "IDENTITY: You are 'Analiz Pro AI": RULE,
    "Savaş Raporu": RULE,
    '"guerilla_ozet"': RULE,
    '"Başarı Formülü"nü 3-4 cümleyle özetle': RULE,
    "bu videonun başarısını klonlayacak 3 yeni": RULE_CREATIVE,
    "CTR (Tıklanma Oranı) odaklı bir YouTube stratejistisin": RULE_CREATIVE,
    "viral içerik büyücüsüsün": RULE_CREATIVE,
    "KURAL 2 (SENTEZ)": RULE_CREATIVE,
    "benim_kancam": RULE_CREATIVE,
}

# Prompt wording that told the model to boss the creator around.
RETIRED_PROMPT_WORDING = [
    "BE DATA-RUTHLESS",
    "give direct orders",
    "command editing actions",
    "acımasız",
    "Be actionable and punchy",
]


def _enclosing_fstring(src, anchor):
    """The triple-quoted prompt literal that contains `anchor`."""
    at = src.index(anchor)
    start = src.rindex('"""', 0, at)
    end = src.index('"""', at)
    return src[start:end]


@pytest.fixture(scope="module")
def server_src():
    return SERVER.read_text(encoding="utf-8", errors="ignore")


def test_advisory_rule_constants_exist():
    src = AI_SERVICE.read_text(encoding="utf-8")
    for name in (RULE, RULE_CREATIVE):
        assert f"{name} = (" in src, f"{name} is not defined in ai_service.py"


def test_advisory_rule_does_not_itself_promise_growth():
    """The rule quotes forbidden phrases as examples; they must stay defanged."""
    import ast

    tree = ast.parse(AI_SERVICE.read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith("ADVISORY_TONE_RULE"):
                    values[target.id] = node.value.value
    assert set(values) == {RULE, RULE_CREATIVE}, f"unexpected rule constants: {sorted(values)}"
    for name, text in values.items():
        for rx, why in [(re.compile(p, re.UNICODE), w) for p, w in GUARANTEE_PATTERNS]:
            assert not rx.search(text), f"{name} contains a real growth promise: {why}"
        assert "never as an order" in text or "never as an order" in text.lower(), (
            f"{name} no longer forbids orders"
        )


@pytest.mark.parametrize("anchor,rule", sorted(PROMPT_SITES.items()))
def test_user_facing_prompt_injects_the_tone_rule(server_src, anchor, rule):
    prompt = _enclosing_fstring(server_src, anchor)
    assert f"{{{rule}}}" in prompt, (
        f"the prompt containing {anchor!r} does not inject {rule}"
    )


def test_coach_prompt_injects_the_tone_rule():
    """The analysis coach paragraph is built in ai_service, not server.pyw."""
    src = AI_SERVICE.read_text(encoding="utf-8")
    body = src[src.index("async def generate_ai_game_feedback"):]
    body = body[: body.index("async def analyze_image_with_gemini")]
    assert f"{{{RULE}}}" in body, "generate_ai_game_feedback does not inject the tone rule"


@pytest.mark.parametrize("phrase", RETIRED_PROMPT_WORDING)
def test_retired_prompt_wording_is_gone(server_src, phrase):
    ai_src = AI_SERVICE.read_text(encoding="utf-8")
    assert phrase not in server_src, f"server.pyw still tells the model: {phrase!r}"
    assert phrase not in ai_src, f"ai_service.py still tells the model: {phrase!r}"


# ── Tone: the fallback used when the model is unavailable ────────────────────

FALLBACK_ADVICE_KEYWORDS = ("editing", "montaje", "kurguyu", "intro", "introducción", "Girişi")


def _fallback_block():
    src = ANALYSIS_ENGINE.read_text(encoding="utf-8")
    start = src.index('prefix = "📢 "')
    return src[start : src.index("# ── Visual intelligence", start)]


def test_offline_fallback_is_advisory():
    block = _fallback_block()
    problems = [f"analysis_engine fallback: {why}" for why in _violations(block)]
    assert not problems, "Imperative or guaranteed wording found:\n" + "\n".join(problems)


def test_offline_fallback_advice_offers_a_choice():
    """When Groq is down we still print a sentence - it must suggest, not order."""
    block = _fallback_block()
    literals = re.findall(r'f"([^"]*)"', block)
    advice = [t for t in literals if any(k in t for k in FALLBACK_ADVICE_KEYWORDS)]
    assert len(advice) >= 6, f"expected 2 branches x 3 languages, found {len(advice)}: {advice}"
    for text in advice:
        assert any(rx.search(text) for rx in ADVISORY_MARKERS.values()), (
            f"fallback line does not read as a suggestion: {text!r}"
        )


# ── Tone: the Chrome extension and the report e-mail ─────────────────────────

EXTENSION_FILES = [
    Path("chrome_extension") / "translations.js",
    Path("chrome_extension") / "popup.js",
    Path("chrome_extension") / "popup.html",
]
EMAIL_SERVICE = ROOT / "app" / "services" / "email_service.py"

# Signing in is a hard requirement, not a recommendation, so its wording is
# allowed to stay obligatory. Same for the "🔬 Acımasız Eleştirmen" persona,
# which is a feature name rather than a piece of advice.
OUT_OF_SCOPE = re.compile(
    r"login|log in|logged in|giriş|sesión|Eleştirmen|Ruthless Critic", re.IGNORECASE
)


@pytest.mark.parametrize("rel", EXTENSION_FILES, ids=lambda p: p.name)
def test_extension_copy_is_advisory(rel):
    path = ROOT / rel
    if not path.exists():
        pytest.skip(f"{rel} not present")
    problems = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if OUT_OF_SCOPE.search(line):
            continue
        for why in _violations(line):
            problems.append(f"{rel.name}:{i}: {why} -> {line.strip()[:120]}")
    assert not problems, "Imperative or guaranteed wording found:\n" + "\n".join(problems)


def test_report_email_is_advisory():
    body = EMAIL_SERVICE.read_text(encoding="utf-8")
    problems = [f"email_service.py: {why}" for why in _violations(body)]
    assert not problems, "Imperative or guaranteed wording found:\n" + "\n".join(problems)


def test_extension_score_tiers_do_not_oblige_or_promise():
    """The badge under a DNA score is a verdict on the user's video."""
    src = (ROOT / "chrome_extension" / "translations.js").read_text(encoding="utf-8")
    tiers = re.findall(r"tier_(?:improve|viral_pot)\w*:\s*'([^']*)'", src)
    assert len(tiers) >= 6, f"tier labels not found - did the file change? {tiers}"
    for label in tiers:
        assert not _violations(label), f"tier label still commands or promises: {label!r}"
        assert "MELİ" not in label, f"tier label still uses obligation mood: {label!r}"


# ── Tone: prefilled coach questions ──────────────────────────────────────────

def test_quick_questions_do_not_imply_obligation(ui_sheet):
    """The one-tap questions are the user's own words - keep them optional too."""
    keys = [f"fast_q{i}" for i in range(1, 7)]
    for key in keys:
        row = ui_sheet.loc[ui_sheet["key"] == key]
        assert not row.empty, f"missing UI key: {key}"
        for lang in LANGS:
            text = row.iloc[0][lang]
            assert not re.search(r"malı|meli|should|debería", text, re.IGNORECASE), (
                f"ui/{key}/{lang} still sounds like an obligation: {text!r}"
            )


def test_pdf_language_table_loads_like_the_server_does(pdf_sheet):
    """Mirror of server._load_pdf_lang so a broken sheet fails here first."""
    table = {lang: {} for lang in LANGS}
    for _, row in pdf_sheet.iterrows():
        key = str(row["key"]).strip()
        if not key:
            continue
        for lang in LANGS:
            table[lang][key] = str(row[lang]).strip()
    for lang in LANGS:
        assert table[lang].get("report_title"), f"{lang}: report_title missing"
        assert table[lang].get("urgent_actions"), f"{lang}: urgent_actions missing"
        headers = [
            table[lang].get("comparison_headers_metric"),
            table[lang].get("comparison_headers_this"),
            table[lang].get("comparison_headers_avg"),
            table[lang].get("comparison_headers_diff"),
        ]
        assert all(headers), f"{lang}: comparison headers incomplete -> {headers}"
