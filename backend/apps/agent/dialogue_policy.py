"""Pre-search dialogue policy: typed, conservative decisions before paid LLM/search.

Three independent concerns:
1) resolve pending clarification state saved per mission;
2) answer supported buying-advice topics with non-catalog explanations;
3) classify product-attribute questions as dialogue, not product retrieval.

Only an explicit search action may reach the catalog. This module never
queries offers, calls an LLM, creates a contact attempt or guesses inventory.
"""
from __future__ import annotations

import re
from typing import Any, Literal, TypedDict

from apps.agent.amounts import NUMBER_TOKEN, toman_amount
from apps.catalog.services.normalization import normalize_persian_text

DialogueAction = Literal["clarify", "advice", "search"]


class DialogueDecision(TypedDict, total=False):
    kind: DialogueAction
    reply: str
    pending_dialogue: dict[str, str] | None
    query_override: str
    constraint_updates: dict[str, Any]


_BARE_LAP = re.compile(r"(?<!\w)لپ(?!\w)")
_LAPTOP = re.compile(r"(?:لپ\s*تاپ|لپتاپ|نوت\s*بوک)")
_WEDDING = re.compile(r"(?:عروسی|مراسم|جشن)")
_GPU = re.compile(r"(?:گرافیک|gpu|rtx|gtx|radeon)")
_SPEC = re.compile(
    r"(?:گرافیک|پردازنده|cpu|رم|ram|حافظه|ssd|باتری|نمایشگر|صفحه نمایش|"
    r"کارت صدا|سرعت|قدرت|ظرفیت|مشخصات)"
)
_QUESTION = re.compile(
    r"(?:\?|؟|چطور|چجوری|آیا|ایا|باید|لازم|نیاز|ضروری|"
    r"نمیدونم|نمی دونم|نمی دانم|کافیه|مناسبه|بهتره|"
    r"کدوم|کدام|چقدر|چه فرقی|فرق|تفاوت|توضیح بده|راهنمایی)"
)
_REQUEST = re.compile(r"(?:می ?خوام|می ?خواهم|بخرم|بخر|پیدا کن|نشون بده|پیشنهاد بده|معرفی کن)")
_GPU_MODEL = re.compile(r"(?<!\w)(?:rtx|gtx|rx)\s*\d{3,4}(?!\w)")
_USAGE_PRESENT = re.compile(r"(?:پخش|نمایش|اسلاید|موزیک|موسیقی|آهنگ|عکس|فیلم دیدن)")
_USAGE_EDIT = re.compile(r"(?:تدوین|ادیت|رندر|افکت|ساخت فیلم|پریمیر|افترافکت|after effects|premiere)")
_OTHER_PRODUCT = re.compile(r"(?:گوشی|هدفون|تلویزیون|دوربین|فشارسنج|شارژر|کیف|مانیتور)")
_BUDGET = re.compile(
    rf"(?:بودجه(?: م| من)?|تا(?: سقف)?|حداکثر(?: بودجه)?|سقف(?: بودجه)?)"
    rf"\s*(?P<amount>{NUMBER_TOKEN})\s*(?P<unit>میلیون|هزار|تومان)?"
)


def _budget(message: str) -> str | None:
    match = _BUDGET.search(message)
    return toman_amount(match.group("amount"), match.group("unit")) if match else None


def _laptop_advice() -> str:
    return (
        "هر لپ‌تاپی پردازش گرافیکی دارد، اما کارت گرافیک مجزا برای همه لازم نیست. "
        "برای وب‌گردی، آفیس، پخش اسلاید، عکس یا موسیقی در مراسم، گرافیک مجتمع "
        "معمولاً کافی است. برای تدوین سنگین ویدئو، جلوه‌های ویژه یا کار سه‌بعدی "
        "گرافیک مجزا می‌تواند مفید باشد. "
        "اگر کاربردت پخش برنامهٔ مراسم است یا تدوین فیلم، و حدود بودجه‌ات را بگویی "
        "می‌توانیم گزینه‌ها را دقیق‌تر بررسی کنیم. "
        "این راهنمای عمومی است؛ دربارهٔ سخت‌افزار هیچ محصول ثبت‌نشده‌ای ادعا نمی‌کنم."
    )


def resolve_dialogue_policy(
    message: str, state: dict[str, Any] | None,
) -> DialogueDecision | None:
    """Return a typed pre-search action, or None for ordinary grounded actions.

    Pending decisions are persisted in mission.state, never inferred from the
    latest result cards or automatically overwritten by a social response.
    """
    normalized = normalize_persian_text(message).strip(" ؟?!.,؛")
    if not normalized:
        return {"kind": "clarify", "reply": "دنبال چه محصولی هستی؟"}
    asking = bool(_QUESTION.search(normalized) or "؟" in message or "?" in message)

    state = state or {}
    old = state.get("pending_dialogue")
    pending = old if isinstance(old, dict) and old.get("slot") in {
        "product_kind", "laptop_usage", "laptop_budget",
    } else None

    if pending and _OTHER_PRODUCT.search(normalized):
        # New explicit product goal supersedes the unfinished laptop flow.
        return None

    # Explicit ambiguity: don't send a potentially wrong object to any model
    # and definitely don't use a stale "search_query" to make up a recommendation.
    if _BARE_LAP.search(normalized) and not _LAPTOP.search(normalized):
        return {
            "kind": "clarify",
            "reply": (
                "منظورت از «لپ» لپ‌تاپ است یا محصول آرایشی مربوط به صورت؟ "
                "برای عروسی قرار است دقیقاً چه کاری انجام بدهی؟"
            ),
            "pending_dialogue": {
                "slot": "product_kind",
                **({"budget": _budget(normalized)} if _budget(normalized) else {}),
            },
        }

    if pending and pending["slot"] == "product_kind":
        if _LAPTOP.search(normalized):
            return {
                "kind": "clarify",
                "reply": (
                    "متوجه شدم منظورت لپ‌تاپ است. برای عروسی قرار است عکس و "
                    "موسیقی پخش کنی یا فیلم را تدوین و ویرایش کنی؟"
                ),
                "pending_dialogue": {
                    "slot": "laptop_usage",
                    **({"budget": pending["budget"]} if pending.get("budget") else {}),
                },
            }
        if "آرایش" in normalized or "صورت" in normalized or "زیبایی" in normalized:
            return {
                "kind": "clarify",
                "reply": "متوجه شدم. محصول آرایشی موردنظر و حدود بودجه‌ات را مشخص کن.",
                "pending_dialogue": None,
            }
        return {
            "kind": "clarify",
            "reply": "هنوز مشخص نیست منظورت لپ‌تاپ است یا لوازم آرایشی؛ لطفاً یکی را مشخص کن.",
            "pending_dialogue": pending,
        }

    # A wedding event alone does not specify a computing workload.
    if _LAPTOP.search(normalized) and _WEDDING.search(normalized) and not (
        _USAGE_EDIT.search(normalized) or _USAGE_PRESENT.search(normalized)
    ) and not _SPEC.search(normalized):
        return {
            "kind": "clarify",
            "reply": "برای عروسی لپ‌تاپ را برای پخش عکس و موسیقی می‌خواهی، یا تدوین فیلم و کارهای سنگین؟",
            "pending_dialogue": {
                "slot": "laptop_usage",
                **({"budget": _budget(normalized)} if _budget(normalized) else {}),
            },
        }

    if pending and pending["slot"] == "laptop_usage":
        if _USAGE_EDIT.search(normalized) or _USAGE_PRESENT.search(normalized):
            usage = "editing" if _USAGE_EDIT.search(normalized) else "presentation"
            amount = _budget(normalized) or pending.get("budget")
            if amount:
                return {
                    "kind": "search", "query_override": "لپ تاپ",
                    "constraint_updates": {"max_price_toman": amount},
                    "pending_dialogue": None,
                }
            return {
                "kind": "clarify",
                "reply": (
                    "برای تدوین سنگین، پردازنده، رم و در برخی کارها گرافیک مجزا اهمیت دارد. "
                    if usage == "editing" else
                    "برای پخش عکس و موسیقی معمولاً گرافیک مجتمع کافی است. "
                ) + "سقف بودجه‌ات چند تومان است تا فقط مدل‌های مناسب را بررسی کنیم؟",
                "pending_dialogue": {"slot": "laptop_budget", "usage": usage},
            }
        # A new explicit laptop search is allowed, without forcing stale context.
        if _LAPTOP.search(normalized) and _BUDGET.search(normalized) and _REQUEST.search(normalized):
            return None

    if pending and pending["slot"] == "laptop_budget":
        amount = _budget(normalized)
        if amount:
            return {
                "kind": "search", "query_override": "لپ تاپ",
                "constraint_updates": {"max_price_toman": amount},
                "pending_dialogue": None,
            }
        if _USAGE_PRESENT.search(normalized) or _USAGE_EDIT.search(normalized):
            return {
                "kind": "clarify",
                "reply": "کاربردت را متوجه شدم. لطفاً سقف بودجه را به تومان بگو.",
                "pending_dialogue": {"slot": "laptop_budget", "usage": pending.get("usage", "")},
            }

    previous = normalize_persian_text(state.get("search_query") or "")
    about_laptop = bool(_LAPTOP.search(normalized) or _LAPTOP.search(previous)
                        or pending and pending.get("slot") in {"laptop_usage", "laptop_budget"})

    if _GPU.search(normalized) and asking and not (
        _GPU_MODEL.search(normalized) and _REQUEST.search(normalized)
    ):
        if about_laptop:
            return {"kind": "advice", "reply": _laptop_advice()}
        return {
            "kind": "clarify",
            "reply": "دربارهٔ گرافیک کدام دستگاه می‌پرسی؟ لپ‌تاپ، رایانه رومیزی یا محصول دیگری؟",
        }

    # An unsupported technical advice question must not be interpreted as a
    # product query. We need information, not a noisy OR catalogue query.
    if _SPEC.search(normalized) and asking and not (
        _GPU_MODEL.search(normalized) and _REQUEST.search(normalized)
    ):
        return {
            "kind": "clarify",
            "reply": "برای پاسخ فنی دقیق، کاربرد، محصول موردنظر و حدود بودجه را بگو. "
                     "بدون این اطلاعات، مدل یا مشخصاتی را از خودم حدس نمی‌زنم.",
        }

    if asking and _LAPTOP.search(normalized) and (
        "چه لپ" in normalized or "کدام لپ" in normalized or "چه مدل" in normalized
    ):
        return {
            "kind": "clarify",
            "reply": "برای پیشنهاد لپ‌تاپ، اول کاربرد و سقف بودجه‌ات را بگو تا "
                     "به‌جای فهرست پراکنده، مدل‌های مرتبط را بررسی کنیم.",
        }
    return None
