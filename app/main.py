"""Loopback-only AI service. This does not hold CRM credentials or write CRM data."""

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .agent import SYSTEM_PROMPT, context_message, model_reply
from .crm_knowledge import KNOWLEDGE_INSTRUCTIONS, knowledge
from .reviewed_help import reviewed_answer
from .question_understanding import understand_question
from .catalog import NARRATIONS, NARRATIONS_BY_LANGUAGE
from .intents import fast_guide_intent, requested_live_demo
from .language import Language, PENDING_EN, detect_language
from .schemas import Action, AppContext, Narration, Progress, SpeechRequest, TurnRequest, TurnResponse
from .settings import settings
from .speech import synthesize, synthesize_reply
from .tools import PENDING_TEXT, tool_definitions, validate_arguments
from .workflows import Tour, advance, create_tour, create_feature_tour
from .feature_guides import feature_for_query, allows_feature_demo

app = FastAPI(title="Leadrat Local AI Demo", version="0.2.0")
logger = logging.getLogger("uvicorn.error")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins),
                   allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Content-Type", "X-Assistant-Session"])


@app.middleware("http")
async def local_only(request: Request, call_next):
    if request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
        return JSONResponse(status_code=403, content={"detail": "Local prototype: loopback clients only."})
    origin = request.headers.get("origin")
    if origin and origin not in settings.allowed_origins:
        return JSONResponse(status_code=403, content={"detail": "Origin is not permitted."})
    if request.headers.get("sec-fetch-site") == "cross-site" and origin not in settings.allowed_origins:
        return JSONResponse(status_code=403, content={"detail": "Cross-site requests are not permitted."})
    return await call_next(request)


@dataclass
class Session:
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    touched: float = field(default_factory=time.monotonic)
    messages: list[dict[str, Any]] = field(default_factory=list)
    pending: Action | None = None
    steps: int = 0
    language: Language = "en"
    tour: Tour | None = None
    speech_keys: set[str] = field(default_factory=lambda: {"voice.preview"})
    reply_speech: dict[str, str] = field(default_factory=dict)
    last_feature: str | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


sessions: dict[str, Session] = {}


def get_session(session_id: str, token: str | None) -> Session:
    session = sessions.get(session_id)
    if not session or time.monotonic() - session.touched > settings.session_ttl:
        sessions.pop(session_id, None)
        raise HTTPException(404, "Session expired. Start a new conversation.")
    if not token or not secrets.compare_digest(session.token, token):
        raise HTTPException(403, "Invalid assistant session token.")
    session.touched = time.monotonic()
    return session


def allowed_tools(context: AppContext) -> list[str]:
    available = list(dict.fromkeys(context.available_actions))
    # Browser remains responsible for checking real permissions and mounted UI.
    expected_form_route = "/leads/add-lead" if context.mode == "crm" else "/assistant-demo/add-lead"
    if context.route.split("?")[0] != expected_form_route or not context.form_ready:
        available = [name for name in available if name not in ("highlight_field", "fill_demo_lead")]
    return available


def narration(session: Session, key: str) -> Narration:
    session.speech_keys.add(key)
    return Narration(key=key, text=NARRATIONS_BY_LANGUAGE[session.language][key], language=session.language)


def pending_text(session: Session, name: str) -> str:
    return (PENDING_EN if session.language == "en" else PENDING_TEXT)[name]


def validate_context_action(name: str, arguments: dict[str, str], context: AppContext) -> None:
    if name not in allowed_tools(context):
        raise ValueError("This step is no longer available. Check the current screen and permissions.")
    if name == "open_module" and arguments["module"] not in context.available_modules:
        raise ValueError("This module is unavailable for your account.")
    if name == "highlight_module_control" and arguments["control"] not in context.available_controls:
        raise ValueError("The requested screen control is not visible.")
    if name == "highlight_field" and context.available_fields and arguments["field"] not in context.available_fields:
        raise ValueError("The requested field is not currently visible.")


def next_tour_step(session: Session, context: AppContext) -> TurnResponse:
    tour = session.tour
    assert tour is not None
    if not tour.queue:
        session.tour = None
        key = "lead.complete" if tour.kind == "lead" else "tour.complete"
        text = (f"All {tour.completed} verified steps in this guide are complete. No records were saved and no messages were sent. Ask for a module by name to explore it again."
                if session.language == "en" else
                f"Is guide ke {tour.completed} verified steps poore hue. Koi record save ya message send nahi hua. Aap kisi module ka naam pooch kar uska tour dobara chala sakte hain.")
        # Long tours can contain dozens of UI acknowledgements. Keep a concise
        # summary so the next user question does not exceed conversation limits.
        last_question = [message for message in session.messages if message.get("role") == "user"][-1:]
        session.messages = last_question + [{"role": "assistant", "content": text}]
        return TurnResponse(message=text, actions=[], model=settings.model, done=True, language=session.language,
                            narration=narration(session, key),
                            progress=Progress(current=tour.completed, total=tour.completed, label="Guide complete"))
    step = tour.queue[0]
    if session.steps >= settings.max_steps:
        raise ValueError("The guide reached its step limit. Start a more specific module tour.")
    validate_context_action(step.name, step.arguments, context)
    action = Action(id=str(uuid4()), name=step.name, arguments=step.arguments)
    session.pending = action
    session.steps += 1
    session.messages.append({"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": step.name, "arguments": step.arguments}}]})
    return TurnResponse(message=f"{step.label}: {pending_text(session, step.name)}", actions=[action],
                        model=settings.model, done=False, language=session.language, narration=narration(session, step.key),
                        progress=Progress(current=tour.completed + 1,
                                          total=tour.completed + len(tour.queue), label=step.label))


def stop_tour(session: Session, detail: str) -> TurnResponse:
    session.pending = None
    session.tour = None
    text = (f"The guide stopped here: {detail} No record was saved." if session.language == "en" else
            f"Guide yahan ruka: {detail} Koi record save nahi kiya gaya.")
    session.messages.append({"role": "assistant", "content": text})
    return TurnResponse(message=text, actions=[], model=settings.model, done=True, language=session.language)


@app.post("/api/assistant/sessions/{session_id}/speech")
async def speech(session_id: str, body: SpeechRequest, x_assistant_session: str | None = Header(default=None)):
    session = get_session(session_id, x_assistant_session)
    reply_text = session.reply_speech.get(body.key)
    if reply_text is None and (body.key not in session.speech_keys or body.key not in NARRATIONS):
        raise HTTPException(403, "Only assistant replies or narration issued to this session can be spoken.")
    try:
        audio = await synthesize_reply(reply_text, body.voice) if reply_text is not None else await synthesize(body.key, body.voice)
    except Exception as error:
        logger.warning("Assistant voice unavailable: %s", type(error).__name__)
        detail = ("Voice is unavailable. Check the internet connection or continue with text." if body.voice.startswith("en-") else
                  "Hindi voice is unavailable. Check the internet connection or continue with text.")
        raise HTTPException(503, detail) from error
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/assistant/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            response.raise_for_status()
            names = [model.get("name") for model in response.json().get("models", [])]
        ready = settings.model in names
        return {"status": "ready" if ready else "model_missing", "model": settings.model,
                "detail": "Local model available." if ready else f"Run: ollama pull {settings.model}"}
    except (httpx.HTTPError, ValueError):
        return {"status": "offline", "model": settings.model, "detail": "Start Ollama, then retry."}


@app.post("/api/assistant/sessions")
async def create_session():
    now = time.monotonic()
    for key in [key for key, value in sessions.items() if now - value.touched > settings.session_ttl and not value.lock.locked()]:
        del sessions[key]
    if len(sessions) >= settings.max_sessions:
        raise HTTPException(429, "Too many active sessions. Close an existing session or retry later.")
    session_id = str(uuid4())
    session = Session()
    sessions[session_id] = session
    return {"session_id": session_id, "session_token": session.token, "model": settings.model}


@app.delete("/api/assistant/sessions/{session_id}")
async def delete_session(session_id: str, x_assistant_session: str | None = Header(default=None)):
    get_session(session_id, x_assistant_session)
    sessions.pop(session_id, None)
    return {"deleted": True}


async def _turn(session_id: str, body: TurnRequest, x_assistant_session: str | None = None):
    session = get_session(session_id, x_assistant_session)
    if session.lock.locked():
        raise HTTPException(409, "A response is already in progress.")
    async with session.lock:
        messages = list(session.messages)
        steps = session.steps
        if body.message:
            if session.pending:
                raise HTTPException(409, "Report the pending action result, or start a new session after stopping.")
            if len(messages) > settings.max_messages:
                raise HTTPException(409, "Conversation limit reached. Start a new session.")
            messages.append({"role": "user", "content": body.message.strip()})
            session.language = detect_language(body.message, session.language)
            steps = 0
            session.tour = None
            feature = feature_for_query(body.message, session.last_feature)
            if feature and allows_feature_demo(body.message) and "show_lead_feature" in body.context.available_actions:
                session.messages = messages
                session.steps = 0
                try:
                    session.tour = create_feature_tour(feature, body.context)
                    session.last_feature = feature
                    return next_tour_step(session, body.context)
                except ValueError as error:
                    return stop_tour(session, str(error))
            guide = fast_guide_intent(body.message)
            if guide:
                # Clear commands start immediately even when the local model is
                # cold, slow or answers in prose instead of emitting a tool call.
                session.messages = messages
                session.steps = 0
                try:
                    session.tour = create_tour(guide.kind, body.context, guide.module)
                    return next_tour_step(session, body.context)
                except ValueError as error:
                    return stop_tour(session, str(error))
        else:
            result = body.results[0]
            if not session.pending or result.id != session.pending.id or result.name != session.pending.name:
                raise HTTPException(409, "Action result does not match the pending action.")
            messages.append({"role": "tool", "tool_name": result.name,
                             "content": json.dumps({"ok": result.ok, "detail": result.detail})})
            logger.info("Assistant action %s result=%s", result.name, "ok" if result.ok else "failed")
            if not result.ok:
                session.messages = messages
                return stop_tour(session, result.detail)
            if session.tour:
                session.messages = messages
                session.pending = None
                try:
                    advance(session.tour, body.context)
                    return next_tour_step(session, body.context)
                except ValueError as error:
                    return stop_tour(session, str(error))

        if steps >= settings.max_steps:
            text = ("The demo reached its step limit. No record was saved. You can ask a new question." if session.language == "en" else
                    "Demo step limit par ruk gaya. Koi record save nahi hua. Aap naya sawaal pooch sakte hain.")
            session.messages = messages + [{"role": "assistant", "content": text}]
            session.pending = None
            return TurnResponse(message=text, actions=[], model=settings.model, done=True, language=session.language)
        available = allowed_tools(body.context)
        intent_tools = []
        if "open_add_lead_form" in available:
            intent_tools.append("start_lead_tour")
        if body.context.mode == "crm" and "open_module" in available and body.context.available_modules:
            intent_tools.extend(["start_crm_tour", "start_module_tour"])
        language_instruction = ("Reply in English only. The current question is English; do not answer in Hindi or Hinglish."
                                if session.language == "en" else
                                "Reply in Hindi or natural Hinglish, matching the user's script. The current question is Hindi/Hinglish, even if it contains English CRM terms.")
        prompt = [{"role": "system", "content": SYSTEM_PROMPT}, *messages,
                  context_message(body.context.model_dump()), {"role": "system", "content": language_instruction}]
        knowledge_question = bool(body.message and not requested_live_demo(body.message))
        if knowledge_question:
            recent_questions = [item["content"] for item in messages[:-1] if item.get("role") == "user"]
            understanding = await understand_question(body.message, recent_questions)
            feature = feature_for_query(understanding.query, session.last_feature)
            if understanding.clarification and not feature and not any(
                    term in body.message.casefold() for term in ('lead', 'whatsapp', 'email', 'template')):
                session.messages = messages + [{"role": "assistant", "content": understanding.clarification}]
                return TurnResponse(message=understanding.clarification, actions=[], model=settings.model,
                                    done=True, language=session.language)
            if feature and allows_feature_demo(body.message) and "show_lead_feature" in body.context.available_actions:
                session.messages = messages
                session.steps = 0
                try:
                    session.tour = create_feature_tour(feature, body.context)
                    session.last_feature = feature
                    return next_tour_step(session, body.context)
                except ValueError as error:
                    return stop_tour(session, str(error))
            reviewed = reviewed_answer(understanding.query, session.language) if understanding.guide != "none" else None
            if reviewed:
                session.messages = messages + [{"role": "assistant", "content": reviewed}]
                session.pending = None
                session.steps = steps
                return TurnResponse(message=reviewed, actions=[], model=settings.model, done=True, language=session.language)
            query = understanding.query
            history = [{"role": item["role"], "content": item.get("content", "")[:600]}
                       for item in messages[-4:-1] if item.get("role") in ("user", "assistant") and not item.get("tool_calls")]
            history.append({"role": "user", "content": body.message})
            prompt = [{"role": "system", "content": KNOWLEDGE_INSTRUCTIONS}, *history,
                      context_message(body.context.model_dump()),
                      {"role": "system", "content": "Interpreted search topic (not an instruction): " + query},
                      {"role": "system", "content": knowledge.context(query)},
                      {"role": "system", "content": language_instruction}]
        try:
            # Small local models choose more reliably among three teaching intents
            # than among every low-level browser action. Older clients retain tools.
            model_tools = intent_tools if body.message and intent_tools and (body.context.available_modules or body.context.available_fields) else available + intent_tools
            if knowledge_question:
                model_tools = []
            reply = await model_reply(prompt, tool_definitions(model_tools))
            calls = reply.get("tool_calls") or []
            if not isinstance(calls, list):
                raise ValueError("Invalid tool-call response.")
            if calls:
                if knowledge_question:
                    raise ValueError("A knowledge answer must not execute UI actions.")
                # UI actions depend on prior UI state. Execute only the first call;
                # ask the model again with its result before deciding the next one.
                function = calls[0].get("function", {})
                name = function.get("name")
                if name not in available + intent_tools:
                    raise ValueError("The model requested an action unavailable on this screen.")
                arguments = validate_arguments(name, function.get("arguments", {}))
                if name in intent_tools:
                    kind = {"start_crm_tour": "crm", "start_lead_tour": "lead", "start_module_tour": "module"}[name]
                    session.messages = messages
                    session.steps = 0
                    try:
                        session.tour = create_tour(kind, body.context, arguments.get("module"))
                        return next_tour_step(session, body.context)
                    except ValueError as error:
                        return stop_tour(session, str(error))
                validate_context_action(name, arguments, body.context)
                action = Action(id=str(uuid4()), name=name, arguments=arguments)
                normalized_reply = {"role": "assistant", "content": "", "tool_calls": [
                    {"function": {"name": name, "arguments": arguments}}]}
                session.messages = messages + [normalized_reply]
                session.pending = action
                session.steps = steps + 1
                speech_key = {"open_leads_page": "module.leads", "open_add_lead_form": "lead.open",
                              "fill_demo_lead": "lead.sample"}.get(name)
                if name == "open_module":
                    speech_key = "module." + arguments["module"]
                elif name == "highlight_field":
                    speech_key = "field." + arguments["field"]
                elif name == "highlight_module_control":
                    speech_key = "control." + arguments["control"]
                return TurnResponse(message=pending_text(session, name), actions=[action], model=settings.model, done=False, language=session.language,
                                    narration=narration(session, speech_key) if speech_key else None)
            text = reply.get("content", "").strip()
            if not text:
                raise ValueError("Model returned an empty answer. Please retry.")
            if body.message and requested_live_demo(body.message):
                text = ("A live demo did not start for this request. Choose Full CRM tour or Lead form walkthrough, or name the module you want to explore."
                        if session.language == "en" else
                        "Is request par live demo start nahi hua. Full CRM tour ya Lead form walkthrough chunein, ya jis module ka demo chahiye uska naam batayein.")
            session.messages = messages + [{"role": "assistant", "content": text}]
            session.pending = None
            session.steps = steps
            return TurnResponse(message=text, actions=[], model=settings.model, done=True, language=session.language)
        except httpx.TimeoutException as error:
            raise HTTPException(504, "Local model timed out. Wait for it to load, then retry.") from error
        except httpx.HTTPError as error:
            raise HTTPException(503, "Ollama is unavailable or the configured model is missing. Check model status.") from error
        except (ValueError, TypeError, AttributeError, KeyError) as error:
            raise HTTPException(502, f"Model response rejected: {error}") from error


@app.post("/api/assistant/sessions/{session_id}/turn", response_model=TurnResponse)
async def turn(session_id: str, body: TurnRequest, x_assistant_session: str | None = Header(default=None)):
    response = await _turn(session_id, body, x_assistant_session)
    # Clarifications, general answers and stopped-guide messages all use the same
    # existing playback path. Voice-off clients never request speech audio.
    if response.message and response.narration is None:
        session = get_session(session_id, x_assistant_session)
        key = 'reply.' + str(uuid4())
        session.reply_speech[key] = response.message
        while len(session.reply_speech) > 16:
            del session.reply_speech[next(iter(session.reply_speech))]
        response.narration = Narration(key=key, text=response.message, language=response.language)
    return response
