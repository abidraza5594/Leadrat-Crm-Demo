"""Permission-aware, result-driven teaching plans; no arbitrary clicks or writes."""

from dataclasses import dataclass, field

from .catalog import CONTROLS, FIELDS, MODULES
from .schemas import AppContext
from .feature_guides import FEATURES


@dataclass(frozen=True)
class Step:
    name: str
    arguments: dict[str, str]
    key: str
    label: str


@dataclass
class Tour:
    kind: str
    queue: list[Step] = field(default_factory=list)
    completed: int = 0


def module_step(key: str) -> Step:
    return Step("open_module", {"module": key}, f"module.{key}", MODULES[key][0])


def create_tour(kind: str, context: AppContext, module: str | None = None) -> Tour:
    queue = []
    if kind in ("crm", "module"):
        if context.mode != "crm" or "open_module" not in context.available_actions:
            raise ValueError("Open the actual CRM with your account to start a CRM tour.")
        modules = [key for key in MODULES if key in context.available_modules]
        if kind == "module":
            if module not in modules:
                raise ValueError("This module is unavailable for your account.")
            modules = [module]
        queue.extend(module_step(key) for key in modules)
    elif "open_add_lead_form" not in context.available_actions:
        raise ValueError("Your account does not have permission to open Add Lead.")
    if kind in ("crm", "lead") and "open_add_lead_form" in context.available_actions:
        queue.append(Step("open_add_lead_form", {}, "lead.open", "Add Lead form"))
    if not queue:
        raise ValueError("No supported tutorial screens are available with your current permissions.")
    return Tour(kind=kind, queue=queue)


def advance(tour: Tour, context: AppContext) -> None:
    """Called ONLY after a matching successful result for the current step."""
    step = tour.queue.pop(0)
    tour.completed += 1
    if tour.kind == "feature":
        return
    extra = []
    if step.name in ("open_module", "open_leads_page"):
        module = step.arguments.get("module", "leads")
        if "highlight_module_control" in context.available_actions:
            extra = [Step("highlight_module_control", {"control": key}, f"control.{key}", label)
                     for key, (label, _) in CONTROLS.items()
                     if key.startswith(module + ".") and key in context.available_controls]
    elif step.name == "open_add_lead_form":
        if context.form_ready and "highlight_field" in context.available_actions:
            extra = [Step("highlight_field", {"field": key}, f"field.{key}", label)
                     for key, (label, _) in FIELDS.items() if key in context.available_fields]
        if "fill_demo_lead" in context.available_actions:
            extra.append(Step("fill_demo_lead", {}, "lead.sample", "Sample name and email"))
        if not extra:
            raise ValueError("The form opened, but no supported fields are ready. Open the form section and retry.")
    tour.queue[0:0] = extra


def create_feature_tour(feature: str, context: AppContext) -> Tour:
    if feature not in FEATURES or context.mode != "crm" or "show_lead_feature" not in context.available_actions:
        raise ValueError("This live feature guide is unavailable. Reload the updated CRM and check Leads access.")
    queue = []
    if context.route.split('?')[0] != '/leads/manage-leads':
        if 'open_module' not in context.available_actions or 'leads' not in context.available_modules:
            raise ValueError("Leads navigation is unavailable for this account.")
        queue.append(module_step('leads'))
    queue.extend(Step('show_lead_feature', {'feature': feature, 'stage': stage},
                      f'feature.{feature}.{stage}', FEATURES[feature][0])
                 for stage in ('open', 'details', 'finish'))
    return Tour(kind='feature', queue=queue)
