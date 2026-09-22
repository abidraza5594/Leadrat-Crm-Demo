"""Fast routing for unambiguous tutorial requests; general questions use Ollama."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GuideIntent:
    kind: Literal["crm", "lead", "module"]
    module: str | None = None


MODULE_ALIASES = {
    "dashboard": r"\bdashboard\b",
    "leads": r"\bleads?\b|लीड",
    "data": r"\bdata\b",
    "invoice": r"\binvoices?\b",
    "projects": r"\bprojects?\b",
    "properties": r"\bpropert(?:y|ies)\b",
    "listing": r"\blistings?\b",
    "tasks": r"\btasks?\b",
    "reports": r"\breports?\b|रिपोर्ट",
    "users": r"\busers?\b",
    "teams": r"\bteams?\b",
    "roles": r"\broles?\b",
    "attendance": r"\battendance\b|अटेंडेंस",
    "settings": r"\b(?:settings?|global config(?:uration)?)\b",
    "profile": r"\b(?:org(?:anisation|anization)?\s+profile)\b",
}

REQUEST = r"\b(?:show|demo|tour|walkthrough|dikhao|dikhaye|samjhao|samjha|use|kaise)\b|कैसे|समझाओ|दिखाओ"
NEGATION = r"\b(?:don'?t|do not|not|never|no|nahi|nahin|mat)\b|नहीं|मत"
MUTATION = r"\b(?:delete|remove|send|save|submit|export|import|assign|reassign|edit|update)\b"


def normalize(message: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", message).casefold().replace("’", "'")).strip()


def fast_guide_intent(message: str) -> GuideIntent | None:
    text = normalize(message)
    # Do not turn negative requests, record mutations or conceptual definitions
    # into demonstrations merely because they mention a supported screen.
    if re.search(NEGATION, text) or re.search(MUTATION, text):
        return None
    request = bool(re.search(REQUEST, text))
    if request and re.search(r"\b(?:crm|application|app)\b|सीआरएम", text):
        if re.search(r"\b(?:full|complete|entire|whole|pura|poora|pure|puri|saara)\b|पूरा", text) or re.search(r"\bcrm\s+(?:tour|demo|kaise)\b", text):
            return GuideIntent("crm")
    lead = bool(re.search(MODULE_ALIASES["leads"], text))
    field_question = bool(re.search(r"\bleads?\s+(?:source|status|owner|email|notes?|documents?|comments?|tasks?|follow.?up|assignment|phone|budget|campaign)\b", text))
    create_lead = bool(re.search(
        r"\b(?:add|create)\s+(?:(?:a|an|new|the|another|ek|naya)\s+){0,3}leads?\b"
        r"|\bleads?\s+(?:ko\s+)?(?:add|create|banana|banane|banau|banao|banaye|banate)\b"
        r"|लीड.*(?:जोड़|बना|ऐड)", text))
    if lead and not field_question and (create_lead or (request and re.search(r"\bform\b|फॉर्म", text))):
        return GuideIntent("lead")
    module_only = re.sub("|".join(MODULE_ALIASES.values()), " ", text)
    module_only = re.sub(r"\b(?:show|me|the|again|how|to|use|kaise|karte|kare|hai|hain|karna|samjhao|please|live|demo|tour|dikhao|ka|ke|ko|a)\b|[?.,!]", " ", module_only).strip()
    explicit_navigation = bool(re.search(r"\b(?:show|demo|tour|walkthrough|dikhao)\b|दिखाओ", text))
    if explicit_navigation and request and not field_question and not module_only:
        matches = [key for key, pattern in MODULE_ALIASES.items() if re.search(pattern, text)]
        if len(matches) == 1:
            return GuideIntent("module", matches[0])
    return None


def requested_live_demo(message: str) -> bool:
    """A text-only model answer must not masquerade as a started demo."""
    text = normalize(message)
    return not re.search(NEGATION, text) and bool(re.search(r"\b(?:demo|tour|walkthrough|dikhao)\b|दिखाओ", text))
