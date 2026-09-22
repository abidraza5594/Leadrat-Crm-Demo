"""Model intent tools and strictly allowlisted browser actions."""

from typing import Any

from .catalog import CONTROLS, FIELDS, MODULES

DESCRIPTIONS = {
    "start_crm_tour": "Start the full available CRM guided tour, visiting modules, highlighting controls and finally explaining Add Lead fields. Use for complete CRM demo, pura CRM samjhao, full tour. The workflow engine handles ALL remaining steps after this call.",
    "start_lead_tour": "Start a complete step-by-step Add Lead form walkthrough: open form, explain every visible supported field and fill sample name/email at the end. Use for how to add a lead / lead demo. The workflow engine handles the remaining steps.",
    "start_module_tour": "Start a guided explanation of one available module, opening its actual screen and highlighting supported visible controls. Use when asked how to use Dashboard, Reports, Tasks or another specific module.",
    "open_module": "Open one available CRM module without editing records. Only for requests to simply open a screen; for explanations use start_module_tour.",
    "highlight_module_control": "Highlight one existing visible, allowlisted screen control. Does not click or change data.",
    "open_leads_page": "Open the CRM Leads list. Use this first for a create-lead live demonstration, unless already on the leads list or add form. No records are changed.",
    "open_add_lead_form": "Open the actual Add Lead form. Wait for its result before highlighting or filling. Never use to edit an existing lead.",
    "highlight_field": "Highlight one available form field. For a full lead walkthrough use start_lead_tour instead. Requires the add form to be ready.",
    "fill_demo_lead": "Fill ONLY empty name and email controls with fixed sample values Demo Customer and demo@example.com. The app decides sample values. Does NOT save or create a lead. Call once during an add-lead demonstration after opening the form and highlighting a field.",
}

PENDING_TEXT = {
    "show_lead_feature": "Actual lead ka feature kholkar dikha raha hoon…",
    "open_module": "CRM screen khol raha hoon…",
    "highlight_module_control": "Screen ka control highlight kar raha hoon…",
    "open_leads_page": "Leads screen khol raha hoon…",
    "open_add_lead_form": "Add Lead form khol raha hoon…",
    "highlight_field": "Form ka field highlight kar raha hoon…",
    "fill_demo_lead": "Khali name aur email fields mein sample details bhar raha hoon…",
}


def tool_definitions(available: list[str]) -> list[dict[str, Any]]:
    tools = []
    for name, description in DESCRIPTIONS.items():
        if name not in available:
            continue
        properties = {}
        required = []
        if name == "highlight_field":
            properties = {"field": {"type": "string", "enum": list(FIELDS)}}
            required = ["field"]
        elif name in ("open_module", "start_module_tour"):
            properties = {"module": {"type": "string", "enum": list(MODULES)}}
            required = ["module"]
        elif name == "highlight_module_control":
            properties = {"control": {"type": "string", "enum": list(CONTROLS)}}
            required = ["control"]
        tools.append({"type": "function", "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": required, "additionalProperties": False},
        }})
    return tools


def validate_arguments(name: str, arguments: Any) -> dict[str, str]:
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")
    if name not in DESCRIPTIONS:
        raise ValueError("The model requested an unsupported action.")
    if name == "highlight_field":
        if set(arguments) != {"field"} or not isinstance(arguments["field"], str) or arguments["field"] not in FIELDS:
            raise ValueError("The model requested an unsupported field.")
    elif name in ("open_module", "start_module_tour"):
        if set(arguments) != {"module"} or not isinstance(arguments["module"], str) or arguments["module"] not in MODULES:
            raise ValueError("The model requested an unsupported module.")
    elif name == "highlight_module_control":
        if set(arguments) != {"control"} or not isinstance(arguments["control"], str) or arguments["control"] not in CONTROLS:
            raise ValueError("The model requested an unsupported control.")
    elif arguments:
        raise ValueError("This action does not accept arguments.")
    return arguments
