"""Batch 12: real-estate developers in English (towers, townships, villas, commercial/IT parks, affordable,
luxury, redevelopment, multi-city, channel-partner-led sales). Examples are composed from per-family scenario
facts; each is checked against labels.complete() so the derived route matches the planned route, and every
visitor line is kept unique against all other raw batches."""
import json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from slm.labels import Extraction, complete  # noqa: E402

RAW = ROOT / "slm" / "data" / "raw"
OUT = RAW / "batch_12.jsonl"
R = random.Random(1212)

SEEN = set()
for f in RAW.glob("batch_*.jsonl"):
    if f.name == OUT.name: continue
    for line in f.read_text("utf-8").splitlines():
        if line.strip():
            for t in json.loads(line)["transcript"]:
                if t["speaker"] == "visitor": SEEN.add(t["text"].strip().lower())

OPENERS = [
    "Hi, I'm Beacon, Leadrat's demo assistant. What are you building or selling right now?",
    "Hello! Beacon here. Tell me about your projects and I'll tailor the tour.",
    "Welcome. I'm Beacon, and I can show you Leadrat live, no forms. Who am I talking to?",
    "Hey there, Beacon from Leadrat. Are you on the developer side or the broker side?",
    "Good to have you here. I'm Beacon. What made you look at a CRM today?",
    "Hi! I'm Beacon. Before I open any screens, what does your company develop?",
    "Hello, Beacon here. Launch coming up, or managing inventory that's already live?",
    "Welcome to the Leadrat demo. I'm Beacon. What should this half hour solve for you?",
    "Hi, this is Beacon. I help developers see how Leadrat tracks leads to site visits. What's your role?",
    "Hey! Beacon here. Residential, commercial, plots? Tell me where you play.",
    "Hello and thanks for stopping by. I'm Beacon. What does your sales setup look like?",
    "Hi there. I'm Beacon, a live guide to Leadrat. Which project brought you here?",
    "Welcome! Beacon at your service. What kind of real estate company are you with?",
    "Hi, Beacon speaking. Quick intro from your side and I'll pick the right screens.",
    "Hello! I'm Beacon. Is this for an in-house sales team or for your channel partners?",
    "Hey, I'm Beacon from Leadrat. What's the biggest thing slowing your sales team down?",
    "Hi! Beacon here, happy to walk you through Leadrat. Where is your company based?",
    "Good day. I'm Beacon. Tell me a little about your company and your current projects.",
    "Hello, I'm Beacon. No sign-up needed. What would you like to see first?",
    "Hi, welcome. I'm Beacon and I run the Leadrat demo. What do you do at your company?",
    "Hey there! Beacon here. Are you evaluating CRMs for a new launch?",
    "Hello! This is Beacon. What part of the sales funnel keeps you up at night?",
    "Hi, I'm Beacon. I can show leads, site visits and broker tracking. Where should we start?",
    "Welcome aboard. Beacon here. Tell me about your developer business.",
    "Hi! I'm Beacon, Leadrat's guide. Who's on the call and what do you build?",
    "Hello, Beacon from Leadrat here. What does a typical month of enquiries look like for you?",
    "Hi there, I'm Beacon. Share a bit about your company and I'll keep this relevant.",
    "Hey! Beacon here. Towers, villas or plots, what are you selling these days?",
    "Hello. I'm Beacon, and this demo adapts to you. What's your company about?",
    "Hi, Beacon here. Are you with a developer? Tell me about the portfolio.",
]

Q = {
 "team": ["How big is the sales team?", "How many people handle sales and pre-sales?", "What's the headcount on your sales side?",
          "How many sales executives do you have across projects?", "Roughly how many people touch leads every day?"],
 "leads": ["How many enquiries come in a month, and from where?", "What's your monthly lead volume and main sources?",
           "Where do leads come from, and how many per month?", "How many leads land in a typical month?",
           "Walk me through lead volume and channels."],
 "tools": ["How do you track leads today?", "What are you using to manage enquiries right now?", "Is there a CRM in place today?",
           "Where do the leads live once they arrive?", "What tools does the team rely on currently?"],
 "pain": ["What's hurting the most?", "What breaks most often in your sales process?", "Where do you lose deals today?",
          "What would you fix first if you could?", "What's the main frustration with the current setup?"],
 "auth": ["Who makes the call on a tool like this?", "Would you be the one signing off?", "Who else is involved in the decision?",
          "How does buying software work at your company?", "Is this your decision, or are you evaluating for someone?"],
 "next": ["Would you like our sales team to follow up?", "What's your timeline, and shall someone from sales reach out?",
          "Should I have a specialist contact you?", "When are you looking to decide, and can sales get in touch?",
          "Happy to set up a proper session with sales. Interested?"],
 "contact": ["What's the best email or number to reach you?", "Where should they reach you?", "Could you share an email or phone?",
             "Great. How should we contact you?", "Drop an email or phone number and I'll pass it on."],
}
SHOW = ["Here is the Leads list with source tags. ", "This is the Site Visit calendar. ", "Here's the Projects view with unit inventory. ",
        "This is the Channel Partner dashboard. ", "Here's the lead assignment screen. ", "This is the follow-up reminders panel. ", ""]

PFX = ["Aravali", "Saffron", "Tidewater", "Kestrel", "Banyan", "Monsoon", "Indigo", "Sandstone", "Vistara", "Coral", "Evergreen",
       "Northstar", "Deccan", "Riverbend", "Silveroak", "Lotus Crest", "Amberline", "Harborview", "Greystone", "Meridian", "Sunmark",
       "Palmgrove", "Crescent", "Orchid", "Tamarind", "Skyforge", "Granite Bay", "Neelkanth", "Pinnacle Arc", "Sapphire", "Mistral",
       "Ashoka Vale", "Cedar", "Keystone", "Marigold", "Horizon Peak", "Emerald Isle", "Ridgeway", "Solace", "Trident", "Velvet Sky",
       "Whitefield Arc", "Zenith", "Brightwater", "Copperleaf", "Dunewood", "Falcon Crest", "Goldmohur", "Hillview", "Ivory Gate"]
SFX = ["Developers", "Infra", "Realty", "Buildcon", "Estates", "Homes", "Constructions", "Projects", "Landmarks", "Spaces", "Group"]
PRJ = ["Heights", "Greens", "Residency", "County", "Enclave", "Towers", "Meadows", "One", "Park", "Vista", "Gardens", "Square", "Bay"]
FIRST = ["Rohan", "Ananya", "Vikram", "Sneha", "Arjun", "Kavya", "Nikhil", "Isha", "Farhan", "Priya", "Aditya", "Neha", "Karthik",
         "Divya", "Omar", "Tanvi", "Siddharth", "Meera", "Rahul", "Aisha", "Varun", "Pooja", "Imran", "Ritika", "Harsh", "Leena"]
CITIES = [("Mumbai", "India"), ("Pune", "India"), ("Bengaluru", "India"), ("Hyderabad", "India"), ("Gurugram", "India"),
          ("Noida", "India"), ("Ahmedabad", "India"), ("Chennai", "India"), ("Kolkata", "India"), ("Jaipur", "India"),
          ("Lucknow", "India"), ("Indore", "India"), ("Kochi", "India"), ("Nagpur", "India"), ("Surat", "India"),
          ("Chandigarh", "India"), ("Coimbatore", "India"), ("Vizag", "India"), ("Dubai", "UAE"), ("Abu Dhabi", "UAE"), ("Sharjah", "UAE")]
ROLES = [("founder", "owner"), ("co-founder", "owner"), ("managing director", "owner"), ("director", "owner"),
         ("CMO", "executive"), ("head of sales", "executive"), ("VP sales", "executive"), ("chief sales officer", "executive"),
         ("CRM manager", "manager"), ("pre-sales manager", "manager"), ("marketing manager", "manager"), ("sales manager", "manager"),
         ("pre-sales executive", "individual_contributor"), ("CRM executive", "individual_contributor"),
         ("marketing associate", "individual_contributor")]
TOOLS = [
 (["Excel", "WhatsApp"], "manual", "everything sits in Excel and WhatsApp groups"),
 (["Google Sheets"], "manual", "a shared Google Sheet per project, updated whenever someone remembers"),
 (["paper registers", "Excel"], "manual", "site visits go in a paper register at the sales lounge, then someone types them into Excel"),
 (["WhatsApp"], "manual", "honestly just WhatsApp, each executive keeps their own chats"),
 (["Salesforce"], "unsatisfied_crm", "we pay for Salesforce but it was set up for a different business and nobody updates site visits"),
 (["Zoho CRM"], "unsatisfied_crm", "Zoho CRM, but it can't handle inventory or broker bookings the way we need"),
 (["HubSpot"], "unsatisfied_crm", "HubSpot for marketing, though sales never adopted it and portal leads don't sync"),
 (["Sell.Do"], "unsatisfied_crm", "we moved to a real-estate CRM last year and the channel partner module is weak"),
 (["in-house CRM"], "unsatisfied_crm", "an in-house CRM our IT team built, and it breaks every launch"),
 (["Zoho CRM"], "satisfied_crm", "Zoho CRM, and to be fair it does the job for us"),
 (["Salesforce"], "satisfied_crm", "Salesforce, well configured, the team is happy with it"),
]
SRC = ["99acres", "MagicBricks", "Housing.com", "Facebook ads", "Google ads", "Instagram", "channel partners", "walk-ins",
       "property expos", "website", "Bayut", "Property Finder", "referrals", "hoardings", "YouTube ads"]
PAINS = [
 ("leads leaking between marketing and sales", "leads fall through the cracks between the marketing agency and our sales team"),
 ("no site visit tracking", "we can't tell which leads actually came for a site visit"),
 ("slow first response", "first call to a new lead often happens a day later"),
 ("duplicate leads from brokers", "brokers register the same buyer we already had and then fight over brokerage"),
 ("no channel partner visibility", "we have no view of which channel partner is bringing what"),
 ("launch lead spike overwhelms team", "during a launch the leads spike and the team simply can't call them all"),
 ("no source-wise ROI", "we don't know which ad spend actually turns into bookings"),
 ("follow-ups missed", "follow-ups get missed once an executive has more than a few hundred leads"),
 ("inventory not linked to leads", "unit availability isn't connected to the lead, so we quote sold flats"),
 ("attrition takes leads with them", "when an executive quits, their leads walk out with them"),
 ("manual reporting", "every Monday someone spends half a day building the sales report by hand"),
 ("no lead ownership rules", "two executives call the same buyer because nothing says who owns the lead"),
]

FAM = [  # (slug, segment phrase, preferred pain indices, preferred sources)
 ("tower_launch_spike", "a 40-storey residential tower launching next quarter", [5, 2, 7], ["Facebook ads", "Google ads", "99acres"]),
 ("plotted_township", "a 120-acre plotted township on the city outskirts", [1, 4, 3], ["channel partners", "hoardings", "Facebook ads"]),
 ("luxury_villas", "a gated community of luxury villas", [1, 2, 10], ["referrals", "Instagram", "property expos"]),
 ("it_park_leasing", "a Grade A IT park where we lease office floors", [0, 10, 11], ["website", "referrals", "Google ads"]),
 ("affordable_pmay", "affordable housing under PMAY with small 1 BHK units", [5, 7, 2], ["Facebook ads", "walk-ins", "hoardings"]),
 ("redevelopment_society", "redevelopment of old housing societies", [8, 11, 0], ["walk-ins", "referrals", "99acres"]),
 ("multi_city_portfolio", "projects in four cities at once", [10, 6, 11], ["99acres", "MagicBricks", "Google ads"]),
 ("cp_driven_sales", "a mid-segment project where most sales come through brokers", [3, 4, 1], ["channel partners", "property expos"]),
 ("inhouse_sales_team", "three residential projects sold only by our in-house team", [7, 11, 2], ["Housing.com", "Google ads", "walk-ins"]),
 ("site_visit_blindspot", "two townships with a sales lounge at each site", [1, 0, 2], ["Facebook ads", "walk-ins", "Instagram"]),
 ("lead_leakage_agency", "a new launch where an agency runs all our digital campaigns", [0, 6, 2], ["Facebook ads", "Google ads", "YouTube ads"]),
 ("broker_registration", "a large project with hundreds of empanelled brokers", [3, 4, 11], ["channel partners", "99acres"]),
 ("dubai_offplan", "off-plan apartments sold to investors", [4, 3, 2], ["Bayut", "Property Finder", "channel partners"]),
 ("nri_investors", "premium apartments mostly bought by NRIs", [2, 7, 1], ["website", "Google ads", "property expos"]),
 ("commercial_retail", "a high-street retail and office complex", [8, 0, 10], ["channel partners", "website", "hoardings"]),
 ("weekend_homes", "weekend homes and farm plots near a hill station", [1, 7, 6], ["Instagram", "YouTube ads", "referrals"]),
 ("senior_living", "a senior living community", [2, 7, 10], ["referrals", "Google ads", "website"]),
 ("student_housing", "co-living and student housing blocks", [6, 5, 11], ["Instagram", "Google ads", "website"]),
 ("ready_to_move_inventory", "unsold ready-to-move inventory in completed towers", [8, 7, 6], ["99acres", "MagicBricks", "walk-ins"]),
 ("expo_leads", "a portfolio we mostly promote at property expos", [0, 7, 5], ["property expos", "walk-ins", "Facebook ads"]),
 ("attrition_pain", "two mid-rise projects with a young sales team", [9, 11, 7], ["Housing.com", "Facebook ads"]),
 ("reporting_overload", "five ongoing residential projects", [10, 6, 1], ["MagicBricks", "Google ads", "channel partners"]),
 ("family_business_gen2", "a family-run business I recently took over from my father", [10, 9, 7], ["walk-ins", "referrals", "hoardings"]),
 ("presales_callcenter", "a pre-sales call centre that qualifies leads for our site team", [2, 11, 1], ["Facebook ads", "Google ads", "99acres"]),
 ("mixed_use_township", "a mixed-use township with homes, retail and a school", [4, 10, 6], ["channel partners", "Google ads", "hoardings"]),
 ("boutique_developer", "small boutique buildings of twenty to thirty flats", [7, 1, 2], ["referrals", "Instagram", "walk-ins"]),
 ("warehousing_park", "warehousing and logistics parks", [0, 10, 8], ["website", "referrals", "channel partners"]),
 ("second_launch_phase", "phase two of a township after a strong phase one", [5, 3, 1], ["channel partners", "Facebook ads", "website"]),
 ("price_sensitive_tier2", "budget apartments in a tier-two city", [2, 7, 5], ["Facebook ads", "hoardings", "walk-ins"]),
 ("branded_residences", "branded luxury residences with a hotel partner", [2, 1, 4], ["referrals", "property expos", "Instagram"]),
 ("jv_landowner", "joint development projects with landowners", [10, 8, 4], ["channel partners", "walk-ins"]),
 ("marketing_roi", "three launches with a big digital budget", [6, 0, 5], ["Google ads", "Facebook ads", "YouTube ads"]),
 ("crm_migration", "a mature portfolio that has outgrown its current CRM", [11, 10, 8], ["99acres", "MagicBricks", "website"]),
 ("whatsapp_first", "entry-level homes where buyers talk to us only on WhatsApp", [7, 11, 9], ["Facebook ads", "Instagram"]),
 ("small_plots", "small plotted layouts of eighty to a hundred plots", [1, 3, 7], ["hoardings", "channel partners", "walk-ins"]),
 ("gulf_multi_emirate", "residential projects across more than one emirate", [4, 6, 10], ["Bayut", "Property Finder", "Google ads"]),
 ("sales_head_new_joinee", "a developer where I joined as the new sales leader last month", [10, 11, 1], ["99acres", "channel partners"]),
 ("booking_to_registration", "projects where the paperwork after booking drags on", [8, 7, 10], ["walk-ins", "referrals"]),
 ("research_only", "a couple of projects, though I'm just browsing tools", [2, 6], ["website", "99acres"]),
 ("tiny_developer", "a single small building, our first project", [7, 2], ["walk-ins", "referrals"]),
 ("happy_with_crm", "several projects and an established CRM", [10, 6], ["MagicBricks", "Google ads"]),
 ("eco_homes", "green-certified homes with solar and rainwater harvesting", [6, 1, 7], ["Instagram", "Google ads", "property expos"]),
 ("hospital_adjacent", "apartments next to a new medical city", [2, 5, 8], ["Housing.com", "Facebook ads"]),
 ("golf_estate", "a golf-course estate with villas and plots", [1, 4, 2], ["referrals", "property expos", "channel partners"]),
 ("metro_corridor", "towers along the new metro corridor", [5, 3, 0], ["99acres", "Facebook ads", "channel partners"]),
]

# ---------------- visitor phrasing ----------------
def v_intro(c):
    who = f"I'm {c['cname']}, " if c.get("say_name") else "I'm the "
    role = c["role"]
    opts = [
        f"{who}{role} at {c['org']}. We're a developer in {c['city']} working on {c['seg']}.",
        f"{c['org']} here, I'm {c['art']} {role}. Our current focus in {c['city']} is {c['seg']}.",
        f"We develop real estate in {c['city']}. The company is {c['org']} and I work as {c['art']} {role}; right now it's {c['seg']}.",
        f"Developer side. {c['org']}, based in {c['city']}. My title is {role}, and the big thing on our plate is {c['seg']}.",
        f"I handle things as {c['art']} {role} for {c['org']}, a {c['city']} developer. We're busy with {c['seg']}, {c['proj']}.",
    ]
    if c.get("say_name"): opts[0] = f"I'm {c['cname']}, {role} at {c['org']}. We're a developer in {c['city']} working on {c['seg']}."
    else: opts[0] = f"I'm the {role} at {c['org']}. We're a developer in {c['city']} working on {c['seg']}."
    return R.choice(opts)

def v_team(c):
    a = c["agents"]
    return R.choice([
        f"{a} people in sales across our sites, pre-sales included.",
        f"We have {a} sales executives right now for {c['proj']} and the other projects.",
        f"Sales headcount is {a}, split between the site lounge and the office.",
        f"About {a} on the team. It grows a bit around launches but {a} is the core.",
        f"{a} in total, and they all work leads for {c['proj']}.",
    ])

def v_leads(c):
    lo, hi = c["lmin"], c["lmax"]; s = c["src_say"]
    n = f"around {lo}" if lo == hi else f"somewhere between {lo} and {hi}"
    if c.get("vague_leads"):
        return R.choice([f"No clue on the count honestly, it swings a lot. Mostly {s}.",
                         f"Hard to put a number on it for {c['proj']}; the channels are {s}.",
                         f"It varies too much to say. Most of it is {s}."])
    return R.choice([
        f"{n.capitalize()} leads a month, mainly from {s}.",
        f"We get {n} enquiries monthly. Sources are {s}.",
        f"For {c['proj']} it's {n} a month, coming from {s}.",
        f"Monthly volume is {n}. The bulk arrives through {s}.",
    ])

def v_tools(c):
    return R.choice([f"Right now, {c['tool_say']}.", f"For {c['proj']}, {c['tool_say']}.", f"Today {c['tool_say']}.",
                     f"In {c['city']} {c['tool_say']}."])

def v_pain(c):
    if c["pain"] == []:
        return R.choice([f"Nothing is really broken at {c['org']}, I'm just keeping an eye on the market.",
                         f"Honestly no complaints about how {c['proj']} is being sold. Just curious.",
                         f"We're fine for now, no real problems on the sales side in {c['city']}."])
    sp = c["pain_say"]
    if len(sp) == 1:
        return R.choice([f"Mainly that {sp[0]}.", f"The big one on {c['proj']}: {sp[0]}.", f"Biggest issue is {sp[0]}."])
    return R.choice([f"Two things: {sp[0]}, and {sp[1]}.", f"First, {sp[0]}. Second, {sp[1]}.",
                     f"On {c['proj']} {sp[0]}, and on top of that {sp[1]}.",
                     f"{sp[0][0].upper() + sp[0][1:]}. Also {sp[1]}."])

def v_auth(c):
    i = c["inf"]
    if i == "approver":
        return R.choice([f"I sign off on software for {c['org']}, so it's my call.", "Budget is mine to approve, nobody else needs to weigh in.",
                         f"It's my decision. I approve tools for all our {c['city']} projects.", "I can buy this myself if it fits."])
    if i == "sponsored_evaluator":
        return R.choice([f"Our MD asked me to shortlist options; she decides after my recommendation.",
                         f"I'm evaluating on behalf of the directors at {c['org']}, they take the final call.",
                         "My job is to pick two or three tools and present them to the promoter, who approves.",
                         f"I'm the one doing the evaluation for {c['proj']}, but the chairman signs."])
    return R.choice([f"I don't have any say in purchases at {c['org']}, I'm just gathering information.",
                     "No decision power here, someone asked me to look around.",
                     f"Purchases aren't my area at all; I'm only collecting brochures for {c['proj']}."])

def v_next(c):
    x, ok = c["nxt"], c["consent"]
    if x == "declined":
        return R.choice([f"Please don't have anyone follow up, I'm only researching for now.",
                         f"No calls please. We're not looking to buy anything for {c['proj']}.",
                         "I'd rather nobody contacts me. This was just a look."])
    if x == "later":
        base = R.choice([f"Not before {c['month']}, we're locked until then", f"Probably after {c['month']}, budgets reopen then",
                         f"We'll revisit this around {c['month']}"])
        return base + (". Sure, sales can reach out then." if ok else ", and I'll get back to you myself, no calls for now.")
    base = R.choice([f"We want this running before {c['proj']} opens bookings in the next few weeks",
                     f"We need to decide within this month", f"Ideally live in two to three weeks, before {c['month']}'s launch push"])
    return base + (R.choice([". Yes, have sales call me.", ", so please get someone to contact me.", ". Go ahead and set up a call."])
                   if ok else ". I'll contact you when ready, please don't pass my details to sales.")

def v_contact(c):
    if c.get("phone"): return R.choice([f"Call me on {c['phone']}.", f"{c['phone']}, afternoons work best.", f"Phone is better: {c['phone']}."])
    return R.choice([f"Email me at {c['email']}.", f"{c['email']} works.", f"You can write to {c['email']}, I check it daily."])

VF = {"team": v_team, "leads": v_leads, "tools": v_tools, "pain": v_pain, "auth": v_auth, "next": v_next, "contact": v_contact}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "October", "November", "December", "Diwali"]

USE = [0] * len(OPENERS)
def opener():
    i = min(range(len(OPENERS)), key=lambda k: (USE[k], R.random())); USE[i] += 1; return OPENERS[i]

def plan(fam, route):
    slug, seg, pidx, srcs = fam
    c = {"seg": seg}
    c["org"] = f"{R.choice(PFX)} {R.choice(SFX)}"
    c["proj"] = f"{R.choice(PFX)} {R.choice(PRJ)}"
    c["city"], c["country"] = R.choice(CITIES[18:] if slug in ("dubai_offplan", "gulf_multi_emirate") else CITIES[:18])
    c["cname"] = R.choice(FIRST); c["say_name"] = R.random() < 0.5
    c["month"] = R.choice(MONTHS)
    hi = route == "sales_handoff" or (route == "nurture" and R.random() < 0.6)
    lowfit = slug in ("research_only", "tiny_developer", "happy_with_crm") or route == "graceful_close" and R.random() < 0.5
    if lowfit:
        c["agents"] = R.choice([2, 3, 4, 5]); lo = R.choice([20, 35, 50, 60, 80])
    elif hi:
        c["agents"] = R.choice([18, 22, 25, 30, 36, 45, 60, 85, 120]); lo = R.choice([450, 600, 800, 1200, 1500, 2500])
    else:
        c["agents"] = R.choice([6, 8, 10, 12, 15, 24]); lo = R.choice([120, 150, 200, 250, 300, 600])
    c["lmin"], c["lmax"] = (lo, lo) if R.random() < 0.6 else ((lo, lo + 100) if lo >= 500 or lo + 100 < 500 else (lo, lo))
    if 100 > lo and c["lmax"] >= 100: c["lmax"] = lo
    c["src"] = R.sample(srcs, min(len(srcs), R.choice([1, 2, 2, 3])))
    c["src_say"] = " and ".join(c["src"])
    tool = R.choice([t for t in TOOLS if t[1] == "satisfied_crm"]) if slug == "happy_with_crm" else \
           R.choice([t for t in TOOLS if t[1] != "satisfied_crm"]) if hi else R.choice(TOOLS)
    c["tools"], c["proc"], c["tool_say"] = tool
    if slug == "happy_with_crm" or (lowfit and R.random() < 0.4): pick = []
    else:
        pool = pidx + [i for i in range(len(PAINS)) if i not in pidx]
        k = 2 if hi else R.choice([1, 2])
        pick = R.sample(pidx, min(k, len(pidx))) if len(pidx) >= k else pool[:k]
    c["pain"] = [PAINS[i][0] for i in pick]; c["pain_say"] = [PAINS[i][1] for i in pick]
    roles = ROLES[:8] if hi else ROLES
    c["role"], c["sen"] = R.choice(roles)
    c["art"] = "an" if c["role"][0] in "aeiou" else "a"
    if c["sen"] == "owner": c["inf"] = "approver"
    elif c["sen"] == "individual_contributor": c["inf"] = R.choice(["none", "sponsored_evaluator"])
    else: c["inf"] = R.choice(["approver", "sponsored_evaluator"]) if hi else R.choice(["approver", "sponsored_evaluator", "none"])
    if route == "sales_handoff": c["nxt"], c["consent"] = "within_30_days", True
    elif route == "graceful_close": c["nxt"], c["consent"] = (("declined", False) if not lowfit or R.random() < 0.4 else (R.choice(["later", "within_30_days"]), False))
    else: c["nxt"], c["consent"] = R.choice([("later", True), ("later", False), ("within_30_days", False), ("within_30_days", True)])
    if c["consent"]:
        if R.random() < 0.5: c["phone"] = f"+91 90000 2{R.randint(0, 9999):04d}" if c["country"] == "India" else f"+971 50 000 2{R.randint(0, 999):03d}"
        else: c["email"] = f"{c['cname'].lower()}.{R.randint(1, 99)}@{c['org'].split()[0].lower()}.example.com"
    c["drop"] = R.choice(["leads", "auth", "tools", "team"]) if route == "human_review" else None
    if c["drop"] == "leads": c["vague_leads"] = True
    return c

def build(fam, route, partial, ex_id):
    c = plan(fam, route)
    mid = ["team", "leads", "tools", "pain"]; R.shuffle(mid)
    if c["drop"] in ("team", "tools"): mid.remove(c["drop"])
    order = mid + ([] if c["drop"] == "auth" else ["auth"]) + ["next"] + (["contact"] if c["consent"] else [])
    turns = [opener(), v_intro(c)]; groups = ["intro"]
    for g in order:
        turns.append(R.choice(SHOW) + R.choice(Q[g]) if g not in ("next", "contact") else R.choice(Q[g]))
        turns.append(VF[g](c)); groups.append(g)
    if partial:
        k = R.randint(2, min(5, len(groups) - 1)); groups = groups[:k]; turns = turns[:2 * k]
    tid = {g: 2 * (i + 1) for i, g in enumerate(groups)}
    ev = {}; L = {"organisation": {"name": None, "type": "developer", "agents": None}, "geography": {"countries": None, "cities": None},
                  "monthly_leads": {"min": None, "max": None}, "contact": {"name": None, "email": None, "phone": None}}
    t = tid["intro"]
    L.update(role=c["role"], seniority=c["sen"]); L["organisation"]["name"] = c["org"]
    L["geography"] = {"countries": [c["country"]], "cities": [c["city"]]}
    for k in ("role", "seniority", "organisation.name", "organisation.type", "geography"): ev[k] = [t]
    if c["say_name"]: L["contact"]["name"] = c["cname"]; ev["contact"] = [t]
    if "team" in tid: L["organisation"]["agents"] = c["agents"]; ev["organisation.agents"] = [tid["team"]]
    if "leads" in tid:
        L["lead_sources"] = c["src"]; ev["lead_sources"] = [tid["leads"]]
        if not c.get("vague_leads"): L["monthly_leads"] = {"min": c["lmin"], "max": c["lmax"]}; ev["monthly_leads"] = [tid["leads"]]
    if "tools" in tid:
        L["current_tooling"] = c["tools"]; L["process"] = c["proc"]; ev["current_tooling"] = ev["process"] = [tid["tools"]]
    if "pain" in tid: L["pain_points"] = c["pain"]; ev["pain_points"] = [tid["pain"]]
    if "auth" in tid: L["influence"] = c["inf"]; ev["influence"] = [tid["auth"]]
    if "next" in tid:
        L["next_step"] = c["nxt"]; ev["next_step"] = [tid["next"]]
        if c["consent"]: L["consent"] = True; ev["consent"] = [tid["next"]]
    if "contact" in tid:
        L["contact"]["email"] = c.get("email"); L["contact"]["phone"] = c.get("phone")
        ev["contact"] = ev.get("contact", []) + [tid["contact"]]
    L["evidence"] = ev
    tr = [{"turn_id": i + 1, "speaker": "beacon" if i % 2 == 0 else "visitor", "text": x} for i, x in enumerate(turns)]
    return {"id": ex_id, "family": f"developer/b12_{fam[0]}", "language": "en", "partial": partial, "transcript": tr, "label": L}

def main():
    rows, n = [], 0
    counts = [6 if i < 25 else 5 for i in range(len(FAM))]  # 25*6 + 20*5 = 250
    cycle = ["sales_handoff", "nurture", "graceful_close", "human_review"]
    ci = 0
    for fam, cnt in zip(FAM, counts):
        for v in range(cnt):
            n += 1; partial = (n % 20) in (0, 3, 6, 9, 12, 15, 18)  # 35%
            if fam[0] in ("research_only", "tiny_developer", "happy_with_crm"): route = "graceful_close" if v % 2 == 0 else "nurture"
            else: route = cycle[ci % 4]; ci += 1
            for _ in range(500):
                saved = list(USE)
                ex = build(fam, route, partial, f"b12-{n:03d}")
                q = complete(Extraction.model_validate(ex["label"]))
                vis = [t["text"].strip().lower() for t in ex["transcript"] if t["speaker"] == "visitor"]
                if (partial or q.route == route) and not (set(vis) & SEEN) and len(set(vis)) == len(vis):
                    SEEN.update(vis); rows.append(ex); break
                USE[:] = saved
            else:
                raise SystemExit(f"could not build {n} {fam[0]} {route}")
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    print(len(rows), "rows ->", OUT)

if __name__ == "__main__":
    main()
