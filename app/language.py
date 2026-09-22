"""Low-latency Hindi/Hinglish and English selection for each new question."""

import re
from typing import Literal

from .intents import normalize

Language = Literal["hi", "en"]


def detect_language(message: str, previous: Language = "en") -> Language:
    text = normalize(message)
    # Respect an explicit instruction even when it is written in the other language.
    explicit = list(re.finditer(
        r"\b(?:in\s+)?(english|hindi)\s+(?:mein|me|mai|में)\b"
        r"|\b(?:in|speak|use)\s+(english|hindi)\b"
        r"|(हिंदी|हिन्दी|अंग्रेजी|अंग्रेज़ी)\s*में", text))
    if explicit:
        choice = next(group for group in explicit[-1].groups() if group)
        return "en" if choice in ("english", "अंग्रेजी", "अंग्रेज़ी") else "hi"
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    if re.search(r"\b(?:hai|hain|hu|hoon|hoga|hogi|honge|tha|thi|kya|kaise|kyu|kyun|mujhe|muje|mujhko|aap|tum|mera|meri|mere|isko|iska|iske|isme|yaha|yahan|yeh|nahi|nahin|chahiye|chaiye|karna|karne|kare|karo|kru|kro|krna|batao|batana|bata|samjhao|samjha|dikhao|dikhana|dikhaye|pura|poora|puri|saara|banana|banane|banao|banaye|banate|bolo|bolna)\b", text):
        return "hi"
    # Short follow-ups keep the ongoing conversation's language.
    if text.strip(".!? ") in ("yes", "ok", "okay", "next", "continue", "again", "demo", "tour", "lead", "leads"):
        return previous
    return "en"


PENDING_EN = {
    "show_lead_feature": "Showing the feature in the actual lead record…",
    "open_module": "Opening the CRM screen…",
    "open_leads_page": "Opening Leads…",
    "open_add_lead_form": "Opening the Add Lead form…",
    "highlight_field": "Highlighting the form field…",
    "highlight_module_control": "Highlighting the screen control…",
    "fill_demo_lead": "Filling the empty name and email fields with sample details…",
}
