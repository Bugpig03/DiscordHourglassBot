"""Site languages: the list, the visitor's language, translation helpers and localized formats.

Two kinds of text are translated:
- keys of translations.py (t('nav.home')), written in French and English there;
- inline pairs tr('Texte français', 'English text'), where the French text identifies the phrase.

French and English live in the code. Every other language has one file app/locales/<code>.json that maps
a key, or the id of a phrase (p0001, listed with its French and English text in app/locales/_phrases.json),
to its translation. A missing translation falls back to English.
"""
import json
import os
import re
from datetime import datetime
from functools import lru_cache

from flask import g, has_request_context, request

LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")
STATIC_JS_DIR = os.path.join(os.path.dirname(__file__), "static", "js")

# Menu order. html: value of <html lang>, intl: locale given to Intl.NumberFormat / toLocaleString in JS.
LANGUAGES = [
    {"code": "fr", "name": "Français", "html": "fr", "intl": "fr-FR"},
    {"code": "en", "name": "English", "html": "en", "intl": "en-US"},
    {"code": "es", "name": "Español", "html": "es", "intl": "es-ES"},
    {"code": "pt", "name": "Português (Brasil)", "html": "pt-BR", "intl": "pt-BR"},
    {"code": "it", "name": "Italiano", "html": "it", "intl": "it-IT"},
    {"code": "de", "name": "Deutsch", "html": "de", "intl": "de-DE"},
    {"code": "pl", "name": "Polski", "html": "pl", "intl": "pl-PL"},
    {"code": "tr", "name": "Türkçe", "html": "tr", "intl": "tr-TR"},
    {"code": "ru", "name": "Русский", "html": "ru", "intl": "ru-RU"},
    {"code": "hi", "name": "हिन्दी", "html": "hi", "intl": "hi-IN"},
    {"code": "ja", "name": "日本語", "html": "ja", "intl": "ja-JP"},
    {"code": "ko", "name": "한국어", "html": "ko", "intl": "ko-KR"},
]
CODES = tuple(lang["code"] for lang in LANGUAGES)
BY_CODE = {lang["code"]: lang for lang in LANGUAGES}
DEFAULT_LANG = "fr"


def normalize_lang(value: str | None) -> str | None:
    """Supported code for a cookie or header value ('pt-BR' -> 'pt'), or None."""
    if not value:
        return None
    value = value.strip().lower().replace("_", "-")
    if value in CODES:
        return value
    return value.split("-")[0] if value.split("-")[0] in CODES else None


def detect_lang() -> str:
    """Language of a visitor without a saved choice: the first supported language of the browser.

    No Accept-Language header (search engines, link previews) keeps French, as before. A browser that asks
    only for unsupported languages gets English, more widely understood than French.
    """
    header = request.accept_languages
    if not header:
        return DEFAULT_LANG
    for value, _quality in header:
        code = normalize_lang(value)
        if code:
            return code
    return "en"


def current_lang() -> str:
    """Language of the current request: the 'lang' cookie, otherwise the browser language. French outside a request."""
    if not has_request_context():
        return DEFAULT_LANG
    cached = g.get("_hg_lang")
    if cached:
        return cached
    lang = normalize_lang(request.cookies.get("lang")) or detect_lang()
    g._hg_lang = lang
    return lang


@lru_cache(maxsize=None)
def phrase_ids() -> dict[str, str]:
    """French text of every inline phrase -> its id (p0001…)."""
    try:
        with open(os.path.join(LOCALES_DIR, "_phrases.json"), encoding="utf-8") as fh:
            phrases = json.load(fh)
    except FileNotFoundError:
        return {}
    return {pair[0]: pid for pid, pair in phrases.items()}


@lru_cache(maxsize=None)
def catalog(lang: str) -> dict[str, str]:
    """Translations of one language other than French and English (key or phrase id -> text)."""
    if lang in ("fr", "en"):
        return {}
    try:
        with open(os.path.join(LOCALES_DIR, f"{lang}.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def _format(text: str, kwargs: dict) -> str:
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return text


def tr(fr: str, en: str, lang: str | None = None, **kwargs) -> str:
    """Inline translation: the French text, the English text, or the current language's translation of the pair.

    Placeholders ({name}) are filled from kwargs in every language.
    """
    lang = lang or current_lang()
    if lang == "fr":
        text = fr
    elif lang == "en":
        text = en
    else:
        pid = phrase_ids().get(fr)
        text = catalog(lang).get(pid, en) if pid else en
    return _format(text, kwargs)


@lru_cache(maxsize=None)
def _js_sources() -> str:
    """All the site's JavaScript, with escaped quotes undone, to tell which phrases the scripts use."""
    chunks = []
    for root, _dirs, files in os.walk(STATIC_JS_DIR):
        if "vendor" in root:
            continue
        for name in files:
            if name.endswith(".js"):
                with open(os.path.join(root, name), encoding="utf-8") as fh:
                    chunks.append(fh.read())
    return re.sub(r"\\(['\"`])", r"\1", "\n".join(chunks))


@lru_cache(maxsize=None)
def js_catalog(lang: str) -> dict[str, str]:
    """Phrases used by the scripts, French text -> translation, embedded in each page for HG.tr()."""
    if lang in ("fr", "en"):
        return {}
    source, translations = _js_sources(), catalog(lang)
    return {fr: translations[pid] for fr, pid in phrase_ids().items() if pid in translations and fr in source}


# ---------------------------------------------------------------------------------------------
# Numbers: same output as Intl.NumberFormat in the browser (HG.fmt)
# ---------------------------------------------------------------------------------------------
NNBSP, NBSP = "\u202f", "\u00a0"
# (thousands separator, decimal separator, minimum digits before grouping starts)
NUMBER_FORMATS = {
    "fr": (NNBSP, ",", 4), "en": (",", ".", 4), "es": (".", ",", 5), "pt": (".", ",", 4), "it": (".", ",", 4),
    "de": (".", ",", 4), "pl": (NBSP, ",", 5), "tr": (".", ",", 4), "ru": (NBSP, ",", 4), "hi": (",", ".", 4),
    "ja": (",", ".", 4), "ko": (",", ".", 4),
}


def format_number(value, decimals: int = 0, lang: str | None = None) -> str:
    """Localized number: '1 826,8' in French, '1,826.8' in English, '1.826,8' in German, '1,23,456' in Hindi."""
    try:
        number = float(value or 0)
    except (ValueError, TypeError):
        return str(value)
    lang = lang or current_lang()
    sep, dec, min_digits = NUMBER_FORMATS.get(lang, NUMBER_FORMATS["en"])
    text = f"{abs(number):.{decimals}f}"
    whole, _, frac = text.partition(".")
    if len(whole) >= min_digits:
        if lang == "hi":  # Indian grouping: last 3 digits, then groups of 2 (1,23,45,678)
            head, tail = whole[:-3], whole[-3:]
            groups = []
            while len(head) > 2:
                groups.insert(0, head[-2:])
                head = head[:-2]
            whole = sep.join(([head] if head else []) + groups + [tail])
        else:
            whole = f"{int(whole):,}".replace(",", sep)
    sign = "-" if number < 0 and float(text) != 0 else ""
    return sign + whole + (dec + frac if frac else "")


# ---------------------------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------------------------
_M = lambda s: s.split()  # noqa: E731
MONTHS = {
    "fr": _M("janvier février mars avril mai juin juillet août septembre octobre novembre décembre"),
    "en": _M("January February March April May June July August September October November December"),
    "es": _M("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre"),
    "pt": _M("janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro"),
    "it": _M("gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre"),
    "de": _M("Januar Februar März April Mai Juni Juli August September Oktober November Dezember"),
    "pl": _M("styczeń luty marzec kwiecień maj czerwiec lipiec sierpień wrzesień październik listopad grudzień"),
    "tr": _M("Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık"),
    "ru": _M("январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь"),
    "hi": _M("जनवरी फ़रवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्तूबर नवंबर दिसंबर"),
    "ja": [f"{n}月" for n in range(1, 13)],
    "ko": [f"{n}월" for n in range(1, 13)],
}
# Month after a day number, where the language declines it ("25 października", "25 октября")
MONTHS_WITH_DAY = {
    "pl": _M("stycznia lutego marca kwietnia maja czerwca lipca sierpnia września października listopada grudnia"),
    "ru": _M("января февраля марта апреля мая июня июля августа сентября октября ноября декабря"),
}
MONTHS_ABBR = {
    "fr": _M("Janv Fév Mars Avr Mai Juin Juil Août Sept Oct Nov Déc"),
    "en": _M("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec"),
    "es": _M("ene feb mar abr may jun jul ago sept oct nov dic"),
    "pt": _M("jan fev mar abr mai jun jul ago set out nov dez"),
    "it": _M("gen feb mar apr mag giu lug ago set ott nov dic"),
    "de": _M("Jan Feb Mär Apr Mai Jun Jul Aug Sep Okt Nov Dez"),
    "pl": _M("sty lut mar kwi maj cze lip sie wrz paź lis gru"),
    "tr": _M("Oca Şub Mar Nis May Haz Tem Ağu Eyl Eki Kas Ara"),
    "ru": _M("янв фев мар апр май июн июл авг сен окт ноя дек"),
    "hi": _M("जन॰ फ़र॰ मार्च अप्रैल मई जून जुल॰ अग॰ सित॰ अक्तू॰ नव॰ दिस॰"),
    "ja": MONTHS["ja"],
    "ko": MONTHS["ko"],
}
# Monday first
WEEKDAYS_SHORT = {
    "fr": _M("Lun Mar Mer Jeu Ven Sam Dim"), "en": _M("Mon Tue Wed Thu Fri Sat Sun"),
    "es": _M("lun mar mié jue vie sáb dom"), "pt": _M("seg ter qua qui sex sáb dom"),
    "it": _M("lun mar mer gio ven sab dom"), "de": _M("Mo Di Mi Do Fr Sa So"),
    "pl": _M("pon wt śr czw pt sob niedz"), "tr": _M("Pzt Sal Çar Per Cum Cmt Paz"),
    "ru": _M("пн вт ср чт пт сб вс"), "hi": _M("सोम मंगल बुध गुरु शुक्र शनि रवि"),
    "ja": _M("月 火 水 木 金 土 日"), "ko": _M("월 화 수 목 금 토 일"),
}
WEEKDAYS = {
    "fr": _M("Lundi Mardi Mercredi Jeudi Vendredi Samedi Dimanche"),
    "en": _M("Monday Tuesday Wednesday Thursday Friday Saturday Sunday"),
    "es": _M("lunes martes miércoles jueves viernes sábado domingo"),
    "pt": _M("segunda terça quarta quinta sexta sábado domingo"),
    "it": _M("lunedì martedì mercoledì giovedì venerdì sabato domenica"),
    "de": _M("Montag Dienstag Mittwoch Donnerstag Freitag Samstag Sonntag"),
    "pl": _M("poniedziałek wtorek środa czwartek piątek sobota niedziela"),
    "tr": _M("Pazartesi Salı Çarşamba Perşembe Cuma Cumartesi Pazar"),
    "ru": _M("понедельник вторник среда четверг пятница суббота воскресенье"),
    "hi": _M("सोमवार मंगलवार बुधवार गुरुवार शुक्रवार शनिवार रविवार"),
    "ja": _M("月曜日 火曜日 水曜日 木曜日 金曜日 土曜日 日曜日"),
    "ko": _M("월요일 화요일 수요일 목요일 금요일 토요일 일요일"),
}
DATE_PATTERNS = {
    "fr": "{d} {month} {y}", "en": "{Month} {d}, {y}", "es": "{d} de {month} de {y}", "pt": "{d} de {month} de {y}",
    "it": "{d} {month} {y}", "de": "{d}. {month} {y}", "pl": "{d} {month} {y}", "tr": "{d} {month} {y}",
    "ru": "{d} {month} {y} г.", "hi": "{d} {month} {y}", "ja": "{y}年{m}月{d}日", "ko": "{y}년 {m}월 {d}일",
}
DATETIME_PATTERNS = {
    "fr": "{date} à {time}", "en": "{date} at {time}", "es": "{date}, {time}", "pt": "{date} às {time}",
    "it": "{date} alle {time}", "de": "{date} um {time}", "pl": "{date}, {time}", "tr": "{date} {time}",
    "ru": "{date}, {time}", "hi": "{date}, {time}", "ja": "{date} {time}", "ko": "{date} {time}",
}


def _lang(lang: str | None) -> str:
    lang = lang or current_lang()
    return lang if lang in MONTHS else "en"


def month_name(month: int, lang: str | None = None) -> str:
    return MONTHS[_lang(lang)][month - 1]


def month_abbr(month: int, lang: str | None = None) -> str:
    return MONTHS_ABBR[_lang(lang)][month - 1]


def format_date(dt: datetime, lang: str | None = None) -> str:
    """Full date: '25 octobre 2026', 'October 25, 2026', '25. Oktober 2026', '2026年10月25日'."""
    lang = _lang(lang)
    month = (MONTHS_WITH_DAY.get(lang) or MONTHS[lang])[dt.month - 1]
    return DATE_PATTERNS[lang].format(d=dt.day, m=dt.month, y=dt.year, month=month, Month=month)


def format_datetime(dt: datetime, lang: str | None = None) -> str:
    lang = _lang(lang)
    return DATETIME_PATTERNS[lang].format(date=format_date(dt, lang), time=dt.strftime("%H:%M:%S"))


def day_month(day: int, month: int, lang: str | None = None) -> str:
    """Short chart label: '25 Oct', '25. Okt', '10月25日'."""
    lang = _lang(lang)
    if lang == "ja":
        return f"{month}月{day}日"
    if lang == "ko":
        return f"{month}월 {day}일"
    return f"{day}{'.' if lang == 'de' else ''} {month_abbr(month, lang)}"


def month_year(month: int, year: int, lang: str | None = None) -> str:
    """Short month label: 'Oct 2026', '2026年10月'."""
    lang = _lang(lang)
    if lang == "ja":
        return f"{year}年{month}月"
    if lang == "ko":
        return f"{year}년 {month}월"
    return f"{month_abbr(month, lang)} {year}"


def day_month_year(day: int, month: int, year: int, lang: str | None = None) -> str:
    """Short date: '25 oct. 2026' style labels ('25 Oct 2026', '2026年10月25日')."""
    lang = _lang(lang)
    if lang in ("ja", "ko"):
        return f"{year}{'年' if lang == 'ja' else '년 '}{day_month(day, month, lang)}"
    return f"{day_month(day, month, lang)} {year}"
