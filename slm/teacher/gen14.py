"""Batch 14: unstated and uncertain facts (English).

Visitors share most facts but leave one ICP dimension unstated, evade, change the subject, or stop before
answering; a role without stated authority leaves influence unknown. Controls with complete facts keep the
model filling what IS known. Each visitor turn carries the facts it states; labels/evidence accumulate
from those turns, so a cut transcript is labelled only with what was said so far.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "batch_14.jsonl"
rows = []

B = lambda t: ('b', t, {})
def V(t, **facts): return ('v', t, facts)

PATH = {'role': 'role', 'sen': 'seniority', 'name': 'organisation.name', 'typ': 'organisation.type',
        'agents': 'organisation.agents', 'pains': 'pain_points', 'tools': 'current_tooling', 'proc': 'process',
        'cities': 'geography', 'leads': 'monthly_leads', 'src': 'lead_sources', 'inf': 'influence',
        'nxt': 'next_step', 'consent': 'consent', 'cname': 'contact', 'email': 'contact', 'phone': 'contact'}
UAE = {"Dubai", "Abu Dhabi", "Sharjah"}

def build(turns):
    f, ev = {}, {}
    for i, (s, _, facts) in enumerate(turns, 1):
        for k, val in facts.items():
            if k == 'clear':            # unresolved contradiction: forget the field and its evidence
                for c in val: f.pop(c, None); ev.pop(PATH[c], None)
                continue
            if val is None: continue
            f[k] = val
            p = PATH[k]
            if p == 'contact': ev['contact'] = sorted(set(ev.get('contact', []) + [i]))
            else: ev[p] = [i]
    lmin, lmax = f.get('leads', (None, None))
    cities = f.get('cities')
    countries = None if not cities else sorted({"UAE" if c in UAE else "India" for c in cities})
    return {"role": f.get('role'), "seniority": f.get('sen', 'unknown'),
            "organisation": {"name": f.get('name'), "type": f.get('typ', 'unknown'), "agents": f.get('agents')},
            "pain_points": f.get('pains'), "current_tooling": f.get('tools'), "process": f.get('proc', 'unknown'),
            "geography": {"countries": countries, "cities": cities},
            "monthly_leads": {"min": lmin, "max": lmax}, "lead_sources": f.get('src'),
            "influence": f.get('inf', 'unknown'), "next_step": f.get('nxt', 'unknown'), "consent": f.get('consent', False),
            "contact": {"name": f.get('cname'), "email": f.get('email'), "phone": f.get('phone')}, "evidence": ev}

# Every visitor line must be new across all raw batches.
SEEN = set()
for fp in (ROOT / "data" / "raw").glob("batch_*.jsonl"):
    if fp.name == OUT.name: continue
    for line in fp.read_text("utf-8").splitlines():
        if line.strip():
            for t in json.loads(line)["transcript"]:
                if t["speaker"] == "visitor": SEEN.add(t["text"].strip().lower())
TAGS = [", to be honest", ", for what it's worth", ", if that helps", " at the moment", ", roughly speaking", " as of now",
        ", just so you know", ", I guess", " for the record", ", in short"]
def uniq(text):
    base, n = text, 0
    while text.strip().lower() in SEEN:
        text = base.rstrip(".?") + TAGS[n % len(TAGS)] + ("." if n < len(TAGS) else f" ({n // len(TAGS)})"); n += 1
    SEEN.add(text.strip().lower()); return text

OPENERS = [
    "Hi, I'm Beacon, Leadrat's demo assistant. What kind of property business are you with?",
    "Hello! Beacon here. No forms, just a chat. What does your company do?",
    "Welcome to Leadrat. I'm Beacon. What would you like to see first?",
    "Hey there, Beacon from Leadrat. Tell me a little about your team?",
    "Good to have you here. I'm Beacon. Brokerage, developer, or something else?",
    "Hi! I'm Beacon and I can show you Leadrat live. Where should we start?",
    "Hello, this is Beacon. What brings you to Leadrat today?",
    "Hi there. Beacon here, happy to walk you through the CRM. What's your business?",
    "Welcome! I'm Beacon. Want a quick tour, or do you have a specific question?",
    "Hey! Beacon here. How are you handling leads right now?",
    "Hello and welcome. I'm Beacon, Leadrat's guide. Who am I chatting with?",
    "Hi, Beacon from Leadrat. What made you look at a CRM today?",
    "Namaste and welcome, I'm Beacon. What does your real estate work look like?",
    "Hi! I'm Beacon. I can show leads, listings and follow-ups. What matters most to you?",
    "Hello! Beacon here. Tell me what you sell and I'll tailor the demo.",
    "Welcome in. I'm Beacon. What should this demo help you figure out?",
    "Hi there, Beacon speaking. Are you exploring for yourself or for a team?",
    "Hey, I'm Beacon. Shall I start with the leads screen, or would you like to tell me about your setup?",
    "Hi! Beacon here from Leadrat. What's going on with your sales pipeline?",
    "Hello, I'm Beacon. Ask me anything about Leadrat. What's your line of business?",
    "Good day! I'm Beacon, and I show people around Leadrat. What are you working on?",
    "Hi, welcome. Beacon here. Which market do you operate in?",
    "Hello there! I'm Beacon. Curious about Leadrat? Tell me what your company does.",
    "Hey, welcome to the Leadrat demo. I'm Beacon. What's your role there?",
    "Hi! I'm Beacon. Before the screens, a quick question: what does your team handle day to day?",
    "Welcome! Beacon here. Residential, commercial, rentals? What's your focus?",
    "Hi, this is Beacon. I'd love to understand your business before showing anything. Where do you fit?",
    "Hello! I'm Beacon, Leadrat's live demo guide. How can I help today?",
    "Hi there! Beacon here. What prompted the visit?",
    "Hey! I'm Beacon. Is there a problem you're hoping a CRM will fix?",
]

# ---------- parameters ----------
PRE = ["Saffron", "Bluestone", "Lotus", "Crescent", "Northgate", "Riverbend", "Emerald", "Pinnacle", "Harbourview", "Sandalwood",
       "Coral", "Skyline", "Banyan", "Monsoon", "Amberline", "Silveroak", "Tulsi", "Greystone", "Indigo", "Marigold",
       "Cedar", "Falcon", "Jasmine", "Oakridge", "Palmyra", "Horizon", "Kestrel", "Mistral", "Vantage", "Zephyr"]
SUF = {"brokerage": ["Realty", "Property Advisors", "Homes", "Estates", "Realtors"],
       "developer": ["Developers", "Infra", "Buildcon", "Constructions", "Projects"],
       "channel_partner": ["Channel Partners", "Property Consultants", "Sales Partners", "Realty Associates", "Distribution"],
       "other_real_estate": ["Property Management", "Facility Services", "Coliving", "Workspaces", "Stays"],
       "unrelated": ["Logistics", "Foods", "Textiles", "EdTech", "Motors"],
       "unknown": ["Group", "Ventures", "Holdings", "Partners", "and Co"]}
TDESC = {"brokerage": ["resale brokerage", "residential brokerage", "rentals and resale agency", "property brokerage", "brokerage firm", "real estate agency"],
         "developer": ["residential developer", "real estate developer", "mid-size builder", "developer with two live projects", "township developer", "housing developer"],
         "channel_partner": ["channel partner firm", "channel partner for a few builders", "developer channel partner", "CP firm selling new launches", "channel partner outfit", "builder channel partner"],
         "other_real_estate": ["property management company", "coliving operator", "facility management firm", "coworking operator", "holiday home operator", "rental management company"]}
IN_CITIES = ["Mumbai", "Pune", "Bengaluru", "Hyderabad", "Gurugram", "Ahmedabad", "Chennai", "Kolkata", "Jaipur", "Noida", "Kochi", "Indore",
             "Lucknow", "Nagpur", "Thane", "Navi Mumbai", "Surat", "Chandigarh", "Coimbatore", "Vadodara"]
AE_CITIES = ["Dubai", "Abu Dhabi", "Sharjah"]
NAMES = ["Rohan", "Priya", "Arjun", "Neha", "Vikram", "Sana", "Karan", "Divya", "Farhan", "Ishita", "Manish", "Aditi", "Rahul", "Zoya",
         "Siddharth", "Meera", "Nikhil", "Tanvi", "Imran", "Pooja", "Aman", "Ritika", "Yusuf", "Kavya", "Harsh", "Anjali", "Omar", "Sneha",
         "Deepak", "Fatima", "Gaurav", "Lavanya", "Kabir", "Nisha", "Varun", "Aisha", "Tarun", "Shreya", "Ali", "Mehak"]
SRCS = [["99acres", "MagicBricks"], ["Facebook ads", "walk-ins"], ["Housing.com", "Google ads"], ["Instagram", "referrals"],
        ["MagicBricks", "Facebook ads"], ["NoBroker", "WhatsApp groups"], ["Google ads", "99acres"], ["Instagram ads", "hoardings"]]
AE_SRCS = [["Bayut", "Property Finder"], ["Dubizzle", "Property Finder"], ["Bayut", "Instagram"]]
PAINS = [("leads come in from three portals and nobody knows who called whom", "no visibility on who contacted which lead"),
         ("follow-ups slip after the first call", "missed follow-ups"),
         ("the same buyer gets called by two agents", "duplicate calls to the same lead"),
         ("I can't see which agent is sitting on leads", "no view of agent performance"),
         ("site visits don't get logged anywhere", "site visits not tracked"),
         ("portal leads take hours to reach an agent", "slow lead response"),
         ("when an agent quits, their contacts leave with them", "lead data lost when agents leave"),
         ("we have no idea which source actually converts", "no source attribution"),
         ("reminders live in people's heads", "no follow-up reminders"),
         ("inventory status is always out of date", "outdated inventory status")]
G = [0]
def P(typ, uae, k):
    g = G[0]; G[0] += 1
    name = f"{PRE[g % 30]} {SUF[typ][(g // 30 + g) % 5]}"
    city = AE_CITIES[g % 3] if uae else IN_CITIES[(g * 7) % 20]
    nm = NAMES[(g * 3) % 40]
    slug = name.lower().replace(" ", "")
    return dict(g=g, k=k, typ=typ, co=name, city=city, nm=nm,
                td=TDESC[typ][g % 6] if typ in TDESC else "business",
                ag=[4, 7, 9, 12, 15, 18, 22, 26, 30, 35, 40, 48, 55, 60][g % 14],
                ld=[80, 120, 180, 250, 320, 400, 450, 550, 600, 750, 900, 1200, 1500][(g * 5) % 13],
                src=(AE_SRCS if uae else SRCS)[g % (3 if uae else 8)],
                ph=(f"+971 50 000 4{g % 1000:03d}" if uae else f"+91 90000 4{g:04d}"),
                em=f"{nm.lower()}@{slug}.example.com", pa=PAINS[g % 10], pb=PAINS[(g + 3) % 10])

def pick(opts, p): return opts[p['k'] % len(opts)]
def srcs(p): return " and ".join(p['src'])

# ---------- reusable visitor statements ----------
def v_org(p):
    t = pick([f"We're {p['co']}, a {p['td']} in {p['city']}.",
              f"{p['co']} here, {p['td']} based out of {p['city']}.",
              f"I'm with {p['co']}. We're a {p['td']} working mainly in {p['city']}.",
              f"Our firm is {p['co']}, a {p['td']} in the {p['city']} market.",
              f"{p['co']} from {p['city']}. We're a {p['td']}.",
              f"Writing from {p['co']}, a {p['td']} covering {p['city']}."], p)
    return V(t, name=p['co'], typ=p['typ'], cities=[p['city']])
def v_ag(p):
    return V(pick([f"{p['ag']} agents on the team.", f"We have {p['ag']} people selling.",
                   f"The sales floor is {p['ag']} strong.", f"{p['ag']} in sales right now.",
                   f"Around {p['ag']} agents, all full-time.", f"Team of {p['ag']} brokers."], p), agents=p['ag'])
def v_ld(p):
    return V(pick([f"About {p['ld']} leads a month, mostly from {srcs(p)}.", f"Roughly {p['ld']} enquiries monthly via {srcs(p)}.",
                   f"We see close to {p['ld']} leads each month, {srcs(p)} being the big ones.", f"{p['ld']} a month on average, from {srcs(p)}.",
                   f"Monthly it's about {p['ld']} leads. {srcs(p)} bring most of them.", f"Something like {p['ld']} leads per month through {srcs(p)}."], p),
             leads=(p['ld'], p['ld']), src=p['src'])
def v_manual(p, pains=True):
    tools = pick([["Excel", "WhatsApp"], ["Google Sheets"], ["WhatsApp", "paper registers"], ["Excel"], ["Google Sheets", "WhatsApp"], ["notebooks", "WhatsApp"]], p)
    tl = " and ".join(tools)
    if pains:
        t = pick([f"It's all {tl}. Honestly {p['pa'][0]}, and {p['pb'][0]}.", f"{tl}, nothing fancy. The trouble is {p['pa'][0]}; also {p['pb'][0]}.",
                  f"We run on {tl}. Two headaches: {p['pa'][0]}, and {p['pb'][0]}.", f"Just {tl}. Problem one, {p['pa'][0]}. Problem two, {p['pb'][0]}.",
                  f"Everything sits in {tl}, so {p['pa'][0]} and {p['pb'][0]}.", f"{tl} is our system. Biggest issues: {p['pa'][0]}, plus {p['pb'][0]}."], p)
        return V(t, tools=tools, proc="manual", pains=[p['pa'][1], p['pb'][1]])
    t = pick([f"We use {tl} for everything.", f"All in {tl} right now.", f"{tl}, that's the whole setup.", f"It lives in {tl}.",
              f"Just {tl} across the team.", f"Our tracking is {tl}."], p)
    return V(t, tools=tools, proc="manual")
def v_pains_only(p):
    return V(pick([f"Main thing: {p['pa'][0]}. And {p['pb'][0]}.", f"Two problems really. {p['pa'][0].capitalize()}, and {p['pb'][0]}.",
                   f"Biggest pain is that {p['pa'][0]}. Also {p['pb'][0]}.", f"Well, {p['pa'][0]}, and on top of that {p['pb'][0]}.",
                   f"Top of the list: {p['pa'][0]}. Second: {p['pb'][0]}.", f"Honestly {p['pa'][0]} and {p['pb'][0]}."], p),
             pains=[p['pa'][1], p['pb'][1]])
def v_appr(p):
    return V(pick(["I'm the founder, the decision on software is mine.", "I own the business, so I sign off on this.",
                   "I'm the MD and I approve any spend like this.", "It's my company, I make the call.",
                   "I'm a partner and I can sign on my own.", "As the owner, the budget is mine to approve."], p),
             **pick([dict(role="founder", sen="owner"), dict(role="owner", sen="owner"), dict(role="MD", sen="executive"),
                     dict(), dict(role="partner", sen="owner"), dict(role="owner", sen="owner")], p), inf="approver")
def v_soon(p):
    return V(pick(["We'd like to be live within the next few weeks.", "Looking to start this month.", "Want this running in the next couple of weeks.",
                   "We need something before the month ends.", "Ideally we switch within 30 days.", "I want to move on it in the next two or three weeks."], p),
             nxt="within_30_days")
def v_later(p):
    return V(pick(["Not before next quarter though.", "Probably in three or four months.", "It's a next-year thing for us.",
                   "We'll look again after the festive season, a few months out.", "Maybe in six months.", "Timeline is later this year, not now."], p), nxt="later")
def v_consent(p, via="email"):
    c = p['em'] if via == "email" else p['ph']
    opts = [(f"Yes, have sales reach me at {c}.", False), (f"Sure, you can contact me: {c}.", False), (f"Go ahead and pass it to sales. {c}", False),
            (f"Okay, someone can follow up. {c}, I'm {p['nm']}.", True), (f"Fine by me, contact me on {c}.", False), (f"Yes please. {p['nm']}, {c}.", True)]
    t, named = pick(opts, p)
    kw = dict(consent=True, **({"email": c} if via == "email" else {"phone": c}))
    if named: kw["cname"] = p['nm']
    return V(t, **kw)

BQ = {"team": ["How many agents do you have?", "What's the team size?", "How big is the sales team?"],
      "leads": ["How many leads a month, and from where?", "What's your monthly lead volume?", "Roughly how many enquiries come in each month?"],
      "tools": ["How do you track leads today?", "What are you using to manage leads right now?", "What's your current setup for leads?"],
      "pain": ["What's the biggest problem right now?", "Where does it hurt most today?", "What would you fix first?"],
      "who": ["Who makes the call on a tool like this?", "Are you the one who decides, or someone else?", "Who signs off on software?"],
      "when": ["What's your timeline?", "When are you hoping to start?", "Is this for now or later?"],
      "consent": ["Would you like our sales team to follow up?", "Shall I have someone from sales contact you?", "Want sales to reach out?"],
      "demo": ["Here's the Leads screen with source and owner columns.", "This is the follow-up board with reminders.", "Here's round-robin assignment in action."]}
def bq(key, p): return B(BQ[key][(p['g'] + len(key)) % 3])

# ---------- family registry ----------
# kind: "consent" (consent+contact, one dimension unknown), "open" (uncertain, no consent), "control" (complete)
FAM = []
def family(name, typ="brokerage", kind="open", n=6, partial=(1, 2, 3, 4), uae=False, precut=False):
    def deco(fn): FAM.append((name, typ, kind, n, set(partial), uae, precut, fn)); return fn
    return deco

def E(fam, turns, partial):
    tt = [(s, uniq(x) if s == 'v' else x, f) for s, x, f in turns]
    tr = [{"turn_id": i + 1, "speaker": "beacon" if s == 'b' else "visitor", "text": x} for i, (s, x, _) in enumerate(tt)]
    rows.append({"id": "b14-%03d" % (len(rows) + 1), "family": fam, "language": "en", "partial": partial,
                 "transcript": tr, "label": build(tt)})

CLOSERS = ["That's all for today.", "No, I'm good.", "Nothing more for now.", "All set, thanks.", "Covered what I needed.", "That's enough, cheers."]

# == consent + contact, one dimension unknown (human_review) ==
@family("brokerage/b14_consent_no_influence", kind="consent", partial=(4, 5))
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p),
            B("Here's the follow-up board. When are you looking to start?"), v_soon(p), bq("consent", p), v_consent(p),
            B("Thanks! Anything else you'd like to see?"), V(pick(CLOSERS, p))]

@family("developer/b14_consent_no_process", "developer", kind="consent")
def _(p):
    return [bq("pain", p), v_org(p), bq("team", p), v_ag(p), bq("leads", p), v_ld(p),
            B("Got it. What problems do you run into with those leads?"), v_pains_only(p), bq("who", p), v_appr(p),
            B("And timing?"), v_soon(p), bq("consent", p), v_consent(p, "phone")]

@family("brokerage/b14_consent_no_pain", kind="consent")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("tools", p), v_manual(p, pains=False), bq("pain", p),
            V(pick(["Hard to say, nothing specific comes to mind.", "I'd rather see the product than list problems.", "Not sure yet, still thinking about it.",
                    "Can't point to one thing really.", "Let me get back to you on that.", "Depends who you ask on the team."], p)),
            bq("leads", p), v_ld(p), bq("who", p), v_appr(p), v_soon(p), bq("consent", p), v_consent(p)]

@family("channel_partner/b14_consent_no_agents", "channel_partner", kind="consent")
def _(p):
    return [bq("team", p), v_org(p),
            V(pick(["Team size changes every month, I'd rather not give a number.", "Depends on the season, it goes up and down.", "Not sure of the exact headcount, HR would know.",
                    "A handful full-time plus freelancers, hard to count.", "It varies with each launch.", "I'll skip that one for now."], p)),
            bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p), v_soon(p), bq("consent", p), v_consent(p, "phone")]

@family("brokerage/b14_consent_no_leads", kind="consent")
def _(p):
    return [bq("leads", p),
            V(pick(["A lot, honestly. Never counted.", "Decent volume, I don't track the number.", "Enough to keep everyone busy.",
                    "Plenty, but I couldn't give you a figure.", "Loads from the portals, no idea of the total.", "Quite a few, I'd have to check."], p)),
            B("No problem. Tell me about the business?"), v_org(p), v_ag(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p), v_soon(p),
            bq("consent", p), v_consent(p)]

@family("developer/b14_consent_no_nextstep", "developer", kind="consent")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p), bq("when", p),
            V(pick(["No fixed timeline yet.", "Depends on how the board meeting goes.", "Not sure, we haven't decided when.", "Can't commit to a date.",
                    "Timing is still open.", "It depends on budget approval, no date."], p)),
            B("Understood. Can sales still get in touch to share details?"), v_consent(p, "phone")]

@family("unknown/b14_consent_no_orgtype", "unknown", kind="consent")
def _(p):
    return [B("What kind of business are you with?"),
            V(pick([f"We're in {p['city']}, I'd rather not say more about the company yet.", f"{p['city']} based. The business side, let's skip for now.",
                    f"Operating from {p['city']}. What we do exactly isn't important for this.", f"Mixed business in {p['city']}, hard to describe.",
                    f"Based in {p['city']}. We do a bit of everything.", f"{p['city']}, and I'll keep the rest vague for now."], p), cities=[p['city']]),
            bq("team", p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p), v_soon(p), bq("consent", p), v_consent(p)]

@family("brokerage/b14_consent_head_sales_no_authority", kind="consent", partial=(4, 5))
def _(p):
    role = pick(["head of sales", "sales head", "VP sales", "sales director", "head of business development", "senior sales manager"], p)
    sen = "executive" if role in ("VP sales", "sales director") else "manager"
    return [B("Who am I speaking with?"), V(f"I'm the {role} at {p['co']}, a {p['td']} in {p['city']}.", role=role, sen=sen, name=p['co'], typ=p['typ'], cities=[p['city']]),
            bq("team", p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("when", p), v_soon(p), bq("consent", p), v_consent(p), bq("who", p),
            V(pick(["Let's leave that for the call.", "We'll discuss that later.", "Good question, I'll explain on the call.", "Hmm, it's a bit complicated.",
                    "Not something I can answer here.", "That's for another day."], p))]

@family("channel_partner/b14_consent_check_with_partner", "channel_partner", kind="consent")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), v_manual(p), bq("who", p),
            V(pick(["Not sure, I have to check with my partner how we decide these things.", "Honestly I don't know who'd sign, I need to check.",
                    "Could be me, could be my partner. Not sure.", "I'd have to check internally.", "Unclear right now, we've never bought software.",
                    "Might be me, might be the other directors. I'll find out."], p)),
            v_soon(p), bq("consent", p), v_consent(p, "phone")]

@family("brokerage/b14_consent_topic_change", kind="consent")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p),
            V(pick(["Before that, how much does it cost per user?", "Wait, does it work on Android?", "Quick one: can I import my Excel?",
                    "Separate question, do you integrate with 99acres?", "Hold on, is there a free trial?", "Can it send WhatsApp messages automatically?"], p)),
            B("Yes, and sales can share the specifics. When would you want to start?"), v_soon(p), bq("consent", p), v_consent(p)]

@family("developer/b14_consent_vague_leads", "developer", kind="consent")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p),
            V(pick(["Depends on the campaign, some months huge, some months nothing.", "Honestly it's all over the place.", "Not sure, marketing handles that.",
                    "I'd rather not share lead numbers.", "It swings a lot, can't give an average.", "Good volume, no hard number."], p)),
            bq("tools", p), v_manual(p), bq("who", p), v_appr(p), v_soon(p), bq("consent", p), v_consent(p, "phone")]

@family("brokerage/b14_consent_uae_no_influence", kind="consent", uae=True, partial=(3, 5))
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("when", p), v_soon(p),
            bq("consent", p), v_consent(p, "phone"), bq("who", p),
            V(pick(["Depends on the deal size.", "Let me not get into that.", "Varies, honestly.", "I'd have to check.", "Hard to say.", "Not my call to share."], p))]

# == no consent, one dimension unknown / evasions ==
@family("brokerage/b14_rather_not_say_leads")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p),
            V(pick(["I'd rather not say.", "Prefer not to share that.", "Let's skip the numbers.", "Rather keep that private.", "I'll pass on that one.", "Not comfortable sharing volumes."], p)),
            bq("tools", p), v_manual(p), bq("who", p), v_appr(p), bq("when", p), v_later(p)]

@family("developer/b14_team_depends", "developer")
def _(p):
    return [bq("pain", p), v_org(p), bq("team", p),
            V(pick(["Depends, we hire for each launch.", "It depends on the project.", "Somewhere between 5 and 30, varies.", "Not sure, a mix of in-house and agencies.",
                    "Honestly depends on the week.", "Hard to say, contractors come and go."], p)),
            bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p)]

@family("brokerage/b14_decent_volume")
def _(p):
    return [bq("leads", p), V(pick(["Decent volume.", "A fair amount.", "Enough, I suppose.", "Quite a lot.", "Good numbers.", "Steady flow."], p)),
            B("And who are you with?"), v_org(p), bq("tools", p), v_manual(p), bq("team", p), v_ag(p), bq("when", p), v_soon(p)]

@family("other_real_estate/b14_missing_process", "other_real_estate")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("pain", p), v_pains_only(p), bq("tools", p),
            V(pick(["Let's not go there, it's a long story.", "A bit of this and that.", "Complicated, I'd rather show you later.", "Varies by team.",
                    "It changes all the time.", "Something our IT guy set up, not sure what."], p)), bq("who", p), v_appr(p)]

@family("brokerage/b14_missing_pain")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("pain", p),
            V(pick(["Just exploring, no specific issue.", "Can't think of one right now.", "Not sure there's a problem yet.", "Just curious what's out there.",
                    "Hmm, I'd need to ask the team.", "Nothing pressing I can name."], p)),
            bq("who", p), v_appr(p), bq("when", p), v_later(p)]

@family("developer/b14_topic_change_leads", "developer")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p),
            V(pick(["Can you show me the reports screen first?", "Does it handle channel partner payouts?", "What about data security?", "How long is onboarding?",
                    "Is there an inventory module?", "Can I see the mobile app?"], p)),
            B(BQ["demo"][p['g'] % 3]), V(pick(["Nice, looks clean.", "Okay, that's useful.", "Interesting layout.", "Right, I see.", "That's neat.", "Makes sense."], p)),
            bq("tools", p), v_manual(p)]

@family("brokerage/b14_ends_on_question", partial=(0, 1, 2, 3, 4, 5), precut=True)
def _(p):
    cut = [7, 5, 9, 7, 5, 9][p['k']]
    t = [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p)]
    return t[:cut] + [bq(["who", "tools", "when", "who", "tools", "when"][p['k']], p)]

@family("channel_partner/b14_role_no_authority", "channel_partner")
def _(p):
    role = pick(["operations manager", "team lead", "sales manager", "head of sales", "business head", "marketing manager"], p)
    sen = "executive" if role == "business head" else "manager"
    return [B("Who am I chatting with?"), V(f"{role.capitalize()} at {p['co']}, we're a {p['td']} in {p['city']}.", role=role, sen=sen, name=p['co'], typ=p['typ'], cities=[p['city']]),
            bq("team", p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("when", p), v_soon(p)]

@family("developer/b14_vp_marketing_no_authority", "developer")
def _(p):
    role = pick(["VP marketing", "CMO", "head of marketing", "digital marketing head", "marketing director", "growth head"], p)
    sen = "executive" if role in ("VP marketing", "CMO", "marketing director") else "manager"
    return [B("What's your role?"), V(f"I'm {role} for {p['co']}, {p['td']}, {p['city']}.", role=role, sen=sen, name=p['co'], typ=p['typ'], cities=[p['city']]),
            bq("leads", p), v_ld(p), bq("pain", p), v_pains_only(p), bq("who", p),
            V(pick(["Let's first see if it's any good.", "We'll get to that.", "One step at a time.", "Show me more first.", "Too early to talk about that.", "Park that for now."], p))]

@family("unknown/b14_pricing_only", "unknown", partial=(2, 3, 4, 5), precut=True)
def _(p):
    t = [B(None), V(pick(["How much is Leadrat per user?", "What's the pricing like?", "Is it priced per seat or flat?", "Do you have a monthly plan?",
                          "What's the cheapest plan?", "Any setup fee?"], p)),
         B("Pricing depends on team size. How many users would you need?"),
         V(pick(["Just want a ballpark first.", "Not sure yet, ballpark please.", "Let's keep that open.", "Depends on the price, frankly.", "No idea yet.", "Couldn't say."], p)),
         B("Sure. Plans start small and scale. What does your business do?"),
         V(pick(["Just comparing options for now.", "I'm only gathering prices.", "Mainly price shopping today.", "Just a quick look.", "Collecting quotes.", "Browsing."], p))]
    return t if p['k'] < 2 else t[:5]

@family("unknown/b14_integration_question", "unknown", partial=(2, 3, 4, 5), precut=True)
def _(p):
    t = [B(None), V(pick(["Does Leadrat integrate with Housing.com?", "Can it pull leads from Facebook forms?", "Is there a Zapier connection?",
                          "Can I connect my IVR?", "Does it sync with Google Calendar?", "Is there an API?"], p)),
         B("Yes, that's supported. Can I ask what kind of business you run?"),
         V(pick(["I'll tell you later, just checking features.", "Rather not say yet.", "Still figuring out if it fits.", "Just need the feature answer.",
                 "Doesn't matter for now.", "Let's stick to features."], p)),
         B("No problem. Anything else you want to see?"), V(pick(["Maybe the dashboard.", "The reports, maybe.", "Show me automations.", "Lead assignment.", "The inbox.", "Call logging."], p))]
    return t if p['k'] < 2 else t[:4]

@family("unknown/b14_mobile_app_question", "unknown", partial=(3, 4, 5), precut=True)
def _(p):
    t = [B(None), V(pick(["Is there an iOS app?", "Does the app work offline?", "Can agents log calls from their phones?",
                          "Does the app track location for site visits?", "Is the Android app free?", "Can I get push alerts for new leads?"], p)),
         B("Yes. Here's the mobile view. How many people would use it?"),
         V(pick(["Not sure, a few maybe.", "Some, depends.", "Can't say yet.", "A small number, or maybe more.", "Not decided.", "We'll see."], p)),
         B("Fair enough. Would you like to see how new leads get assigned?"),
         V(pick(["Sure, quickly.", "Go on.", "Okay.", "Yes, show me.", "Fine.", "Alright."], p))]
    return t if p['k'] < 3 else t[:5]

@family("brokerage/b14_not_sure_timeline")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p), bq("when", p),
            V(pick(["Not sure, have to check our cash flow.", "Depends on a lot of things.", "I don't know yet.", "Couldn't tell you right now.",
                    "Whenever it makes sense.", "Open-ended."], p)), bq("consent", p),
            V(pick(["Not now, I'll reach out.", "Let me think first.", "I'll come back to you.", "No calls yet please, I'll revert.", "Maybe later, I'll message.", "Hold off for now."], p))]

@family("developer/b14_depends_on_budget", "developer")
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p),
            V(pick(["Depends on the budget.", "Depends who owns the budget this year.", "It depends.", "Depends on the amount.", "Depends on the approval chain.", "It really depends."], p)),
            bq("when", p), V(pick(["Also depends.", "Same answer, it depends.", "Can't say.", "Unclear.", "Not decided.", "Let's see how it goes."], p))]

@family("developer/b14_uae_vague_leads", "developer", uae=True)
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p),
            V(pick(["A lot during launches.", "Hundreds, maybe thousands, depends.", "Can't give a number.", "It's seasonal.", "Plenty.", "Varies too much to say."], p)),
            bq("tools", p), v_manual(p), bq("who", p), v_appr(p)]

@family("brokerage/b14_leads_range_spans_bands")
def _(p):
    lo, hi = pick([(60, 150), (80, 200), (300, 700), (50, 120), (400, 900), (90, 250)], p)
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), V(f"Anywhere from {lo} to {hi}, it jumps around.", leads=(lo, hi)),
            bq("tools", p), v_manual(p), bq("who", p), v_appr(p)]

@family("brokerage/b14_agents_range")
def _(p):
    lo, hi = pick([(5, 10), (15, 25), (3, 8), (18, 30), (4, 12), (10, 22)], p)
    return [bq("team", p), v_org(p), V(f"Between {lo} and {hi} agents depending on the month."), bq("leads", p), v_ld(p),
            bq("tools", p), v_manual(p), bq("who", p), v_appr(p)]

@family("brokerage/b14_team_contradiction", partial=(3, 4, 5))
def _(p):
    a, b = p['ag'], p['ag'] + 9
    return [bq("team", p), v_org(p), V(f"We're {a} agents.", agents=a), bq("leads", p), v_ld(p),
            V(f"Actually my partner says {b}, and I still think {a}. We'll sort it out.", clear=["agents"]),
            bq("tools", p), v_manual(p), bq("who", p), v_appr(p)]

@family("developer/b14_early_exit", "developer", n=5, partial=(0, 1, 2, 3, 4), precut=True)
def _(p):
    return [bq("team", p), v_org(p), bq("team", p),
            V(pick(["Have to jump into a meeting, back later.", "Sorry, got a call, will come back.", "Need to run.", "Brb.", "Let me come back to this."], p))]

@family("unknown/b14_security_question", "unknown", partial=(2, 3, 4, 5), precut=True)
def _(p):
    t = [B(None), V(pick(["Where is the data hosted?", "Is the data encrypted?", "Can agents export contacts?", "Do you have role-based access?",
                          "What happens to our data if we leave?", "Are you GDPR compliant?"], p)),
         B("Good question. Data is encrypted and access is role based. Where are you based, if I may ask?"),
         V(pick([f"Property stuff in {p['city']}, that's all I'll say.", f"Real estate, {p['city']}. Details later.", f"We're in {p['city']}.",
                 f"{p['city']}-based. Let's leave it there.", f"Out of {p['city']}.", f"{p['city']}, mostly."], p), cities=[p['city']]),
         B("Thanks. Want to see the permissions screen?"), V(pick(["Yes please.", "Sure.", "Go ahead.", "Okay, show it.", "Alright.", "Please do."], p))]
    return t if p['k'] < 2 else t[:5]

@family("brokerage/b14_manager_evaluating_unclear")
def _(p):
    return [B("Who am I speaking with?"), V(f"Branch manager at {p['co']}, {p['td']}, {p['city']} office.", role="branch manager", sen="manager", name=p['co'], typ=p['typ'], cities=[p['city']]),
            bq("team", p), v_ag(p), bq("tools", p), v_manual(p), bq("who", p),
            V(pick(["Head office is involved somehow, not sure how.", "No idea how the approval works here.", "I think it goes through someone, not sure who.",
                    "Might need HO sign-off, might not.", "Unclear, first time we're buying software.", "I'll figure that out."], p))]

@family("unrelated/b14_student_research", "unrelated", partial=(3, 4, 5), precut=True)
def _(p):
    t = [B(None), V(pick(["I'm a student researching CRMs for a project.", "I work at a logistics firm, just curious about CRMs.", "Doing a college assignment on proptech, not in real estate myself.",
                          "I run a bakery, just exploring software.", "I'm a journalist writing about proptech, not a buyer.", "Just a software developer curious how this is built."], p), typ="unrelated"),
         B("Welcome! Happy to show you around. What would you like to see?"),
         V(pick(["The lead screen.", "Maybe the dashboard.", "Anything really.", "The automation bits.", "Just a general tour.", "Reports."], p)),
         B("Here's the dashboard. Anything specific?"), V(pick(["No, that's plenty.", "That's good, thanks.", "Enough for my notes.", "Cool, thanks.", "Got it.", "Nice, done."], p))]
    return t if p['k'] < 3 else t[:4]

# == controls: complete facts ==
@family("brokerage/b14_control_sales", kind="control", partial=())
def _(p):
    p['ag'] = max(p['ag'], 20) + p['k']; p['ld'] = max(p['ld'], 500) + 10 * p['k']
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p),
            bq("when", p), v_soon(p), bq("consent", p), v_consent(p)]

@family("developer/b14_control_sales", "developer", kind="control", partial=())
def _(p):
    p['ag'] = max(p['ag'], 20) + p['k']; p['ld'] = max(p['ld'], 500) + 5 * p['k']
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p),
            bq("when", p), v_soon(p), bq("consent", p), v_consent(p, "phone")]

@family("channel_partner/b14_control_sales", "channel_partner", kind="control", partial=(), uae=True)
def _(p):
    p['ag'] = 6 + p['k']; p['ld'] = 520 + 20 * p['k']
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p),
            v_soon(p), bq("consent", p), v_consent(p, "phone")]

@family("developer/b14_control_nurture", "developer", kind="control", partial=())
def _(p):
    p['ag'] = 7 + p['k']; p['ld'] = 110 + 15 * p['k']
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p),
            V(pick(["We use Salesforce but it can't auto-assign portal leads.", "We're on Zoho CRM, reporting is weak.", "HubSpot, but the WhatsApp side is missing.",
                    "Sell.Do today, the app is slow for agents.", "Zoho, but site visits aren't tracked.", "Salesforce, costly and nobody logs calls."], p),
              tools=[pick(["Salesforce", "Zoho CRM", "HubSpot", "Sell.Do", "Zoho CRM", "Salesforce"], p)], proc="unsatisfied_crm",
              pains=[pick(["portal leads not auto-assigned", "weak reporting", "no WhatsApp integration", "slow mobile app", "site visits not tracked", "calls not logged"], p)]),
            bq("who", p), V(pick(["I'm evaluating for our director.", "My boss decides, I'm shortlisting.", "I'll recommend to the promoters.",
                                  "Evaluating on behalf of the CEO.", "The MD asked me to look.", "I'm building the case for my GM."], p), inf="sponsored_evaluator"),
            bq("when", p), v_later(p)]

@family("brokerage/b14_control_nurture", kind="control", partial=())
def _(p):
    p['ag'] = 25 + p['k']; p['ld'] = 600 + 25 * p['k']
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p),
            bq("when", p), v_soon(p), bq("consent", p),
            V(pick(["No calls please, I'll sign up myself.", "Not yet, I'll try it on my own first.", "I'll reach out when ready, no follow-up for now.",
                    "Skip the sales call for now.", "Let me explore alone first.", "I'll contact you, not the other way round."], p))]

@family("channel_partner/b14_control_nurture", "channel_partner", kind="control", partial=())
def _(p):
    p['ag'] = 10 + p['k']; p['ld'] = 150 + 20 * p['k']
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p),
            V(pick(["I'm the sales manager, my director signs.", "Team lead here, I report to the owner who decides.", "Ops head, evaluating for the partners.",
                    "I'm shortlisting, the founder decides.", "Manager here, owner approves.", "I'll present it to my boss for approval."], p),
              role=pick(["sales manager", "team lead", "ops head", None, "manager", None], p),
              sen=pick(["manager", "manager", "manager", None, "manager", None], p), inf="sponsored_evaluator"),
            bq("when", p), v_later(p)]

@family("unrelated/b14_control_close", "unrelated", kind="control", partial=())
def _(p):
    return [B(None), V(pick([f"We run a {x} business in {p['city']}, not real estate." for x in ["logistics", "catering", "garments", "car rental", "coaching", "printing"]], p),
                       typ="unrelated", cities=[p['city']]),
            bq("team", p), V(f"Just {3 + p['k'] % 3} people in {p['city']}.", agents=3 + p['k'] % 3), bq("leads", p),
            V(f"Maybe {10 + p['k']} enquiries a month for our {p['city']} shop.", leads=(10 + p['k'], 10 + p['k'])),
            bq("tools", p), V(pick(["Zoho works fine for us, no problems.", "HubSpot free does the job, no issues.", "Our CRM is fine, no complaints.",
                                    "Freshsales, happy with it, nothing to fix.", "Pipedrive, all good, no pain points.", "Zoho Bigin, it's fine, no problems."], p),
                               proc="satisfied_crm", pains=[]),
            bq("who", p), V(pick(["I'm the owner, I decide.", "My call, I own it.", "I decide, it's my firm.", "Owner here, I sign.", "It's mine to decide as owner.", "I sign, I'm the owner."], p),
                            inf="approver", role="owner", sen="owner"),
            bq("when", p), V(pick(["Not interested in switching, thanks.", "No follow-up needed, we're done.", "Please don't contact me.", "No thanks, not switching.", "We'll pass on this.", "Not for us, no follow-up."], p), nxt="declined")]

@family("brokerage/b14_control_declined", kind="control", partial=())
def _(p):
    return [bq("team", p), v_org(p), v_ag(p), bq("leads", p), v_ld(p), bq("tools", p), v_manual(p), bq("who", p), v_appr(p), bq("consent", p),
            V(pick(["No, please don't call me. Not buying.", "Not interested, no follow-up.", "Decline, we're staying with what we have.", "No thanks, please don't contact us.",
                    "I don't want any follow-up.", "We're not going ahead, thanks."], p), nxt="declined")]

@family("other_real_estate/b14_control_small_close", "other_real_estate", kind="control", partial=())
def _(p):
    return [bq("team", p), v_org(p), V(f"Only {2 + p['k'] % 3} of us at {p['co']}.", agents=2 + p['k'] % 3), bq("leads", p),
            V(f"{15 + p['k']} leads in a month, max, for {p['co']}.", leads=(15 + p['k'], 15 + p['k'])),
            bq("tools", p), V(pick(["We use a CRM already and we're happy, no issues.", "Our current CRM is fine, nothing broken.", "Zoho handles it well, no problems.",
                                    "No issues with our CRM at all.", "We're satisfied with HubSpot, no pain.", "The CRM we have works, no complaints."], p),
                               proc="satisfied_crm", pains=[]),
            bq("who", p), V(pick(["I'm an employee, no say in tools.", "I don't decide anything here.", "No say on purchases.", "Not my decision at all.", "I have no role in buying.", "I'm just staff, no say."], p), inf="none"),
            bq("when", p), v_later(p)]

# ---------- generate ----------
for name, typ, kind, n, partials, uae, precut, fn in FAM:
    for j in range(n):
        p = P(typ, uae, j)
        turns = fn(p)
        op = B(OPENERS[p['g'] % 30])
        turns = [op] + (turns[1:] if turns[0][1] is None else turns)
        partial = j in partials
        if partial and not precut:
            if kind == "consent":
                ci = max(i for i, t in enumerate(turns) if t[2].get('consent'))
                if ci + 1 < len(turns): turns = turns[:ci + 1]
                else: partial = False
            else:
                turns = turns[:max(4, len(turns) - 2 - 2 * (j % 3))]
        E(name, turns[:16], partial)

rows = rows[:250]
with open(OUT, "w", encoding="utf-8") as fh:
    for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(len(rows), "rows ->", OUT, "families", len({r['family'] for r in rows}))
