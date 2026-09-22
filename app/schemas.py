from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ActionName = Literal[
    "open_leads_page", "open_add_lead_form", "highlight_field", "fill_demo_lead",
    "open_module", "highlight_module_control", "show_lead_feature"
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppContext(StrictModel):
    route: str = Field(max_length=200)
    available_actions: list[ActionName] = Field(default_factory=list, max_length=7)
    available_modules: list[str] = Field(default_factory=list, max_length=20)
    available_fields: list[str] = Field(default_factory=list, max_length=32)
    available_controls: list[str] = Field(default_factory=list, max_length=20)
    mode: Literal["crm", "sandbox"]
    form_ready: bool = False


class ActionResult(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    name: ActionName
    ok: bool
    detail: str = Field(max_length=500)


class TurnRequest(StrictModel):
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    context: AppContext
    results: list[ActionResult] = Field(default_factory=list, max_length=1)

    @model_validator(mode="after")
    def require_input(self):
        if bool(self.message and self.message.strip()) == bool(self.results):
            raise ValueError("Send either a non-empty message or one action result.")
        return self


class Action(StrictModel):
    id: str
    name: ActionName
    arguments: dict[str, str]


class Narration(StrictModel):
    key: str
    text: str
    language: Literal["hi", "en"] = "hi"


class Progress(StrictModel):
    current: int
    total: int
    label: str


class SpeechRequest(StrictModel):
    key: str = Field(min_length=1, max_length=100)
    voice: Literal["hi-IN-SwaraNeural", "hi-IN-MadhurNeural", "en-IN-NeerjaNeural", "en-IN-PrabhatNeural"] = "hi-IN-SwaraNeural"
    language: Literal["hi", "en"] | None = None

    @model_validator(mode="after")
    def voice_matches_language(self):
        if self.language and not self.voice.startswith(self.language + "-"):
            raise ValueError("The voice must match the narration language.")
        return self


class TurnResponse(StrictModel):
    message: str
    actions: list[Action]
    model: str
    done: bool
    language: Literal["hi", "en"] = "hi"
    narration: Narration | None = None
    progress: Progress | None = None
