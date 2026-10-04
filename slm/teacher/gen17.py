"""Batch 17 (English): pain-point counts, tooling/process, geography and lead sources.
Each example is built from segments (intro, size, tools, pains, sources, authority, close); a segment is one
Beacon question plus one visitor answer and the facts that answer states. Partial transcripts keep the first
k segments and label only their facts. Visitor k sits at turn 2k."""
import json, random
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = RAW / "batch_17.jsonl"
R = random.Random(1717)
SEEN = set()
for f in RAW.glob("batch_*.jsonl"):
    if f.name == OUT.name: continue
    for line in f.read_text("utf-8").splitlines():
        if line.strip():
            for t in json.loads(line)["transcript"]:
                if t["speaker"] == "visitor": SEEN.add(t["text"].strip().lower())


SCREENS = ["Leads list", "follow-up timeline", "Sources report", "site visit calendar", "agent leaderboard", "WhatsApp inbox", "inventory grid", "reports page"]
TAILS = ["By the way, the {s} looked neat.", "That {s} you showed is interesting.", "I liked the {s}, for what it's worth.",
         "The {s} is the bit I'd show my team.", "Nice {s}, by the way.", "Thanks for showing the {s}."]


def uniq(gen):
    for n in range(300):
        text, facts = gen()
        if n > 15: text = text + " " + pick(TAILS).format(s=pick(SCREENS))
        if text.strip().lower() not in SEEN:
            SEEN.add(text.strip().lower()); return text, facts
    raise RuntimeError("could not make a unique line: " + text)


pick = R.choice

OPENERS = [
 "Hi, I'm Beacon, Leadrat's demo assistant. What does your business do?",
 "Hello! Beacon here. Tell me a little about your company and I'll tailor the tour.",
 "Welcome to Leadrat. I'm Beacon. Who am I chatting with today?",
 "Hey there, Beacon from Leadrat. What kind of real estate work are you in?",
 "Good to have you here. I'm Beacon. What should I know about your team before we start?",
 "Hi! I'm Beacon, and I can show you Leadrat live, no forms. What's your line of business?",
 "Hello, this is Beacon. Brokerage, developer, channel partner, something else?",
 "Hey! Beacon here. What brings you to Leadrat today?",
 "Welcome. I'm Beacon, your guide for this demo. Tell me about your firm?",
 "Hi, Beacon from Leadrat here. Where would you like to start, or shall I ask a couple of questions first?",
 "Hello and welcome! I'm Beacon. What does a normal day look like for your sales team?",
 "Hi there. I'm Beacon. Give me a quick picture of your business and I'll show the relevant screens.",
 "Hey, I'm Beacon. Happy to walk you through the CRM. Who are you with?",
 "Welcome! Beacon here, Leadrat's live demo. What are you hoping to fix?",
 "Hi! This is Beacon. Mind telling me about your company first?",
 "Hello, I'm Beacon. I'll keep this short and useful. What's your role and company?",
 "Hey there! Beacon at your service. What kind of properties do you deal in?",
 "Hi, I'm Beacon. Before the screens, a quick intro: what does your firm do?",
 "Good day! I'm Beacon from Leadrat. What made you click on the demo?",
 "Hello! Beacon here. Tell me who you are and what you sell, and we'll go from there.",
 "Hi, Beacon from Leadrat. Are you looking for a CRM for a sales team?",
 "Welcome aboard. I'm Beacon. What's your business, in a sentence or two?",
 "Hey, I'm Beacon, the demo guide. What would make the next ten minutes worth it?",
 "Hi there, I'm Beacon. I can show leads, listings and reports. First, what do you do?",
 "Hello! I'm Beacon. Which company are you from, and what's your part in it?",
 "Hi! Beacon here. How can I help you evaluate Leadrat today?",
 "Welcome to the Leadrat demo. I'm Beacon. What's your setup at the moment?",
 "Hey! I'm Beacon. Tell me about the team you'd be buying this for?",
 "Hello, Beacon here from Leadrat. Let's start with you: what's the business?",
 "Hi, I'm Beacon. No sign-up needed. What kind of real estate firm are you with?",
]
OP_USE = [0] * len(OPENERS)

Q = {
 "size": ["How big is the sales team, and roughly how many enquiries come in a month?", "How many agents do you have, and what's the monthly lead volume?",
          "Quick sizing question: headcount on sales and leads per month?", "Roughly how many people sell for you, and how many leads land each month?",
          "What's the team size, and about how many enquiries a month?"],
 "tools": ["What are you using to manage leads right now?", "How do you track leads today?", "Which tools does the team work in at the moment?",
           "Where do your leads live today, a CRM or something else?", "Here is the Leads list with owner and status columns. How do you manage this today?"],
 "pain": ["What's the biggest headache in that setup?", "What's not working for you today?", "Where does it hurt most, day to day?",
          "Here's the follow-up timeline view. What problems are you trying to fix?", "What made you start looking at a new CRM?"],
 "pain2": ["Anything else slowing the team down?", "Is there anything else on the list?", "Got it. Any other problems I should know about?", "Makes sense. What else?"],
 "src": ["Where do most of your leads come from?", "Which channels bring in enquiries?", "Here's the Sources report. What are your main lead channels?",
         "What are the main lead sources for you?"],
 "auth": ["Who makes the call on buying software like this?", "If this looks right, who signs off?", "Are you the decision maker here, or is someone else involved?",
          "Who else would be involved in choosing a CRM?"],
 "close": ["Would you like our sales team to follow up with you?", "Shall I have someone from sales get in touch?",
           "Want a proper follow-up from our team? If so, what's the best email or number?",
           "Happy to connect you with sales. Interested, and how soon are you looking to move?", "Before you go, should sales reach out, and what's your timeline?"],
}

ROLES = {"owner": ["founder", "co-founder", "owner", "managing partner", "proprietor"],
         "executive": ["CEO", "director", "COO", "VP of sales", "head of sales"],
         "manager": ["sales manager", "team lead", "CRM manager", "operations manager", "marketing manager"],
         "individual_contributor": ["sales executive", "relationship manager", "senior agent"]}
PRE = ["Skyline", "Harbourview", "Tulsi", "Amber", "Crescent", "Banyan", "Marigold", "Redstone", "Oakwood", "Sapphire", "Lotus", "Keystone",
       "Meridian", "Azure", "Vanshi", "Northstar", "Silverleaf", "Greenfield", "Palmera", "Coral", "Vistara", "Shivalik", "Riverbend", "Emerald",
       "Horizon", "Saffron", "Indigo", "Pinnacle", "Neelkanth", "Dunescape", "Falcon", "Desert Rose", "Kaveri", "Godavari", "Aravali", "Nilgiri",
       "Monsoon", "Jasmine", "Orchid", "Cedar", "Brightkey", "Anchorline", "Tamarind", "Sandstone", "Bluewater"]
SUF = {"brokerage": ["Realty", "Properties", "Realtors", "Estates", "Homes"], "developer": ["Developers", "Infra", "Buildcon", "Constructions", "Landmarks"],
       "channel_partner": ["Advisors", "Property Partners", "Consultants", "Realty Partners", "Sales Co"]}
DESC = {"brokerage": ["resale and rentals brokerage", "boutique luxury brokerage", "commercial leasing agency", "secondary-market agency", "residential brokerage"],
        "developer": ["residential developer", "mid-size builder with two towers under construction", "plotted development company", "developer doing mid-income housing", "villa developer"],
        "channel_partner": ["channel partner firm selling for developers", "CP firm handling new launches", "mandate-sales channel partner", "channel partner agency for big builders", "project marketing and CP outfit"]}
IN_C = ["Mumbai", "Pune", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Kochi", "Lucknow", "Indore", "Chandigarh", "Noida",
        "Gurgaon", "Thane", "Navi Mumbai", "Surat", "Nagpur", "Coimbatore", "Visakhapatnam"]
AE_C = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah"]

PAINS = [
 ("leads not followed up on time", ["half our leads sit for a day before anyone calls", "follow-ups slip and buyers get a call two days late", "we're slow to call new enquiries back"]),
 ("duplicate leads", ["the same buyer shows up three times from different portals", "duplicates everywhere, two agents end up calling one person", "we keep getting duplicate enquiries and nobody merges them"]),
 ("no visibility into agent activity", ["I have no idea what my agents did all day", "there's zero visibility into who called whom", "I can't see which agent is actually working the leads"]),
 ("leads lost when agents leave", ["when an agent quits, their leads walk out with them", "every time someone resigns we lose their contacts", "leads vanish when an agent leaves the company"]),
 ("site visits not tracked", ["site visits aren't tracked anywhere", "we never know which visits actually happened", "site visit scheduling is chaos"]),
 ("no lead source ROI tracking", ["I can't tell which channel is worth the money", "I have no clue which ad spend brings actual bookings", "we can't measure ROI by lead source"]),
 ("manual lead distribution", ["someone assigns leads by hand every morning", "lead distribution is manual and unfair", "I spend an hour a day just handing out leads"]),
 ("WhatsApp chats scattered across phones", ["client chats are spread over twenty personal phones", "all the conversations are stuck in agents' personal WhatsApp", "chat history is scattered across everyone's phones"]),
 ("inventory status out of date", ["the inventory sheet is always out of date", "we once sold a unit that was already blocked", "nobody knows which units are still available"]),
 ("reports take hours to compile", ["the weekly report takes me half a day to build", "making MIS reports eats my Saturday", "reporting is all copy-paste and takes hours"]),
 ("portal leads copied by hand", ["someone copies portal leads into the sheet by hand", "portal enquiries get typed in manually", "we download portal leads and paste them in every day"]),
 ("missed callbacks", ["callbacks get forgotten all the time", "buyers ask us to call back and nobody does", "promised callbacks just fall through"]),
]
CRM_PAINS = [
 ("current CRM hard to use", ["{crm} is so clunky that the team avoids it", "nobody wants to open {crm}, it's too complicated", "{crm} takes ten clicks to log one call"]),
 ("current CRM lacks portal integration", ["{crm} doesn't pull in portal leads at all", "we can't connect our portals to {crm}", "{crm} has no proper portal integration"]),
 ("current CRM too expensive", ["{crm} licences cost us a fortune", "we pay way too much per seat for {crm}", "the {crm} bill keeps going up every year"]),
 ("current CRM has no usable mobile app", ["{crm} barely works on a phone", "agents in the field can't use {crm} on mobile", "the {crm} mobile experience is useless"]),
]
UNREL = ["parking near our office is a nightmare", "the market has been slow since the monsoon", "our office rent went up again", "interest rates are scaring buyers",
         "our AC has been broken for a week", "traffic to the sites is terrible", "cement prices are killing our margins", "finding good office staff is impossible"]

SRC = {"99acres": ["99acres"], "MagicBricks": ["MagicBricks", "Magicbricks"], "Housing.com": ["Housing.com", "Housing"], "Bayut": ["Bayut"],
       "Property Finder": ["Property Finder", "PropertyFinder"], "Dubizzle": ["Dubizzle"], "Meta ads": ["Facebook and Instagram ads", "Meta ads", "Insta and FB campaigns"],
       "Google ads": ["Google ads", "Google search ads"], "referrals": ["referrals", "word of mouth from old clients", "referrals from past buyers"],
       "walk-ins": ["walk-ins", "people walking into the office", "walk-ins at the site office"], "hoardings": ["hoardings", "billboards on the highway", "hoardings near the project"],
       "WhatsApp campaigns": ["WhatsApp broadcast campaigns", "WhatsApp campaigns", "bulk WhatsApp blasts"], "property expos": ["property expos", "exhibitions and expos", "NRI property shows"]}
SRCSETS = {"portals_in": ["99acres", "MagicBricks", "Housing.com"], "portals_ae": ["Bayut", "Property Finder", "Dubizzle"], "ads": ["Meta ads", "Google ads"],
           "offline": ["referrals", "walk-ins", "hoardings"], "wa": ["WhatsApp campaigns", "referrals", "Meta ads"], "events": ["property expos", "referrals", "Google ads"],
           "mixed": ["99acres", "Meta ads", "referrals", "walk-ins", "Housing.com", "Google ads"]}


def join(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def cap(s):
    return s[0].upper() + s[1:]


def seg_intro(p):
    def g():
        sen = p["sen"]; role = pick(ROLES[sen]); org = p["org"]
        name = f"{pick(PRE)} {pick(SUF[org])}" if R.random() < 0.7 else None
        desc = pick(DESC[org]); geo = p["geo"]; f = {"role": role, "sen": sen, "type": org}
        if name: f["name"] = name
        if geo == "in_city":
            c = pick(IN_C); gp = pick([f"based in {c}", f"working mostly around {c}", f"out of {c}", f"in {c}"]); f.update(countries=["India"], cities=[c])
        elif geo == "ae_city":
            c = pick(AE_C); gp = pick([f"in {c}", f"based out of {c}", f"working in {c}"]); f.update(countries=["UAE"], cities=[c])
        elif geo == "multi":
            a, b = pick(IN_C), pick(AE_C); gp = pick([f"with offices in {a} and {b}", f"selling in {a} and also in {b}", f"split between {a} and {b}"]); f.update(countries=["India", "UAE"], cities=[a, b])
        elif geo == "several":
            cs = R.sample(IN_C, 3); gp = pick([f"covering {join(cs)}", f"active in {join(cs)}", f"with teams in {join(cs)}"]); f.update(countries=["India"], cities=cs)
        elif geo == "country":
            k = pick(["India", "UAE"]); w = "the UAE" if k == "UAE" else "India"
            gp = pick([f"working across {w}", f"operating all over {w}"]); f.update(countries=[k])
        elif geo == "nri":
            c = pick(["Kochi", "Thiruvananthapuram", "Kozhikode", "Mangaluru", "Hyderabad", "Chandigarh"]); gp = f"based in {c}"; f.update(countries=["India"], cities=[c])
        else:
            gp = ""
        if name:
            t = pick(["I'm the {r} at {n}", "{n} here, I'm the {r}", "I'm {r} with {n}", "I work as {r} at {n}"]).format(r=role, n=name) + f", a {desc}"
        else:
            t = pick(["I'm the {r} at a {d}", "I'm {r} of a small {d}", "I'm working as {r} for a {d}"]).format(r=role, d=desc)
        t = (t + (" " + gp if gp else "")).strip()
        return pick(["Hi, ", "Hello. ", "Hey, ", "", "Hi there. "]) + t + pick([".", ". Just exploring options.", ". We're looking at CRMs.", ". Curious what you've got."]), f
    return "intro", g


def src_text(p):
    m = p["src"]
    if m == "unknown":
        return pick(["No idea where the leads come from, marketing handles that.", "Honestly I don't know the sources, someone else runs that.",
                     "Not sure about the sources, I never looked.", "Where they come from? No clue, to be honest."]), {}
    labs = R.sample(SRCSETS[m], R.randint(1, min(3, len(SRCSETS[m]))))
    words = join([pick(SRC[x]) for x in labs])
    t = pick([f"Mostly {words}.", f"Leads come through {words}.", f"{cap(words)}, mainly.", f"Our enquiries are from {words}."])
    if p["geo"] == "nri":
        t += " " + pick(["A lot of our buyers are NRIs sitting in Dubai.", "Many buyers are NRIs in the Gulf and the US.", "Half the buyers are NRIs from London and Singapore, but we only sell locally."])
    return t, {"src": labs}


def seg_size(p, with_src=False):
    def g():
        out = p["out"]; f = {}
        if out == "handoff": a = R.randint(20, 70) if p["pain"] == "0" else R.randint(8, 60)
        elif out == "close_low": a = R.randint(1, 4)
        else: a = R.randint(3, 45)
        if out == "handoff" and p["pain"] == "0": l = R.choice([600, 750, 900, 1200, 1500, 2000])
        elif out == "close_low": l = R.choice([15, 20, 30, 40, 50, 60])
        else: l = R.choice([80, 120, 150, 200, 250, 300, 350, 400, 450, 500, 700, 800, 1000, 1800])
        vague = out == "review" and R.random() < 0.5
        if out not in ("handoff", "close_low") and R.random() < 0.12:
            lo = pick([4, 5]); at = f"somewhere between {lo} and {lo + R.randint(4, 8)} agents"
        else:
            at = pick([f"{a} agents", f"a team of {a}", f"{a} people on sales", f"{a} salespeople"]); f["agents"] = a
        if vague:
            lt = pick(["a lot of leads, never counted properly", "loads of enquiries, I honestly don't know the number", "plenty of leads, but no idea of the exact count"])
        elif R.random() < 0.3 and l >= 150:
            lo, hi = l - 50, l + 50
            if ((lo >= 100) == (hi >= 100) and (lo >= 500) == (hi >= 500)) or out == "review":
                lt = f"{lo} to {hi} leads a month"; f.update(lmin=lo, lmax=hi)
            else:
                lt = f"about {l} leads a month"; f.update(lmin=l, lmax=l)
        else:
            lt = pick([f"about {l} leads a month", f"roughly {l} enquiries monthly", f"close to {l} leads every month", f"around {l} a month"]); f.update(lmin=l, lmax=l)
        t = pick(["{A}, and {l}.", "We're {a}. {L}.", "{A}; {l}, give or take.", "Right now {a}, handling {l}."]).format(a=at, A=cap(at), l=lt, L=cap(lt))
        if with_src:
            st, sf = src_text(p); t += " " + st; f.update(sf)
        return t, f
    return "size", g


def tools_of(p):
    m = p["tool"]
    if m == "excel": return ["Excel"], "manual"
    if m == "sheets_wa": return ["Google Sheets", "WhatsApp"], "manual"
    if m == "paper": return ["paper registers"], "manual"
    if m == "wa": return ["WhatsApp"], "manual"
    if m == "mixed_manual": return ["Google Sheets", "WhatsApp", "paper registers"], "manual"
    crm = p["crm"].replace("an in-house CRM", "in-house CRM")
    if m.startswith("unsat_"): return [crm], "unsatisfied_crm"
    if m.startswith("mixunsat_"): return [crm, "Excel"], "unsatisfied_crm"
    return [crm], "satisfied_crm"


def seg_tools(p):
    def g():
        tools, proc = tools_of(p); m = p["tool"]; y = R.randint(2, 9); f = {"tools": tools}
        if proc == "manual":
            f["proc"] = "manual"
            t = {"excel": [f"Everything is in Excel, one big file with {y} tabs.", f"Excel sheets, we've done it that way for {y} years.", f"Just an Excel workbook that {pick(['I', 'my assistant', 'our admin'])} maintains."],
                 "sheets_wa": [f"A shared Google Sheet plus WhatsApp groups, about {y} groups by project.", "Google Sheets for the list and WhatsApp for talking to clients.", f"We use Google Sheets and WhatsApp, nothing fancy, for {y} years now."],
                 "paper": [f"Honestly, paper registers at the site office. {y} thick ledgers.", "Registers. Pen and paper, one book per project.", f"The old-school way, paper registers kept at the front desk for {y} years."],
                 "wa": ["Only WhatsApp. Every agent keeps their own chats.", f"We run the whole thing on WhatsApp, {y} groups and personal chats.", f"WhatsApp and that's it, for {y} years."],
                 "mixed_manual": [f"A mix: Google Sheets, WhatsApp, and paper registers at the {pick(['site', 'office'])}.", "Sheets for the lead list, WhatsApp for chats, and registers for walk-ins."]}[m]
            return pick(t), f
        c = p["crm"]
        if proc == "satisfied_crm":
            f["proc"] = "satisfied_crm"
            return pick([f"We're on {c} and honestly it works well for us.", f"{cap(c)}, been using it {y} years, the team is happy with it.",
                         f"We use {c}. No complaints, it does what we need.", f"{cap(c)}, and I'd say we're quite satisfied with it."]), f
        extra = " and a couple of Excel sheets for inventory" if m.startswith("mixunsat_") else ""
        return pick([f"We use {c}{extra}.", f"{cap(c)}{extra}, for about {y} years.", f"Currently {c}{extra}.", f"The team is on {c}{extra} right now."]), f
    return "tools", g


def pain_items(p):
    n = {"0": 0, "1": 1, "2": 2, "3": 3, "split": 2, "repeat": 1, "unrel": 1}[p["pain"]]
    items = []
    if p["tool"].startswith(("unsat_", "mixunsat_")) and n:
        crm = "our in-house CRM" if "in-house" in p["crm"] else p["crm"]
        lab, ph = pick(CRM_PAINS); items.append((lab, pick(ph).format(crm=crm)))
    for lab, ph in R.sample(PAINS, 4):
        if len(items) >= n: break
        items.append((lab, pick(ph)))
    return items


def seg_pain(p, items, part):
    def g():
        mode = p["pain"]
        if mode == "0":
            base = pick(["Honestly, no real problems. The setup works.", "Nothing major, to be honest. We're fine as we are.",
                         "No real pain points, it all runs smoothly.", "I can't think of any problem, things are okay."])
            if R.random() < 0.6: base += " My only gripe is that " + pick(UNREL) + ", but that's not a software thing."
            return base, {"pain": []}
        if mode == "split" and part == 1:
            return pick(["The main one: ", "First, ", "Biggest issue is that ", "Okay, so "]) + items[0][1] + ".", {"pain": [items[0][0]]}
        if mode == "split" and part == 2:
            return pick(["Also, ", "Oh, and ", "Another thing: ", "On top of that, "]) + items[1][1] + ".", {"pain": [items[1][0]]}
        if mode == "repeat" and part == 2:
            return pick(["Really it's the same thing I said, that's the one that hurts.", "Nothing new, just that first problem again, it happens every single week.",
                         "Mainly what I mentioned already. It keeps coming back.", "Same issue as before, honestly. It's the only one but it's a big one."]) + \
                pick(["", " Every day.", " It drives me mad.", " Ask any of my agents."]), {"pain": [items[0][0]]}
        ph = [x[1] for x in items]
        body = ph[0] if len(ph) == 1 else "; ".join(ph[:-1]) + ("; and " if len(ph) > 2 else " and ") + ph[-1]
        t = pick(["Well, ", "Honestly, ", "Where do I start. ", "Simple: ", "For us, "]) + body + "."
        if mode == "unrel": t += " Also, unrelated, but " + pick(UNREL) + "."
        return t, {"pain": [x[0] for x in items]}
    return ("pain2" if part == 2 else "pain"), g


def seg_auth(p):
    def g():
        i = p["inf"]
        t = {"approver": ["I sign off on software myself.", "It's my decision, I hold the budget.", "Final call is mine.", "I can approve this on my own."],
             "sponsored_evaluator": [f"My {pick(['MD', 'boss', 'director', 'founder'])} decides; I'm shortlisting for them.", f"I'm evaluating for our {pick(['CEO', 'partners', 'MD'])}, they sign.", "I do the research, my director gives the yes."],
             "none": ["I don't get a say in this, just looking around.", "Not my call at all, I was curious.", "I have no role in buying tools, honestly."]}[i]
        return pick(t) + pick(["", " That's how it works here.", " Just so you know.", " Always has been."]), {"inf": i}
    return "auth", g


def seg_close(p):
    def g():
        o = p["out"]; nm = pick(["Ravi", "Sana", "Arjun", "Meher", "Kabir", "Nisha", "Farhan", "Leela", "Omar", "Tanvi", "Yusuf", "Pooja", "Rohan", "Aisha", "Dev"])
        uae = p["geo"] == "ae_city" or (p["geo"] in ("multi", "country") and R.random() < 0.5)
        phone = f"+971 50 000 7{R.randint(0, 999):03d}" if uae else f"+91 90000 7{R.randint(0, 9999):04d}"
        email = f"{nm.lower()}{R.randint(1, 99)}@{pick(PRE).lower().replace(' ', '')}.example.com"
        which = pick(["email", "phone", "both"]); ct = {"cname": nm}
        if which in ("email", "both"): ct["email"] = email
        if which in ("phone", "both"): ct["phone"] = phone
        cs = {"email": f"email me at {email}", "phone": f"call me on {phone}", "both": f"{email} or {phone}"}[which]
        if o == "handoff":
            return pick([f"Yes, have someone reach out this week. I'm {nm}, {cs}.", f"Sure, we want to decide within the month. {nm} here, {cs}.",
                         f"Please do, we're keen to switch soon. {cap(cs)}, ask for {nm}.", f"Yes please, in the next couple of weeks ideally. {nm}, {cs}."]), dict(nxt="within_30_days", consent=True, **ct)
        if o == "nurture_noconsent":
            return pick(["We want to pick something this month, but no calls please, I'll explore on my own.", "Timeline is the next few weeks, but I'd rather not be contacted yet.",
                         "We'll decide within 30 days, just don't have sales call me, I'll reach out."]), dict(nxt="within_30_days")
        if o == "nurture_later":
            return pick(["Not right now, maybe next quarter.", "Probably after the festive season, not before.", "We'll look again in a few months.", "Later this year, not now."]), dict(nxt="later")
        if o == "nurture_later_consent":
            return pick([f"Sure, sales can contact me, but we'll only move in two or three months. {cap(cs)}.", f"Okay, {cs}, though realistically we'd start next quarter. I'm {nm}."]), dict(nxt="later", consent=True, **ct)
        if o == "close_declined":
            return pick(["No, please don't contact me. I was just curious.", "No follow-ups please, not interested.", "Please don't have anyone call, we're not buying."]), dict(nxt="declined")
        if o == "close_low":
            return pick(["Maybe someday, not now. We're tiny.", "Not anytime soon, we're too small for this.", "Later maybe, no rush."]), dict(nxt="later")
        return pick([f"Yes, this month if possible. {cap(cs)}.", f"Sure, reach out soon, {cs}. I'm {nm}."]), dict(nxt="within_30_days", consent=True, **ct)
    return "close", g


PATH = {"role": "role", "sen": "seniority", "name": "organisation.name", "type": "organisation.type", "agents": "organisation.agents",
        "tools": "current_tooling", "proc": "process", "countries": "geography", "cities": "geography", "lmin": "monthly_leads",
        "lmax": "monthly_leads", "src": "lead_sources", "inf": "influence", "nxt": "next_step", "consent": "consent",
        "cname": "contact", "email": "contact", "phone": "contact"}


def build(idx, p, partial, opener):
    items = pain_items(p)
    split = p["pain"] in ("split", "repeat")
    segs = [seg_intro(p), seg_size(p, with_src=split), seg_tools(p), seg_pain(p, items, 1)]
    segs.append(seg_pain(p, items, 2) if split else ("src", lambda: src_text(p)))
    if p["out"] != "review" or R.random() < 0.3: segs.append(seg_auth(p))
    segs.append(seg_close(p))
    if partial:
        segs = segs[:R.randint(2, min(5, len(segs) - 1))]
    turns = [opener]; F = {}; ev = {}; pains = []
    unsat = p["tool"].startswith(("unsat_", "mixunsat_"))
    for k, (qk, gen) in enumerate(segs, 1):
        text, f = uniq(gen)
        if k > 1: turns.append(pick(Q[qk]))
        turns.append(text); tid = 2 * k
        for key, val in f.items():
            if key == "pain":
                for x in val:
                    if x not in pains: pains.append(x)
                F["pain"] = pains; ev.setdefault("pain_points", []).append(tid)
                if unsat and val and "tools" in F:
                    F["proc"] = "unsatisfied_crm"; ev["process"] = sorted(set(ev.get("process", []) + ev["current_tooling"] + [tid]))
                continue
            F[key] = val
            if tid not in ev.setdefault(PATH[key], []): ev[PATH[key]].append(tid)
    lab = {"role": F.get("role"), "seniority": F.get("sen", "unknown"),
           "organisation": {"name": F.get("name"), "type": F.get("type", "unknown"), "agents": F.get("agents")},
           "pain_points": F.get("pain"), "current_tooling": F.get("tools"), "process": F.get("proc", "unknown"),
           "geography": {"countries": F.get("countries"), "cities": F.get("cities")},
           "monthly_leads": {"min": F.get("lmin"), "max": F.get("lmax")}, "lead_sources": F.get("src"),
           "influence": F.get("inf", "unknown"), "next_step": F.get("nxt", "unknown"), "consent": F.get("consent", False),
           "contact": {"name": F.get("cname"), "email": F.get("email"), "phone": F.get("phone")}, "evidence": ev}
    tr = [{"turn_id": i + 1, "speaker": "beacon" if i % 2 == 0 else "visitor", "text": t} for i, t in enumerate(turns)]
    return {"id": f"b17-{idx:03d}", "family": f"{p['org']}/b17_{p['scen']}", "language": "en", "partial": partial, "transcript": tr, "label": lab}


# (org, scenario, geography mode, tooling mode, pain mode, source mode)
FAM = [
 ("brokerage", "excel_two_pains_portals", "in_city", "excel", "2", "portals_in"),
 ("brokerage", "sheets_wa_three_pains", "in_city", "sheets_wa", "3", "mixed"),
 ("brokerage", "dubai_zoho_unhappy", "ae_city", "unsat_Zoho CRM", "2", "portals_ae"),
 ("brokerage", "happy_salesforce_no_pains", "several", "sat_Salesforce", "0", "portals_in"),
 ("brokerage", "wa_only_split_pains", "in_city", "wa", "split", "wa"),
 ("brokerage", "india_uae_leadsquared", "multi", "unsat_LeadSquared", "split", "mixed"),
 ("brokerage", "paper_register_walkins", "in_city", "paper", "1", "offline"),
 ("brokerage", "repeat_pain_excel", "in_city", "excel", "repeat", "portals_in"),
 ("brokerage", "unrelated_gripe_sheets", "in_city", "sheets_wa", "unrel", "ads"),
 ("brokerage", "no_location_mixed_tools", "none", "mixed_manual", "2", "mixed"),
 ("brokerage", "uae_countrywide_satisfied", "country", "sat_Zoho CRM", "0", "portals_ae"),
 ("brokerage", "nri_resale_sheets", "nri", "sheets_wa", "2", "portals_in"),
 ("brokerage", "inhouse_crm_three_pains", "in_city", "unsat_an in-house CRM", "3", "portals_in"),
 ("brokerage", "unknown_sources_excel", "in_city", "excel", "1", "unknown"),
 ("brokerage", "sharjah_wa_campaigns", "ae_city", "wa", "2", "wa"),
 ("brokerage", "salesforce_plus_excel", "multi", "mixunsat_Salesforce", "2", "portals_ae"),
 ("developer", "site_registers_hoardings", "in_city", "paper", "2", "offline"),
 ("developer", "selldo_unhappy", "in_city", "unsat_Sell.Do", "split", "ads"),
 ("developer", "happy_leadsquared", "in_city", "sat_LeadSquared", "0", "ads"),
 ("developer", "multi_city_three_pains", "several", "excel", "3", "mixed"),
 ("developer", "nri_launch_expos", "nri", "sheets_wa", "split", "events"),
 ("developer", "dubai_offplan_salesforce", "ae_city", "unsat_Salesforce", "2", "portals_ae"),
 ("developer", "india_uae_sales_office", "multi", "mixed_manual", "3", "events"),
 ("developer", "repeat_inventory_pain", "in_city", "excel", "repeat", "offline"),
 ("developer", "unrelated_cement_gripe", "in_city", "wa", "unrel", "offline"),
 ("developer", "no_problems_sheets", "in_city", "sheets_wa", "0", "ads"),
 ("developer", "zoho_plus_excel", "several", "mixunsat_Zoho CRM", "1", "ads"),
 ("developer", "countrywide_inhouse", "country", "unsat_an in-house CRM", "2", "mixed"),
 ("developer", "unknown_sources_paper", "none", "paper", "2", "unknown"),
 ("developer", "abu_dhabi_happy_salesforce", "ae_city", "sat_Salesforce", "0", "portals_ae"),
 ("developer", "wa_campaign_split", "in_city", "wa", "split", "wa"),
 ("channel_partner", "excel_one_pain_portals", "in_city", "excel", "1", "portals_in"),
 ("channel_partner", "wa_three_pains", "in_city", "wa", "3", "wa"),
 ("channel_partner", "leadsquared_split", "several", "unsat_LeadSquared", "split", "ads"),
 ("channel_partner", "happy_zoho", "in_city", "sat_Zoho CRM", "0", "mixed"),
 ("channel_partner", "india_uae_cp_sheets", "multi", "sheets_wa", "2", "events"),
 ("channel_partner", "nri_cp_excel", "nri", "excel", "repeat", "ads"),
 ("channel_partner", "dubai_cp_selldo", "ae_city", "unsat_Sell.Do", "2", "portals_ae"),
 ("channel_partner", "paper_and_referrals", "in_city", "paper", "unrel", "offline"),
 ("channel_partner", "no_location_unknown_src", "none", "sheets_wa", "2", "unknown"),
 ("channel_partner", "mixed_manual_three", "several", "mixed_manual", "3", "mixed"),
 ("channel_partner", "salesforce_excel_mix", "in_city", "mixunsat_Salesforce", "split", "portals_in"),
 ("channel_partner", "uae_country_wa", "country", "wa", "2", "portals_ae"),
 ("channel_partner", "inhouse_one_pain", "in_city", "unsat_an in-house CRM", "1", "wa"),
 ("channel_partner", "no_problems_excel", "in_city", "excel", "0", "offline"),
]
OUTS = ["handoff", "nurture_noconsent", "handoff", "nurture_later", "close_declined", "review", "handoff",
        "nurture_later_consent", "close_low", "handoff", "nurture_later", "review"]


def main():
    n = 250; plan = []
    for fi, fam in enumerate(FAM):
        plan += [fam] * (6 if fi < n - 5 * len(FAM) else 5)
    partial_idx = set(R.sample(range(n), 88)); oc = 0; rows = []
    for i, (org, scen, geo, tool, pain, src) in enumerate(plan):
        partial = i in partial_idx
        if partial: out = pick(OUTS)
        else: out = OUTS[oc % len(OUTS)]; oc += 1
        crm = tool.split("_", 1)[1] if tool.split("_")[0] in ("unsat", "sat", "mixunsat") else None
        sen = pick(["owner", "executive"]) if out == "handoff" else pick(list(ROLES))
        inf = "approver" if out == "handoff" else "none" if out == "close_low" else pick(["approver", "sponsored_evaluator", "none", "sponsored_evaluator"])
        p = dict(org=org, scen=scen, geo=geo, tool=tool, pain=pain, src=src, crm=crm, out=out, sen=sen, inf=inf)
        o = min(range(len(OPENERS)), key=lambda k: (OP_USE[k], R.random())); OP_USE[o] += 1
        rows.append(build(i + 1, p, partial, OPENERS[o]))
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    print("wrote", len(rows), OUT)


if __name__ == "__main__":
    main()
