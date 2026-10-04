"""Batch 16: consent, contact and declines in English. Discovery turns are assembled from varied
templates; each family fixes one closing pattern (explicit consent, non-consent, withdrawal, colleague
contact, declines of different strength, malformed contacts). Labels are built alongside the turns so
evidence always points at the visitor turn that stated the fact."""
import json, random, re
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = RAW / "batch_16.jsonl"
R = random.Random(1616)

SEEN = set()
for f in RAW.glob("batch_*.jsonl"):
    if f.name == OUT.name: continue
    for line in f.read_text("utf-8").splitlines():
        if line.strip():
            for t in json.loads(line)["transcript"]:
                if t["speaker"] == "visitor": SEEN.add(t["text"].strip().lower())

OPENERS = [
    "Hi, I'm Beacon, Leadrat's demo assistant. What does your business do?",
    "Hello! Beacon here. No forms, just a chat. Tell me about your team?",
    "Welcome to Leadrat. I'm Beacon. What kind of real estate work do you do?",
    "Hey there, Beacon from Leadrat. Who am I chatting with today?",
    "Good to have you here. I'm Beacon. What should this demo cover for you?",
    "Hi! Beacon here, I can show you the CRM live. What's your company about?",
    "Hello, I'm Beacon. Brokerage, developer, channel partner, something else?",
    "Hey! I'm Beacon, your guide to Leadrat. What brings you in today?",
    "Hi there. Beacon speaking. Tell me a little about how you sell property?",
    "Welcome! I'm Beacon. Before the tour, what does your firm focus on?",
    "Hi, this is Beacon from Leadrat. What are you hoping to fix with a CRM?",
    "Hello and welcome. I'm Beacon. Who's on the other side of the chat?",
    "Hey, Beacon here. Want a quick walkthrough? First, what's your setup?",
    "Hi! I'm Beacon. I'll keep this short. What's your role and company?",
    "Good morning! Beacon from Leadrat here. What does your team sell?",
    "Hi, Beacon here. Happy to answer questions or give a tour. Where do we start?",
    "Hello! I'm Beacon, Leadrat's live demo guide. What's your line of business?",
    "Hey, welcome in. I'm Beacon. Tell me what a normal sales week looks like for you?",
    "Hi there, I'm Beacon. Resale, new launches, leasing? What do you handle?",
    "Welcome. Beacon here, no sign-up needed. What would make this useful for you?",
    "Hi! Beacon from Leadrat. Are you looking at a CRM for yourself or for a team?",
    "Hello, Beacon here. I show people around Leadrat. What's your business?",
    "Hey! I'm Beacon. Quick question to start: what does your company do?",
    "Hi, I'm Beacon. Let's make this demo about your workflow. What do you do?",
    "Good evening! I'm Beacon from Leadrat. Tell me about your agency or project?",
    "Hi there! Beacon, Leadrat's assistant. What made you look at Leadrat today?",
]
OUSE = {}
def opener():
    i = min(range(len(OPENERS)), key=lambda k: (OUSE.get(k, 0), R.random()))
    OUSE[i] = OUSE.get(i, 0) + 1
    return OPENERS[i]

FIRST = ["Priya", "Rahul", "Ananya", "Vikram", "Sneha", "Arjun", "Kavya", "Rohan", "Isha", "Karan", "Neha", "Aditya",
         "Farah", "Omar", "Zara", "Yusuf", "Meera", "Siddharth", "Tanvi", "Nikhil", "Pooja", "Harsh", "Divya", "Aman",
         "Leena", "Imran", "Ritika", "Varun", "Aisha", "Kabir", "Shreya", "Manish", "Nadia", "Tarun", "Gauri", "Faisal"]
LAST = ["Mehta", "Iyer", "Shah", "Reddy", "Kapoor", "Nair", "Joshi", "Rao", "Khan", "Desai", "Menon", "Gupta", "Pillai", "Bhat"]
PRE = ["Skyline", "Harbour", "Crest", "Maple", "Lotus", "Keystone", "Silverline", "Banyan", "Horizon", "Northstar", "Emerald",
       "Palm", "Riverstone", "Sunrise", "Oakwood", "Bluegate", "Indigo", "Saffron", "Summit", "Coral", "Granite", "Amber",
       "Meridian", "Cedar", "Falcon", "Orchid", "Pinnacle", "Zenith", "Tidewater", "Monsoon", "Aster", "Vista", "Marigold"]
SUF = {"brokerage": ["Realty", "Properties", "Homes", "Estates", "Realtors"],
       "developer": ["Developers", "Infra", "Buildcon", "Constructions", "Projects"],
       "channel_partner": ["Advisors", "Property Partners", "Consultants", "Realty Partners"],
       "other_real_estate": ["Property Management", "Facility Services", "Co-living", "Home Services"],
       "unrelated": ["Logistics", "Software", "Foods", "Travels"]}
TYPEPH = {"brokerage": ["a resale brokerage", "a brokerage doing rentals and resale", "a property brokerage",
                        "a real estate agency, mostly secondary market", "a brokerage focused on premium homes"],
          "developer": ["a residential developer", "a real estate developer with two live projects", "a builder doing mid-segment apartments",
                        "a developer, plotted and villa projects", "a developer with a new launch coming"],
          "channel_partner": ["a channel partner for a few big builders", "a CP firm selling new launches", "a channel partner agency",
                              "a mandate and channel partner outfit", "a CP network selling for developers"],
          "other_real_estate": ["a property management company", "a co-living operator", "a facility and rental management firm",
                                "a home interiors firm that also refers property buyers"],
          "unrelated": ["a logistics company", "a small software shop", "a food delivery startup"]}
CITIES = [("India", "Mumbai"), ("India", "Pune"), ("India", "Bengaluru"), ("India", "Hyderabad"), ("India", "Delhi NCR"),
          ("India", "Ahmedabad"), ("India", "Chennai"), ("India", "Kolkata"), ("India", "Jaipur"), ("India", "Noida"),
          ("India", "Gurugram"), ("India", "Kochi"), ("India", "Indore"), ("India", "Lucknow"), ("UAE", "Dubai"),
          ("UAE", "Abu Dhabi"), ("UAE", "Sharjah"), ("India", "Nagpur"), ("India", "Surat"), ("India", "Chandigarh")]
ROLES = [("founder", "owner", "approver"), ("owner", "owner", "approver"), ("managing director", "executive", "approver"),
         ("director", "executive", "approver"), ("CEO", "executive", "approver"), ("sales head", "executive", None),
         ("VP sales", "executive", None), ("sales manager", "manager", None), ("CRM manager", "manager", None),
         ("operations manager", "manager", None), ("team lead", "manager", None), ("senior sales executive", "individual_contributor", None),
         ("marketing executive", "individual_contributor", None), ("co-founder", "owner", "approver")]
SOURCES = ["99acres", "MagicBricks", "Housing.com", "Facebook ads", "Google ads", "Instagram", "walk-ins", "referrals",
           "Bayut", "Property Finder", "Dubizzle", "our website", "NoBroker", "WhatsApp groups", "site hoardings"]
MANUAL = [["Excel"], ["WhatsApp"], ["Google Sheets"], ["Excel", "WhatsApp"], ["paper registers"], ["Google Sheets", "WhatsApp"]]
CRMS = ["Salesforce", "Zoho CRM", "HubSpot", "Sell.Do", "a homegrown CRM", "LeadSquared"]
PAINS = ["leads go cold before anyone calls", "no idea which agent followed up", "duplicate leads from portals",
         "site visits are not tracked", "managers can't see the pipeline", "agents leave and take the leads with them",
         "follow-up reminders get missed", "no reporting on lead source ROI", "calls are not logged anywhere",
         "hot leads get mixed up with junk enquiries", "inventory status is always out of date", "slow response to portal leads"]

def uniq(cands):
    """Pick an unused visitor line (case-insensitive) from candidates; raise if all are used."""
    cands = list(cands); R.shuffle(cands)
    for c in cands:
        k = c.strip().lower()
        if k not in SEEN:
            SEEN.add(k); return c
    tails = [", thanks", ". thanks!", " :)", ", cheers", ". appreciate it", " - that's fine", ", sounds good", ". ok?", " btw",
             ", no rush", ". thank you", " for sure", ", honestly", " then", ". cool"]
    heads = ["ok ", "right, ", "hmm ", "alright, ", "well, ", "so ", "yeah ", "fine, ", "okay so ", "got it. "]
    combos = [h + c + t for c in cands for h in [""] + heads for t in [""] + tails]
    R.shuffle(combos)
    for c in combos:
        if c.strip().lower() not in SEEN:
            SEEN.add(c.strip().lower()); return c
    raise RuntimeError("no unique line: " + cands[0])

class B:
    def __init__(s): s.tr, s.ev, s.L = [], {}, {}
    def bc(s, t): s.tr.append({"turn_id": len(s.tr) + 1, "speaker": "beacon", "text": t})
    def vi(s, cands, keys=(), **lab):
        s.tr.append({"turn_id": len(s.tr) + 1, "speaker": "visitor", "text": uniq(cands)})
        tid = len(s.tr)
        for k in keys: s.ev[k] = [tid]
        s.L.update(lab); return tid
    def add_ev(s, k, tid): s.ev.setdefault(k, []); s.ev[k] = sorted(set(s.ev[k]) | {tid})

PH = [0]
def phone(uae=False):
    PH[0] += 1
    return f"+971 50 000 6{PH[0]:03d}" if uae else f"+91 90000 6{PH[0]:04d}"
def email(first, co):
    slug = re.sub(r"[^a-z]", "", co.lower())[:14]
    return R.choice([f"{first.lower()}@{slug}.example.com", f"{first.lower()}.{R.choice(LAST).lower()}@{slug}.example.com",
                     f"sales@{slug}.example.com" if R.random() < .2 else f"{first.lower()[0]}{R.choice(LAST).lower()}@example.com"])

def profile(fit):
    if fit == "hi": return dict(agents=R.randint(20, 90), leads=R.choice([500, 600, 750, 800, 900, 1200, 1500, 2000, 2500, 3000]),
                                proc="manual", npain=2, inf="approver", nxt="within_30_days")
    if fit == "mid": return dict(agents=R.randint(6, 19), leads=R.choice([120, 150, 200, 250, 300, 350, 400]),
                                 proc=R.choice(["manual", "unsatisfied_crm"]), npain=R.choice([1, 2]),
                                 inf=R.choice(["approver", "sponsored_evaluator"]), nxt=R.choice(["within_30_days", "later"]))
    if fit == "low": return dict(agents=R.randint(1, 4), leads=R.choice([10, 20, 25, 30, 40, 50, 60, 80]), proc="satisfied_crm",
                                 npain=0, inf="none", nxt="later")
    if fit == "unk": d = profile("mid"); d["leads"] = None; return d

def discovery(b, otype, fit, stop):
    """Turns 2..8: intro, size, tools/pain, decision. `stop` = number of visitor turns to emit (1-4)."""
    P = profile(fit)
    country, city = R.choice(CITIES)
    uae = country == "UAE"
    role, sen, rinf = R.choice(ROLES)
    if P["inf"] == "approver" and rinf is None and fit == "hi": role, sen, rinf = R.choice(ROLES[:5])
    first = R.choice(FIRST)
    co = f"{R.choice(PRE)} {R.choice(SUF[otype])}"
    tph = R.choice(TYPEPH[otype])
    named = R.random() < .7
    b.meta = dict(first=first, co=co, uae=uae, P=P)
    b.bc(opener())
    who = f"{co}, " if named else ""
    b.vi([f"I'm the {role} at {who}{tph} in {city}.", f"hi, {first} here, {role}. we're {who}{tph}, based in {city}",
          f"{tph.capitalize()} out of {city}{', called ' + co if named else ''}. I'm the {role}.",
          f"Hello. {role.capitalize()} at {who}{tph}. We work mainly in {city}.",
          f"We're {tph} in {city}{' - ' + co if named else ''}. My title is {role}."],
         ["role", "seniority", "organisation.type", "geography"] + (["organisation.name"] if named else []),
         role=role, sen=sen, type=otype, name=co if named else None, countries=[country], cities=[city])
    if stop == 1: return P
    b.bc(R.choice(["How big is the sales team, and roughly how many leads a month?", "Nice. Team size and monthly enquiry volume?",
                   "Got it. How many agents do you have, and how many leads come in monthly?", "How many people sell for you, and what's the lead flow like?",
                   "Thanks! Quick one: headcount on sales and leads per month?"]))
    src = R.sample([s for s in SOURCES if (s in ("Bayut", "Property Finder", "Dubizzle")) == uae or s in ("walk-ins", "referrals", "Instagram", "our website", "Google ads")], 2)
    a, l = P["agents"], P["leads"]
    lt = f"about {l}" if l else R.choice(["honestly no clue on leads", "not sure how many leads, nobody counts", "leads, I really couldn't tell you"])
    lc = lt if l is None else f"{lt} leads"
    b.vi([f"{a} agents. {lc} a month, mostly {src[0]} and {src[1]}", f"we have {a} people in sales, {lc} monthly from {src[0]} plus {src[1]}",
          f"{a} on the team; {lc} each month. {src[0]} and {src[1]} bring most of it", f"team of {a}. {lc} per month, sources are {src[0]} and {src[1]}",
          f"{a} sales folks at {b.meta['co']}. {lc} a month via {src[0]}, {src[1]}"],
         ["organisation.agents", "lead_sources"] + (["monthly_leads"] if l else []), agents=a, lmin=l, lmax=l, src=src)
    if stop == 2: return P
    b.bc(R.choice(["How do you track leads today, and what's the biggest headache?", "What tools are you using now, and what's not working?",
                   "Here is the Leads list with source and owner. How does your team manage this today?", "Where do leads live right now? Any pain points?",
                   "This is the Follow-ups board. What do you use at the moment, and what breaks?"]))
    pains = R.sample(PAINS, P["npain"])
    if P["proc"] == "manual":
        tools = R.choice(MANUAL); tt = " and ".join(tools)
        pt = " and ".join(pains)
        b.vi([f"all on {tt}. problem is {pt}", f"{tt}, nothing else. the pain: {pt}", f"we run on {tt}; {pt}",
              f"just {tt} honestly, and {pt}", f"{tt} for everything at {b.meta['co']}. biggest issues, {pt}"],
             ["current_tooling", "process", "pain_points"], tools=tools, proc="manual", pain=pains)
    elif P["proc"] == "unsatisfied_crm":
        tools = [R.choice(CRMS)]; pt = " and ".join(pains)
        b.vi([f"we have {tools[0]} but {pt}", f"{tools[0]}, and it doesn't solve it: {pt}", f"using {tools[0]} for a year. still, {pt}",
              f"{tools[0]} is what we pay for, yet {pt}", f"on {tools[0]} in {b.meta['co']}, but {pt}"],
             ["current_tooling", "process", "pain_points"], tools=tools, proc="unsatisfied_crm", pain=pains)
    else:
        tools = [R.choice(CRMS)]
        b.vi([f"{tools[0]}, and it works fine. no real problems right now", f"we're happy on {tools[0]}, nothing is broken for us",
              f"{tools[0]} does the job. no complaints honestly", f"using {tools[0]}; no issues to fix, I'm just curious",
              f"{tools[0]} at {b.meta['co']} and it's fine, zero problems"],
             ["current_tooling", "process", "pain_points"], tools=tools, proc="satisfied_crm", pain=[])
    if stop == 3: return P
    b.bc(R.choice(["Who decides on software, and what's your timeline?", "Are you the one who signs off? And when would you want this live?",
                   "Here is the Manager Dashboard. Who approves a purchase like this, and how soon?", "Makes sense. Decision-maker and timing?",
                   "Who else is involved in choosing, and is this for this month or later?"]))
    when = {"within_30_days": ["this month", "in the next two weeks", "before month end", "within three weeks"],
            "later": ["next quarter", "after Diwali", "in a few months", "sometime next year"]}[P["nxt"]]
    w = R.choice(when)
    inf = {"approver": [f"I sign off. want it running {w}", f"my call, I approve budgets. looking at {w}", f"I decide. timing is {w}",
                        f"I'm the approver here, and we'd move {w}"],
           "sponsored_evaluator": [f"my boss decides, I'm evaluating for him. {w}", f"I'm shortlisting for our MD, she signs. target is {w}",
                                   f"the director approves; I'm doing the evaluation, {w}", f"evaluating on behalf of the partners, {w}"],
           "none": [f"not my decision at all, I'm just looking. maybe {w}", f"I have no say in buying. {w} perhaps",
                    f"no authority on purchases, just curious. {w} if ever"]}[P["inf"]]
    b.vi(inf, ["influence", "next_step"], inf=P["inf"], nxt=P["nxt"])
    return P

ASK = ["Would you like our sales team to get in touch?", "Shall I have someone from sales follow up with you?",
       "Want a specialist to reach out and set this up?", "Should I connect you with our sales team?",
       "Happy to have sales contact you. Would that help?", "Would a follow-up from our team be useful?"]
def ask(b): b.bc(R.choice(ASK))
def cdet(b): b.bc(R.choice(["Great. What's the best email or phone?", "Perfect. How should they reach you?", "Sure. Share a number or email?",
                            "Done. Which contact should they use?"]))

# ---------- closing patterns: each mutates b (turns + labels) ----------
def E_phone(b, m):
    ask(b); t = b.vi([f"yes, have someone call me", "yes please, a call works", "go ahead, get someone to ring me", "sure, have sales call me",
                      "yes, I'd like a call", "please do, a call is best", "yeah, set up a call with me"], ["consent"], consent=True)
    cdet(b); p = phone(m["uae"])
    b.vi([f"{p}", f"call {p}", f"my number is {p}", f"{p}, after 11am", f"{p} - I'm {m['first']}"], ["contact"], phone=p,
         cname=None)
def E_email(b, m):
    ask(b); e = email(m["first"], m["co"])
    b.vi([f"please share details on email, {e}", f"email is better: {e}. yes, send me the details", f"yes, reach me on {e}",
          f"send the proposal to {e}, happy to hear from sales", f"sure, have them email {e}"], ["consent", "contact"], consent=True, email=e)
def E_both(b, m):
    ask(b); b.vi(["yes, book a call", "book a call for me please", "let's book a call this week", "yes. book me a slot with sales",
                  "definitely, book a call"], ["consent"], consent=True)
    cdet(b); e, p = email(m["first"], m["co"]), phone(m["uae"])
    n = f"{m['first']} {R.choice(LAST)}"
    b.vi([f"{n}, {e}, {p}", f"name {n}. {p} or {e}", f"{e} / {p} - ask for {n}", f"I'm {n}: {p}, email {e}"], ["contact"],
         cname=n, email=e, phone=p)
def E_consent_nocontact(b, m):
    ask(b); b.vi(["yes, someone can reach out", "sure, have your team contact me", "yes, I'm okay with sales following up",
                  "fine by me, have them get in touch"], ["consent"], consent=True)
    cdet(b); b.vi(["I'll share it later, not now", "let me send that another time", "I'd rather not type it here yet",
                   "skip that for now, I'll come back"])
def E_question(b, m):
    ask(b); b.vi([f"before that, does it integrate with {R.choice(SOURCES)}?", "does it have a mobile app for agents?",
                  "can I import my existing Excel leads?", "what does it cost per user?", "is there an Arabic interface?",
                  "can managers reassign leads in bulk?", "how long does onboarding take usually?"])
    b.bc(R.choice(["Yes, that's supported. Anything else you want to see?", "It does. Want me to show it on screen?", "Good question, yes."]))
    b.vi(["ok thanks, good to know", "nice, that's useful", "alright, noted", "cool, thanks for clarifying", "got it, that helps"])
def E_maybe(b, m):
    ask(b); t = b.vi(["maybe, not sure yet", "hmm, maybe. let me see", "maybe later, I don't know", "possibly, I haven't decided",
                      "maybe. depends on budget"], ["next_step"], nxt="later")
def E_think(b, m):
    ask(b); b.vi(["I'll think about it and get back to you", "let me think it over first", "I need to think about it, will revert",
                  "give me some time to think", "I'll mull it over this week"], ["next_step"], nxt="later")
def E_brochure(b, m):
    ask(b); b.vi(["no call. just send me a brochure link here in the chat", "can you drop the brochure link right here instead?",
                  "just paste a pricing PDF link in this chat", "share a brochure link here, that's enough", "only a link in this chat please"])
    b.bc("Here's the product overview link: leadrat.example.com/overview")
    b.vi(["thanks, I'll read it", "got it, will go through it", "ok, downloading", "perfect, that's all", "thanks, will check it tonight"])
def E_myself(b, m):
    ask(b); b.vi(["no need, I'll reach out myself when ready", "I'll contact you guys myself if we go ahead", "don't worry, I'll get in touch on my own",
                  "I'll reach out when I'm ready, no follow-up", "I'll ping you myself later"], ["next_step"], nxt="later")
def E_feature_contact(b, m):
    e = email(m["first"], m["co"])
    b.bc("Anything specific you'd like to see?")
    b.vi([f"can the daily lead report go to {e} automatically?", f"if I set {e} as admin, do alerts go there?",
          f"will reminders reach {e} or only the app?", f"could {e} get a weekly summary?"], ["contact"], email=e)
    b.bc("Yes, reports can be scheduled to any email. Want sales to follow up?")
    b.vi(["no, just wanted to check that", "not needed, thanks", "no follow-up, I was only checking the feature", "nope, that answers it"])
def E_withdrawn(b, m):
    ask(b); b.vi(["yes, have them call", "sure, a call is fine", "ok, get sales to call me", "yes go ahead"])
    cdet(b); p = phone(m["uae"]); b.vi([f"{p}", f"it's {p}", f"use {p}"], ["contact"], phone=p)
    b.bc("Thanks, I'll pass that on.")
    b.vi(["actually, don't call. not now, maybe later", "wait, cancel that. no calls for now, maybe next quarter",
          "on second thought please don't have anyone call yet, later", "hold on, I changed my mind, no call right now, some other time"],
         ["next_step"], nxt="later")
def E_refuse_then_yes(b, m):
    ask(b); b.vi(["no calls please", "not interested in a sales call", "no, I don't want anyone contacting me", "no thanks, no follow-up"])
    b.bc("No problem. Here's how lead assignment works on the Auto-Allocation screen.")
    b.vi(["wait, that auto-assign is exactly what we need. okay, have someone call me", "ok this changes things. yes, please get sales to call",
          "fine, you've convinced me. have someone call", "alright, I take it back, I want a call"], ["consent"], consent=True)
    cdet(b); p = phone(m["uae"]); b.vi([f"{p}", f"{p}, ask for {m['first']}", f"reach me at {p}"], ["contact"], phone=p,
                                      cname=None)
def E_colleague_phone(b, m):
    ask(b); n = R.choice(FIRST); p = phone(m["uae"])
    b.vi([f"yes, call my manager {n} on {p}", f"please have sales call {n}, our sales head, at {p}", f"yes, but talk to {n}: {p}",
          f"sure, contact my colleague {n} on {p}, she handles vendors"], ["consent", "contact"], consent=True, cname=n, phone=p)
def E_colleague_email(b, m):
    ask(b); n = R.choice(FIRST); e = email(n, m["co"])
    b.vi([f"yes, email our ops head {n} at {e}", f"please send details to {n}, {e}", f"sure, loop in {n} on {e}",
          f"yes, have sales write to {n} at {e}"], ["consent", "contact"], consent=True, cname=n, email=e)
def E_decline(b, m):
    ask(b); b.vi(["not interested, please don't contact me", "no. I don't want any follow-up at all", "please don't reach out, we're not buying",
                  "no thanks, and no calls or emails please", "we won't go ahead, don't contact us"], ["next_step"], nxt="declined")
def E_later(b, m):
    ask(b); b.vi(["not this year. maybe revisit next year", "not now, try us in six months", "too early for us, maybe after the new financial year",
                  "not right now, perhaps later in the year"], ["next_step"], nxt="later")
def E_unsub(b, m):
    ask(b); b.vi(["unsubscribe", "unsubscribe me from everything", "please unsubscribe me", "unsubscribe. no more messages"], ["next_step"], nxt="declined")
def E_stop(b, m):
    ask(b); b.vi(["stop messaging me", "stop sending me messages", "please stop messaging, not interested", "stop. don't message me again"],
                 ["next_step"], nxt="declined")
def E_polite(b, m):
    ask(b); b.vi(["thanks, that's all I needed. bye", "appreciate the tour, I'm done for now", "that was helpful, signing off",
                  "cheers, that covers it for today", "great demo, thanks. leaving it here"])
def E_bad_email(b, m):
    ask(b); b.vi(["yes please follow up", "yes, contact me", "sure, have them reach out", "yes, happy to talk to sales"], ["consent"], consent=True)
    cdet(b); f = m["first"].lower(); e = R.choice([f"{f}@example,com", f"{f}@@example.com", f"{f}.example.com", f"{f}@example"])
    b.vi([f"{e}", f"email: {e}", f"{e} is my email"], ["contact"], email=e)
def E_bad_phone(b, m):
    ask(b); b.vi(["yes call me", "yes, please call", "ok, a call works for me", "yes, get someone to phone me"], ["consent"], consent=True)
    cdet(b); PH[0] += 1; p = R.choice([f"+91 90000 6{PH[0]:03d}", f"90000-6{PH[0]:04d}-", f"+91 9000 06{PH[0]:04d}"]) if not m["uae"] else f"+971 50 00 6{PH[0]:03d}"
    b.vi([f"{p}", f"number {p}", f"{p} call anytime"], ["contact"], phone=p)
def E_email_no_phone(b, m):
    ask(b); b.vi(["yes, but only by email", "yes, email me, no phone calls please", "okay, email follow-up is fine, don't call"], ["consent"], consent=True)
    cdet(b); e = email(m["first"], m["co"]); b.vi([f"{e}", f"{e}. no phone number, sorry", f"use {e} only"], ["contact"], email=e)
def E_whatsapp(b, m):
    ask(b); p = phone(m["uae"])
    b.vi([f"yes, whatsapp me on {p}", f"sure, message me on WhatsApp, {p}", f"ok, reach me on WhatsApp: {p}",
          f"yes, ping me on {p} on WhatsApp"], ["consent", "contact"], consent=True, phone=p)
def E_name_only(b, m):
    ask(b); b.vi([f"yes, tell them {m['first']} from {m['co']} is interested", f"sure, I'm {m['first']}, have sales look me up",
                  f"yes, my name's {m['first']}, they can reach out"], ["consent", "contact"], consent=True, cname=m["first"])
    cdet(b); b.vi(["find me on LinkedIn, I won't share a number here", "just the name for now", "no number or email, sorry"])
def E_contact_then_consent(b, m):
    p = phone(m["uae"])
    b.bc("Anything you'd like to check?")
    b.vi([f"does the app send SMS to {p} when a lead lands?", f"if my number is {p}, will I get lead alerts on it?",
          f"can alerts go to {p} as well as the app?"], ["contact"], phone=p)
    b.bc("Yes, SMS and push alerts are both supported.")
    ask(b); b.vi(["yes, go ahead, call me on that number", "yes, same number, have sales call", "sure, call me on the number above"], ["consent"],
                 consent=True)
def E_colleague_nocons(b, m):
    ask(b); n = R.choice(FIRST); e = email(n, m["co"])
    b.vi([f"not yet. fyi my colleague {n} is {e}, she may look at this", f"no calls. {n} ({e}) handles our tools anyway",
          f"don't contact anyone yet. for reference, {n}'s email is {e}"], ["contact"], cname=n, email=e)
def E_consent_then_decline(b, m):
    ask(b); b.vi(["yes okay", "sure", "yes, fine", "ok go on"])
    cdet(b); b.vi(["actually I'm not interested at all. remove my details", "you know what, no. don't contact me",
                   "on reflection we won't buy, please don't reach out"], ["next_step"], nxt="declined")
def E_pricing_email(b, m):
    ask(b); e = email(m["first"], m["co"])
    b.vi([f"please email pricing to {e} and have someone follow up", f"yes, send the quote on {e}, and sales can contact me",
          f"share details on {e}, I'm happy to be contacted"], ["consent", "contact"], consent=True, email=e)
def E_chat_only(b, m):
    ask(b); b.vi(["no, just send me info here in the chat", "keep it in this chat, no follow-up", "tell me here, I don't want calls",
                  "answer here please, nobody needs to contact me"])
def E_ask_if_call(b, m):
    ask(b); b.vi(["if I give my number, will sales keep calling me?", "will I get spam calls if I say yes?", "how often would they call?"])
    b.bc("Just one call to understand your needs, and only if you agree.")
    b.vi(["ok, I'll hold off for now", "hmm, let me decide later", "fine, not today though"])
def E_sure_later(b, m):
    ask(b); b.vi(["sure, but in two months. contact me then", "yes, have sales reach out after the quarter ends", "yes, but only after Diwali"],
                 ["consent", "next_step"], consent=True, nxt="later")
    cdet(b); e = email(m["first"], m["co"]); b.vi([f"{e}", f"email {e}"], ["contact"], email=e)
def E_exploring(b, m):
    ask(b); b.vi(["no thanks, just exploring", "no, just browsing options", "not now, just comparing tools", "nah, window shopping today"])

FAMS = [  # (org type, scenario, closing, fit list for 6 variations)
    ("brokerage", "yes_call_phone", E_phone, "hi hi hi mid hi hi"),
    ("developer", "yes_call_phone", E_phone, "hi hi hi hi mid hi"),
    ("channel_partner", "email_details", E_email, "hi hi hi hi mid hi"),
    ("brokerage", "email_details", E_email, "hi hi mid hi hi"),
    ("developer", "book_call_full_contact", E_both, "hi hi hi hi hi mid"),
    ("channel_partner", "book_call_full_contact", E_both, "hi hi hi mid hi"),
    ("brokerage", "consent_no_contact", E_consent_nocontact, "hi mid hi hi mid"),
    ("developer", "consent_no_contact", E_consent_nocontact, "hi hi mid hi mid"),
    ("brokerage", "feature_question_not_consent", E_question, "hi mid hi mid hi unk"),
    ("channel_partner", "feature_question_not_consent", E_question, "hi hi mid unk hi"),
    ("developer", "maybe", E_maybe, "hi mid hi mid hi hi"),
    ("brokerage", "think_about_it", E_think, "hi mid hi hi mid"),
    ("other_real_estate", "think_about_it", E_think, "mid mid low mid hi"),
    ("channel_partner", "brochure_in_chat", E_brochure, "hi mid hi mid low"),
    ("brokerage", "reach_out_myself", E_myself, "hi mid hi mid hi mid"),
    ("developer", "email_typed_for_feature", E_feature_contact, "hi mid hi unk hi"),
    ("brokerage", "email_typed_for_feature", E_feature_contact, "hi hi mid hi mid"),
    ("channel_partner", "consent_withdrawn", E_withdrawn, "hi hi mid hi hi"),
    ("brokerage", "consent_withdrawn", E_withdrawn, "hi mid hi hi hi"),
    ("developer", "refusal_then_consent", E_refuse_then_yes, "hi hi hi hi mid hi"),
    ("brokerage", "refusal_then_consent", E_refuse_then_yes, "hi hi hi mid hi"),
    ("brokerage", "colleague_phone", E_colleague_phone, "hi hi hi hi mid hi"),
    ("developer", "colleague_email", E_colleague_email, "hi hi hi hi mid"),
    ("channel_partner", "colleague_phone", E_colleague_phone, "hi hi hi mid hi"),
    ("brokerage", "firm_decline", E_decline, "hi mid low hi mid"),
    ("developer", "firm_decline", E_decline, "mid hi low mid hi"),
    ("other_real_estate", "firm_decline", E_decline, "low mid low mid low"),
    ("channel_partner", "not_this_year", E_later, "hi mid hi low mid"),
    ("brokerage", "unsubscribe", E_unsub, "low mid hi low mid hi"),
    ("developer", "stop_messaging", E_stop, "mid low hi low mid hi"),
    ("channel_partner", "stop_messaging", E_stop, "low hi mid low low"),
    ("other_real_estate", "polite_exit", E_polite, "low low mid low low"),
    ("brokerage", "polite_exit", E_polite, "low mid low hi low"),
    ("developer", "malformed_email", E_bad_email, "hi hi hi hi mid hi"),
    ("brokerage", "malformed_phone", E_bad_phone, "hi hi hi mid hi"),
    ("channel_partner", "email_only_no_phone", E_email_no_phone, "hi hi hi hi mid"),
    ("brokerage", "whatsapp_consent", E_whatsapp, "hi hi hi mid hi hi"),
    ("developer", "name_only_consent", E_name_only, "hi hi mid hi mid"),
    ("channel_partner", "contact_first_consent_later", E_contact_then_consent, "hi hi hi mid hi"),
    ("developer", "colleague_contact_no_consent", E_colleague_nocons, "hi mid hi hi mid"),
    ("brokerage", "consent_then_decline", E_consent_then_decline, "hi mid low hi mid"),
    ("developer", "pricing_on_email", E_pricing_email, "hi hi hi mid hi hi"),
    ("other_real_estate", "chat_only_no_followup", E_chat_only, "low mid low mid low"),
    ("channel_partner", "asks_if_sales_will_call", E_ask_if_call, "hi mid hi mid hi"),
    ("brokerage", "consent_but_later", E_sure_later, "hi hi mid hi hi mid"),
    ("unrelated", "just_exploring", E_exploring, "low low low low low"),
    ("other_real_estate", "unsubscribe", E_unsub, "low low mid low low"),
]

KMAP = {"role": "role", "sen": "seniority"}
def label(b):
    L = b.L
    return {"role": L.get("role"), "seniority": L.get("sen", "unknown"),
            "organisation": {"name": L.get("name"), "type": L.get("type", "unknown"), "agents": L.get("agents")},
            "pain_points": L.get("pain"), "current_tooling": L.get("tools"), "process": L.get("proc", "unknown"),
            "geography": {"countries": L.get("countries"), "cities": L.get("cities")},
            "monthly_leads": {"min": L.get("lmin"), "max": L.get("lmax")}, "lead_sources": L.get("src"),
            "influence": L.get("inf", "unknown"), "next_step": L.get("nxt", "unknown"), "consent": L.get("consent", False),
            "contact": {"name": L.get("cname"), "email": L.get("email"), "phone": L.get("phone")}, "evidence": b.ev}

def build(otype, scen, close, fit, partial, pstop, cont_partial):
    b = B()
    if partial and cont_partial:
        # partial that still reaches a contact moment mid-demo (no discovery completed)
        discovery(b, otype, fit, pstop); close(b, b.meta)
    elif partial:
        discovery(b, otype, fit, pstop)
    else:
        discovery(b, otype, fit, 4); close(b, b.meta)
    return b

EX = []
for fi, (otype, scen, close, fits) in enumerate(FAMS):
    fits = fits.split()
    for v, fit in enumerate(fits):
        partial = v == 1 or (v == 3 and fi % 2 == 0)
        pstop = R.choice([2, 3]) if partial else 4
        cont = partial and close in (E_feature_contact, E_colleague_nocons, E_contact_then_consent, E_question, E_think, E_consent_nocontact, E_phone) and R.random() < .6
        for attempt in range(30):
            snap = set(SEEN), PH[0], dict(OUSE)
            try:
                b = build(otype, scen, close, fit, partial, pstop, cont); break
            except RuntimeError:
                SEEN.clear(); SEEN.update(snap[0]); PH[0] = snap[1]; OUSE.clear(); OUSE.update(snap[2])
        else:
            raise SystemExit(f"could not build {scen} v{v}")
        EX.append({"id": f"b16-{len(EX) + 1:03d}", "family": f"{otype}/b16_{scen}", "language": "en", "partial": partial,
                   "transcript": b.tr, "label": label(b)})

assert len(EX) == 250, len(EX)
OUT.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in EX), "utf-8")
print("wrote", len(EX), "to", OUT)
