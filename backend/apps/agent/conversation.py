"""Deterministic social-intent guard shared by mission API and the search graph.

Short courtesy messages must never reach the paid LLM or enter a broad OR-based
catalogue search. The full normalized message must match: product-bearing
sentences such as «سلام، هدفون می‌خواهم» must remain regular search requests.
"""
from __future__ import annotations

import re
from typing import Literal

from apps.catalog.services.normalization import normalize_persian_text

ConversationIntent = Literal["greeting", "help", "thanks", "goodbye"]
_PUNCTUATION = re.compile(r"[!؟?.,،؛:\s]+")
_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670]")

_GREETING = frozenset({
    "سلام", "درود", "سلام علیکم", "سلام خوبی", "سلام خوبی چطوری",
    "سلام چطوری", "سلام وقت بخیر", "سلام وقتتون بخیر",
    "صبح بخیر", "عصر بخیر", "شب بخیر", "خوبی", "چطوری",
    "چطوری خوبی", "حالت چطوره", "چه خبر", "چه خبرا", "احوال شما",
    "احوالتون چطوره", "احوالتان چطوره", "احوال شریف", "احوالات چطوره",
    "حال شما چطوره", "حال شما چگونه است", "حالتون چطوره",
    "حالتون خوبه", "حالت خوبه", "خوب هستید", "خوبین", "چطورید",
    "چطورین", "شما چطورید", "شما خوبید", "سلام حال شما چطوره",
    "سلام احوال شما", "سلام حالتون چطوره", "سلام چه خبر",
    "hi", "hello", "hey",
})
_HELP = frozenset({
    "راهنما", "کمک", "روش استفاده", "چطور ازت استفاده کنم",
    "چجوری ازت استفاده کنم", "چطور از این برنامه استفاده کنم",
    "چطوری از این برنامه استفاده کنم", "چطور باهات کار کنم",
    "چجوری باهات کار کنم", "چطور کار می کنی", "چطوری کار می کنی",
    "چه کارهایی می تونی انجام بدی", "چه کارهایی بلدی",
    "چطور با این دستیار خرید کار کنم", "راهنمای استفاده از دستیار",
})
_THANKS = frozenset({"مرسی", "ممنون", "ممنونم", "سپاس", "متشکرم", "دمت گرم", "خیلی ممنون"})
_GOODBYE = frozenset({"خداحافظ", "خدا حافظ", "فعلا", "فعلاً", "بای", "به امید دیدار"})


def classify_conversation_intent(message: str) -> ConversationIntent | None:
    if not isinstance(message, str) or len(message) > 200:
        return None
    normalized = normalize_persian_text(_DIACRITICS.sub("", message))
    normalized = _PUNCTUATION.sub(" ", normalized).strip()
    if normalized in _GREETING:
        return "greeting"
    if normalized in _HELP:
        return "help"
    if normalized in _THANKS:
        return "thanks"
    if normalized in _GOODBYE:
        return "goodbye"
    return None


def conversation_reply(intent: ConversationIntent) -> str:
    replies = {
        "greeting": "سلام! خوش اومدی. دنبال چه محصولی هستی؟ می‌تونی مدل، کاربرد یا بودجه رو بگی تا فروشگاه‌های تهران رو بررسی کنیم.",
        "help": "نام یا کاربرد محصول را بنویس؛ مثلاً «هدفون بی‌سیم تا ۳ میلیون تومان». سپس می‌توانی کالاها را مقایسه و فروشندگان را بررسی کنی. استعلام‌ها صرفاً شبیه‌سازی‌اند.",
        "thanks": "خواهش می‌کنم! هر زمان خواستی، می‌تونی جست‌وجوی خریدت را ادامه بدهی.",
        "goodbye": "خداحافظ! نتیجه‌های ذخیره‌شده مأموریتت برای ادامه در دسترس‌اند.",
    }
    return replies[intent]
