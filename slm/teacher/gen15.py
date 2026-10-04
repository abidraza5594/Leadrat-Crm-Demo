"""Batch 15: seniority, purchase influence and next step in English (brokerage, developer, channel partner).
Compositional generator: each family fixes org type, seniority, influence, next step and target route;
variations draw company, city, numbers and phrasing. Every visitor line is checked unique against all raw batches."""
import json, random, glob
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = RAW / "batch_15.jsonl"
R = random.Random(1515)
SEEN = set()
for f in glob.glob(str(RAW / "batch_*.jsonl")):
    if f.endswith("batch_15.jsonl"): continue
    for line in open(f, encoding="utf-8"):
        if line.strip():
            for t in json.loads(line)["transcript"]:
                if t["speaker"] == "visitor": SEEN.add(t["text"].strip().lower())


def uniq(make):
    for _ in range(500):
        s = make()
        if s.strip().lower() not in SEEN:
            SEEN.add(s.strip().lower()); return s
    raise RuntimeError("could not make a unique line: " + s)


OPENERS = [
 "Hi, I'm Beacon, Leadrat's demo guide. What does your business do?",
 "Hello! Beacon here. Tell me a little about your company and I'll tailor the tour.",
 "Welcome to Leadrat. I'm Beacon. Who am I chatting with today?",
 "Hey there, Beacon from Leadrat. What brings you to the demo?",
 "Good to have you here. I'm Beacon. What kind of real estate work do you do?",
 "Hi! No forms, just a chat. I'm Beacon. What's your role and company?",
 "Hello, this is Beacon. I can show the CRM live. Where would you like to start?",
 "Beacon here, happy to help. Are you a broker, a developer or a channel partner?",
 "Hi, I'm Beacon. Before I open any screens, what does your team look like?",
 "Welcome! Beacon at your service. What would make this demo useful for you?",
 "Hey, I'm Beacon, the Leadrat assistant. What are you hoping to fix?",
 "Hello and welcome. I'm Beacon. Tell me about the company you're with.",
 "Hi there. Beacon here. Which part of your sales process do you want to see in Leadrat?",
 "Nice to meet you, I'm Beacon. What's your business about?",
 "Hi! I'm Beacon and I'll give you a quick live walkthrough. What do you do?",
 "Beacon from Leadrat here. Shall we start with who you are and what you sell?",
 "Hello! I'm Beacon. Resale, new launches, or channel sales? What's your world?",
 "Hi, welcome in. I'm Beacon. How can I help today?",
 "Hey! Beacon here, Leadrat's live demo. Tell me about your setup.",
 "Good day. I'm Beacon. What should I know about your business before we begin?",
 "Hi, Beacon speaking. Want the tour, or do you have a specific question first?",
 "Hello there, I'm Beacon. What's the company and what's your part in it?",
 "Welcome to the Leadrat demo. I'm Beacon. What are you working on these days?",
 "Hi! Beacon here. Quick question to start: what kind of properties do you deal in?",
 "Hey, thanks for stopping by. I'm Beacon. What's going on with your leads right now?",
 "Hello, I'm Beacon, and I'll keep this short. Who are you with?",
 "Hi, I'm Beacon. Tell me your business in a line and I'll show the relevant screens.",
 "Welcome! I'm Beacon from Leadrat. Which team are you from?",
 "Hi there, Beacon here. Where does your team sell, and what?",
 "Hello! Beacon, Leadrat's guide. What would you like Leadrat to do for you?"]
OUSE = {}


def opener():
    i = min(range(len(OPENERS)), key=lambda k: (OUSE.get(k, 0), R.random()))
    OUSE[i] = OUSE.get(i, 0) + 1
    return OPENERS[i]


IN_CITIES = ["Mumbai", "Pune", "Bengaluru", "Hyderabad", "Gurugram", "Noida", "Ahmedabad", "Chennai", "Kolkata", "Jaipur",
             "Thane", "Navi Mumbai", "Kochi", "Indore", "Lucknow", "Chandigarh", "Surat", "Nagpur", "Coimbatore", "Vadodara"]
AE_CITIES = ["Dubai", "Abu Dhabi", "Sharjah"]
PRE = ["Aster", "Crest", "Banyan", "Silverline", "Kesar", "Harbour", "Maple", "Orchid", "Saffron", "Tidewater", "Northstar",
       "Greenfield", "Skyrise", "Lotus", "Ivory", "Riverbend", "Monsoon", "Amber", "Coral", "Summit", "Velvet", "Zenith",
       "Peacock", "Sandstone", "Terrace", "Bluepine", "Goldleaf", "Horizon", "Cedar", "Evergreen", "Marigold", "Oasis"]
SUF = {"brokerage": ["Realty", "Properties", "Homes", "Estates", "Property Advisors", "Realtors"],
       "developer": ["Developers", "Infra", "Buildcon", "Constructions", "Landmark Projects", "Habitats"],
       "channel_partner": ["Channel Partners", "Property Consultants", "Realty Partners", "Sales Associates", "Advisory"]}
DESC = {"brokerage": ["a resale and rentals brokerage", "a brokerage focused on secondary sales", "a mid-size brokerage",
                      "a property brokerage doing resale and leasing", "a residential brokerage"],
        "developer": ["a residential developer", "a real estate developer with two live projects", "a builder doing mid-segment apartments",
                      "a developer with a new launch coming up", "a township developer"],
        "channel_partner": ["a channel partner firm selling for developers", "a CP agency tied up with several builders",
                            "a channel partner outfit handling new launches", "a mandate and channel sales firm",
                            "a channel partner network"]}
ROLES = {"owner": ["founder", "co-founder", "owner", "managing partner", "proprietor", "founding partner"],
         "executive": ["CEO", "VP of sales", "sales director", "COO", "director of marketing", "chief revenue officer", "VP operations"],
         "manager": ["sales manager", "branch manager", "team lead", "CRM manager", "operations manager", "presales manager"],
         "individual_contributor": ["sales executive", "relationship executive", "telecaller", "property consultant",
                                    "marketing associate", "presales executive"]}
BOSS = ["MD", "boss", "director", "CEO", "founder", "managing partner", "chairman", "business head"]
SOURCES = ["99acres", "MagicBricks", "Housing.com", "Facebook ads", "Google ads", "walk-ins", "referrals",
           "Instagram", "website forms", "NoBroker", "site visits"]
UAE_SOURCES = ["Bayut", "Property Finder", "Dubizzle", "Instagram", "referrals"]

INF = {
 "approver": ["I sign off on anything we buy", "it's my call, nobody else signs", "I own the budget for tools like this",
   "I approve all software spend at {co}", "the purchase decision is mine", "if I like it, we buy it, simple as that",
   "I hold the budget and I make the final call", "any contract at {co} goes through me and only me",
   "I can sign today if the pricing works", "budget sits with me, no committee", "I decide, I don't need anyone's approval",
   "the cheque book is mine, so yes I decide", "spend approvals for sales tools are in my hands"],
 "sponsored_evaluator": ["I'm shortlisting options for my {boss}", "my {boss} asked me to evaluate a few CRMs",
   "I recommend, the {boss} decides", "I'll put together a comparison and my {boss} picks", "the {boss} wants my recommendation by the next review",
   "I'm doing the legwork, final approval is with our {boss}", "I shortlist, the {boss} signs", "my {boss} has tasked me with finding a CRM",
   "I evaluate and present, but the {boss} holds the budget", "our {boss} will decide based on what I report back",
   "I'm the one testing tools, the {boss} makes the purchase", "I've been asked by the {boss} to look at three vendors"],
 "none": ["honestly I have no say in purchases", "I just use whatever they give us", "tools get picked by head office, not me",
   "I don't get involved in buying software", "whatever management chooses, I work with", "purchasing isn't something I'm part of",
   "I'm only here out of curiosity, I don't decide anything", "they never ask us before buying tools",
   "that decision is way above my pay grade", "someone else picks the software, I just log in"],
 "pilot": ["my {boss} signs the full rollout, but I can approve a pilot on my own budget",
   "I'm evaluating for the {boss}, though a small pilot I can sign myself", "the big decision is the {boss}'s, a pilot for my team I can approve",
   "I have my own budget for a trial, the company-wide deal needs the {boss}"],
 "delegate": ["I've handed software decisions to my ops head, I won't be involved", "my son runs the tech side now, I stay out of tool purchases",
   "I leave these decisions entirely to my COO, not my area anymore", "I've delegated this completely to our operations team, I don't sign these"],
}
NEXT = {
 "within_30_days": ["let's talk again this week", "can someone call me tomorrow", "I want this sorted before month end",
   "let's do a proper session in two weeks", "we want to go live within the month", "follow up with me next week",
   "call me on Monday, I'll be free", "I'd like a pricing call in the next few days", "we're aiming to decide in about ten days",
   "set up something for this Friday", "we need a system before our launch in three weeks", "reach out in a week or so"],
 "later": ["let's revisit next quarter", "we'll look at it after Diwali", "maybe in a couple of months", "after our financial year closes",
   "not before the new year", "we'll pick this up after the monsoon", "probably in Q3, not now", "once our current launch wraps up, a few months out",
   "check back in around three months", "after Ramadan would suit us better", "once budgets reopen in April"],
 "declined": ["please don't contact me", "no follow-up please", "I don't want sales calling me", "don't put me on any list",
   "I'm not interested in a follow-up", "please no calls or emails", "I'll reach out myself if needed, don't chase me"],
}
TAIL = ["", "", " honestly", ", to be clear", ", that's how it works here", " for now", ", just so you know", ", fyi", " in our setup", " at the moment"]
PAINS = [("leads fall through the cracks after the first call", "leads dropped after first call"),
         ("we get duplicate leads from multiple portals", "duplicate leads across portals"),
         ("there's no visibility into what each agent is doing", "no visibility into agent activity"),
         ("site visits don't get followed up", "site visits not followed up"),
         ("new enquiries get a slow response", "slow response to enquiries"),
         ("we can't tell which source actually converts", "no source-wise conversion tracking"),
         ("reports take a whole day to compile", "manual reporting takes a day"),
         ("agents leave and take their leads with them", "leads lost when agents leave"),
         ("callbacks get missed every single week", "missed callbacks"),
         ("partner leads get disputed", "lead ownership disputes")]
MANUAL = [("Excel and WhatsApp", ["Excel", "WhatsApp"]), ("Google Sheets", ["Google Sheets"]),
          ("a paper register and WhatsApp", ["paper register", "WhatsApp"]), ("spreadsheets mostly", ["spreadsheets"])]
CRMS = ["Zoho CRM", "Salesforce", "HubSpot", "LeadSquared", "Sell.Do", "a homegrown CRM"]


def seg_intro(L):
    co, city, org, role = L["name"], L["city"], L["type"], L["role"]

    def mk():
        d = R.choice(DESC[org])
        if role:
            t = R.choice(["I'm the {r} at {co}, {d} in {c}", "{R} here, {co}. We're {d} based in {c}",
                          "hi, {r} of {co} in {c}. we're {d}", "I work as {r} with {co}, {d} out of {c}",
                          "this is the {r} from {co}. {d}, {c} market"])
        else:
            t = R.choice(["we're {co}, {d} in {c}", "just checking this out for {co}, {d} in {c}", "{co} here, {d} operating in {c}",
                          "hey, we are {d} called {co}, based in {c}"])
        s = t.format(r=role, R=(role or "")[:1].upper() + (role or "")[1:], co=co, d=d, c=city)
        return s[:1].upper() + s[1:] if R.random() < 0.6 else s
    ev = ["organisation.type", "organisation.name", "geography"] + (["role", "seniority"] if role else [])
    return [(uniq(mk), ev)]


def seg_size(L):
    def mk():
        s = " and ".join(L["src"])
        return R.choice(["{a} agents, roughly {l} leads a month from {s}", "we have {a} people selling and about {l} enquiries monthly, mostly {s}",
                         "team of {a}. leads are around {l} a month, {s} mainly", "{a} on the sales floor, maybe {l} leads monthly via {s}",
                         "about {l} leads a month from {s}, handled by {a} agents"]).format(a=L["agents"], l=L["leads"], s=s)
    return [R.choice(["How big is the sales team, and how many leads a month?", "Team size and monthly lead volume?",
                      "How many agents do you have, and roughly how many enquiries?", "Where do leads come from, and how many?"]),
            (uniq(mk), ["organisation.agents", "monthly_leads", "lead_sources"])]


def seg_tools(L):
    def mk():
        p = " and ".join(x[0] for x in L["pains"])
        if L["proc"] == "manual":
            return R.choice(["we run everything on {t}. biggest issues: {p}", "all on {t} right now, and {p}",
                             "{t}, nothing fancy. the problem is {p}", "it's {t} for us, and {p}"]).format(t=L["tooltxt"], p=p) + R.choice(TAIL)
        if L["proc"] == "unsatisfied_crm":
            return R.choice(["we have {t} but it's not working for us, {p}", "we pay for {t}, still {p}",
                             "{t} is what we use, and yet {p}"]).format(t=L["tools"][0], p=p) + R.choice(TAIL)
        return R.choice(["we use {t} and honestly it works fine, no real problems", "{t} does the job for us, nothing is broken",
                         "we're happy on {t}, no complaints really", "{t} covers everything, we have no issues"]).format(t=L["tools"][0]) + R.choice(TAIL)
    return [R.choice(["What do you use today, and what hurts most?", "How do you track leads right now?",
                      "Which tools are you on, and where does it break?", "Here's the Leads list. How does this compare to your current setup?"]),
            (uniq(mk), ["current_tooling", "process", "pain_points"])]


def seg_inf(L):
    if L["inf_kind"] == "unknown":
        return [R.choice(["Here's the Pipeline board by stage.", "This is the Site Visits calendar.", "Here is the Reports screen."]),
                (uniq(lambda: R.choice(["does it integrate with {s}?", "can I export this to Excel for {co}?", "how does the mobile app look for {co}?",
                                        "is the data hosted in {c}?", "can agents at {co} see each other's leads?"]).format(
                    s=L["src"][0], co=L["name"], c="India" if not L["uae"] else "the UAE") + R.choice(["", " just curious", " asking for the team"])), [])]
    line = uniq(lambda: (lambda s: s[:1].upper() + s[1:])(R.choice(INF[L["inf_kind"]]).format(boss=R.choice(BOSS), co=L["name"]) + R.choice(TAIL))
                + R.choice(["", ".", " btw."]))
    return [R.choice(["Who decides on a tool like this?", "Who signs off on software purchases?", "Are you the decision maker here?",
                      "Who else would be involved in choosing a CRM?"]), (line, ["influence"])]


def seg_next(L):
    if L["nxt"] == "unknown":
        return []
    q = R.choice(["What would a sensible next step be?", "When would you want to pick this up?", "What's your timeline?",
                  "When are you hoping to have something in place?"])
    if L["corrected"]:
        first = uniq(lambda: R.choice(NEXT["later"]) + R.choice(TAIL) + R.choice(["", " I think", ", probably"]))
        second = uniq(lambda: R.choice(["actually scratch that, {x}", "wait, my {b} just messaged, {x}", "correction: {x}, things moved up",
                                        "no sorry, {x} after all"]).format(x=R.choice(NEXT["within_30_days"]), b=R.choice(BOSS)))
        return [q, (first, []), R.choice(["Noted.", "Okay, got it.", "Sure."]), (second, ["next_step"])]
    line = uniq(lambda: R.choice(NEXT[L["nxt"]]) + R.choice(TAIL) + R.choice(["", ".", " please", ", thanks"]))
    return [q, (line, ["next_step"])]


def seg_consent(L):
    if L["nxt"] == "declined": return []
    q = R.choice(["Would you like our sales team to get in touch?", "Shall I have sales follow up with you?", "Okay if our team contacts you?"])
    if L["consent"]:
        c = L["contact"]
        bits = ", ".join(x for x in [c["name"], c["email"], c["phone"]] if x)
        return [q, (uniq(lambda: R.choice(["yes please, {b}", "sure, reach me at {b}", "go ahead, {b}", "yes, contact me: {b}"]).format(b=bits)),
                    ["consent", "contact"])]
    line = uniq(lambda: R.choice(["not yet, I'll get back to you", "no thanks, I'll reach out when ready", "hold off for now",
                                  "not at this point", "I'd rather not share details yet"]) + R.choice(TAIL) + R.choice(["", " for {co}".format(co=L["name"]), "."]))
    return [q, (line, [])]


FAMS = []
H, N, G, HR = "handoff", "nurture", "graceful", "review"
for org in ["brokerage", "developer", "channel_partner"]:
    FAMS += [(org, "owner_signs_now", "owner", "approver", "within_30_days", H, {}),
             (org, "exec_budget_owner", "executive", "approver", "within_30_days", H, {}),
             (org, "manager_evaluates_for_md", "manager", "sponsored_evaluator", "within_30_days", H, {}),
             (org, "pilot_budget_evaluator", "manager", "pilot", "within_30_days", H, {}),
             (org, "timeline_moved_up", "executive", "sponsored_evaluator", "within_30_days", H, {"corrected": True}),
             (org, "evaluator_next_quarter", "executive", "sponsored_evaluator", "later", N, {}),
             (org, "owner_after_festival", "owner", "approver", "later", N, {}),
             (org, "user_no_say", "individual_contributor", "none", "within_30_days", N, {"noconsent": True}),
             (org, "owner_delegates", "owner", "delegate", "later", N, {}),
             (org, "declines_followup", "manager", "approver", "declined", G, {}),
             (org, "happy_crm_user", "individual_contributor", "none", "later", G, {"happy": True}),
             (org, "role_no_authority", "executive", "unknown", "within_30_days", HR, {}),
             (org, "anonymous_browser", "unknown", "unknown", "unknown", HR, {}),
             (org, "ic_shortlisting", "individual_contributor", "sponsored_evaluator", "later", N, {}),
             (org, "partner_no_timeline", "owner", "approver", "unknown", HR, {})]
# interleave so the 6-variation families spread across org types
FAMS = [FAMS[i + 15 * j] for i in range(15) for j in range(3)]


def build(org, sen, ik, nxt, route, extra):
    uae = org == "brokerage" and R.random() < 0.3
    if route == H or (route in (N, HR) and R.random() < 0.5):
        agents, leads, np_ = R.randint(20, 90), R.choice(range(500, 4000, 50)), 2
    elif extra.get("happy"):
        agents, leads, np_ = R.randint(2, 5), R.randint(20, 90), 0
    else:
        agents, leads, np_ = R.randint(6, 19), R.choice(range(100, 450, 10)), R.choice([1, 2])
    if extra.get("happy"): proc, tools, tooltxt = "satisfied_crm", [R.choice(CRMS[:5])], None
    elif R.random() < 0.6: proc = "manual"; tooltxt, tools = R.choice(MANUAL)
    else: proc, tools, tooltxt = "unsatisfied_crm", [R.choice(CRMS)], None
    consent = not extra.get("noconsent") and nxt != "declined" and (route == H or R.random() < 0.45)
    first = R.choice(["Riya", "Arjun", "Sana", "Kabir", "Neha", "Vikram", "Farah", "Rohan", "Isha", "Imran", "Priya", "Dev", "Aisha", "Karan", "Meera"])
    k = R.random()
    contact = {"name": first if k < 0.5 else None, "email": f"{first.lower()}.{R.randint(10, 99)}@example.com" if k < 0.7 else None,
               "phone": (f"+971 50 000 5{R.randint(0, 999):03d}" if uae else f"+91 90000 5{R.randint(0, 9999):04d}") if k >= 0.4 else None}
    return dict(name=f"{R.choice(PRE)} {R.choice(SUF[org])}", city=R.choice(AE_CITIES if uae else IN_CITIES), type=org,
                role=None if sen == "unknown" else R.choice(ROLES[sen]), sen=sen, agents=agents, leads=leads,
                src=R.sample(UAE_SOURCES if uae else SOURCES, 2), proc=proc, tools=tools, tooltxt=tooltxt,
                pains=R.sample(PAINS, np_), inf_kind=ik, inf={"pilot": "approver", "delegate": "none"}.get(ik, ik),
                nxt=nxt, consent=consent, contact=contact, uae=uae, corrected=extra.get("corrected"))


def assemble(L, partial):
    segs = [seg_intro(L), seg_size(L), seg_tools(L)]
    if partial: segs = segs + [seg_inf(L)] if R.random() < 0.5 else segs[:R.choice([2, 3])]
    else: segs += [s for s in (seg_inf(L), seg_next(L), seg_consent(L)) if s]
    turns, ev = [{"turn_id": 1, "speaker": "beacon", "text": opener()}], {}
    for s in segs:
        for it in s:
            if isinstance(it, str):
                turns.append({"turn_id": len(turns) + 1, "speaker": "beacon", "text": it})
            else:
                turns.append({"turn_id": len(turns) + 1, "speaker": "visitor", "text": it[0]})
                for f in it[1]: ev.setdefault(f, []).append(len(turns))
    if partial and R.random() < 0.3:
        turns.append({"turn_id": len(turns) + 1, "speaker": "beacon", "text": R.choice(["Let me pull up the Leads screen.", "One sec while I load the demo."])})
    has = ev.__contains__
    lab = {"role": L["role"] if has("role") else None, "seniority": L["sen"] if has("seniority") else "unknown",
           "organisation": {"name": L["name"], "type": L["type"], "agents": L["agents"] if has("organisation.agents") else None},
           "pain_points": [p[1] for p in L["pains"]] if has("pain_points") else None,
           "current_tooling": L["tools"] if has("current_tooling") else None, "process": L["proc"] if has("process") else "unknown",
           "geography": {"countries": ["UAE" if L["uae"] else "India"], "cities": [L["city"]]},
           "monthly_leads": {"min": L["leads"], "max": L["leads"]} if has("monthly_leads") else {"min": None, "max": None},
           "lead_sources": list(L["src"]) if has("lead_sources") else None,
           "influence": L["inf"] if has("influence") else "unknown", "next_step": L["nxt"] if has("next_step") else "unknown",
           "consent": bool(L["consent"] and has("consent")),
           "contact": L["contact"] if has("contact") else {"name": None, "email": None, "phone": None}, "evidence": ev}
    return turns, lab


def main():
    rows = []
    for fi, (org, scen, sen, ik, nxt, route, extra) in enumerate(FAMS):
        for v in range(6 if fi < 25 else 5):
            partial = v in (1, 4)
            turns, lab = assemble(build(org, sen, ik, nxt, route, extra), partial)
            rows.append({"id": f"b15-{len(rows) + 1:03d}", "family": f"{org}/b15_{scen}", "language": "en",
                         "partial": partial, "transcript": turns, "label": lab})
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(len(rows), "rows ->", OUT)


if __name__ == "__main__":
    main()
