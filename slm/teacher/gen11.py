"""Batch 11: English brokerages (resale, rentals, commercial leasing, luxury, NRI desks, franchises, micro shops,
100+ agent firms) with deliberate band-boundary numbers. Facts are planned per example; turns are assembled from
varied phrasings and every visitor line is checked for uniqueness against all other raw batches."""
import json
import random
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = RAW / "batch_11.jsonl"
R = random.Random(1111)

SEEN = set()
for f in RAW.glob("batch_*.jsonl"):
    if f.name == OUT.name:
        continue
    for line in f.read_text("utf-8").splitlines():
        if line.strip():
            for t in json.loads(line)["transcript"]:
                if t["speaker"] == "visitor":
                    SEEN.add(t["text"].strip().lower())


def pick(options, fmt):
    """Choose a phrasing whose rendered visitor line is new everywhere."""
    opts = list(options)
    R.shuffle(opts)
    for o in opts:
        s = o.format(**fmt)
        if s.strip().lower() not in SEEN:
            SEEN.add(s.strip().lower())
            return s
    ctx = CTX[:]
    R.shuffle(ctx)
    for o in opts:
        for c in ctx:
            try:
                s = o.format(**fmt) + " " + c.format(**CUR)
            except KeyError:
                continue
            if s.strip().lower() not in SEEN:
                SEEN.add(s.strip().lower())
                return s
    raise RuntimeError("no unique phrasing for " + repr(fmt))


CUR = {}
CTX = ["That's for the whole {name} team.", "Our {city} office is the priority.", "Speaking for {name} here.",
       "The {city} branch would go first.", "We'd start with the {city} team.", "I'll loop in the rest of {name}.",
       "Things are busy in {city} right now.", "Everyone at {name} is stretched thin."]


OPENERS = [
    "Hello, I'm Beacon, Leadrat's demo assistant. What does your brokerage handle day to day?",
    "Hi! Beacon here. I can show you Leadrat live, no sign-up needed. Tell me about your firm?",
    "Welcome. I'm Beacon. Resale, rentals or commercial: where does your team spend most of its time?",
    "Hey there, Beacon from Leadrat. Who am I chatting with today?",
    "Good morning! I'm Beacon, and I run the Leadrat walkthrough. What kind of agency are you with?",
    "Hi, I'm Beacon. Before I open any screens, what does your business look like?",
    "Hello and thanks for stopping by. I'm Beacon. What would you like Leadrat to fix for you?",
    "Beacon here, happy to help. Are you a brokerage, a developer, or something else entirely?",
    "Hi! I'm Beacon, the Leadrat guide. What brings you to the demo today?",
    "Welcome to Leadrat. I'm Beacon. Tell me a little about your agency and I'll tailor the tour.",
    "Hello! Beacon speaking. What markets does your team work in?",
    "Hi there. I'm Beacon, and I can walk you through leads, listings and follow-ups. Where shall we start?",
    "Good to have you here. Beacon from Leadrat. What's your role at the company?",
    "Hey! Beacon here. Give me a quick picture of your brokerage and I'll show the relevant bits.",
    "Hello, Beacon here. No forms, just questions and screens. What does your firm do?",
    "Hi, welcome in. I'm Beacon. Which part of your sales process hurts the most right now?",
    "Beacon here, Leadrat's live demo. Who are you and what does your team sell or lease?",
    "Hello! I'm Beacon. Many brokers come here for lead tracking. Is that you too?",
    "Hi, this is Beacon. I can keep it short. What kind of property business are you in?",
    "Welcome! Beacon from Leadrat here. What would make the next ten minutes useful for you?",
    "Hi there, Beacon here. Tell me where your agency is based and what you deal in.",
    "Hello, I'm Beacon. Shall I start with a tour, or would you rather tell me about your setup first?",
    "Hey, welcome. I'm Beacon. What made you look at a CRM this week?",
    "Good afternoon! Beacon here. Which brokerage are you with?",
    "Hi, I'm Beacon, the assistant behind this demo. How does your agency run today?",
    "Hello there. Beacon from Leadrat. What does a normal week look like for your team?",
    "Hi! Beacon here. Tell me about your business and I'll pull up the matching screens.",
    "Welcome, I'm Beacon. Are you exploring for yourself or on behalf of your company?",
    "Hi, Beacon speaking. What sort of deals does your team close most often?",
    "Hello! I'm Beacon. Let's start simple: what's your company and what's your part in it?",
]
OUSE = {}


def opener():
    idx = min(range(len(OPENERS)), key=lambda i: (OUSE.get(i, 0), R.random()))
    OUSE[idx] = OUSE.get(idx, 0) + 1
    return OPENERS[idx]


Q = {
    "agents": ["How many agents are on your team?", "What's the size of your sales team?", "How many brokers work with you?",
               "Roughly how many people handle clients?", "How big is the team on the ground?", "And headcount on the sales side?"],
    "leads": ["How many enquiries come in each month?", "What's your monthly lead volume like?", "How many leads a month, and from where?",
              "Where do your leads come from, and how many per month?", "Any sense of monthly enquiry numbers?", "What does lead flow look like in a month?"],
    "pain": ["How do you track all that today?", "What are you using to manage leads right now?", "Walk me through how leads get handled now.",
             "What tools does the team rely on, and what's frustrating about them?", "Where do things fall through the cracks?", "How is follow-up managed at the moment?"],
    "inf": ["Who makes the call on software like this?", "Would you be the one to sign off?", "Who else is involved in the decision?",
            "Is this your decision or someone else's?", "Who approves a purchase like this?", "How does buying software work at your firm?"],
}
SCREENS = ["Here is the Leads list with source, owner and next follow-up on one row.",
           "This is the Listings screen; each unit shows who is showing it and when.",
           "Here's the follow-up board, overdue calls turn red.",
           "This is the auto-assignment rule screen; portal leads route to agents in rotation.",
           "Here is the agent performance report by source and closure.",
           "This is the WhatsApp inbox view, all chats tied to the lead record.",
           "Here's the site-visit calendar, synced for every agent.",
           "This is the duplicate check; the same buyer from two portals merges into one lead."]
ASK = ["Would you like our sales team to follow up with you?", "Shall I have someone from sales contact you?",
       "Happy for a Leadrat specialist to reach out?", "Can our team get in touch to set this up?",
       "Would a call from our sales folks be useful?", "Want me to pass this to sales for a proper walkthrough?"]
ASKC = ["Great. What's the best email or number?", "Perfect. Where should they reach you?", "Sure. Email or phone?",
        "Noted. Could you share a contact?", "Thanks. Which email or phone should they use?"]

# --- visitor phrasings ---
INTRO = [
    "I'm the {role} at {name}, a {flavor} in {city}.",
    "{name} here, we're a {flavor} based in {city}. I'm the {role}.",
    "Hi, {role} of {name}. We run a {flavor} out of {city}.",
    "We're {name}, {flavor}, {city}. I handle things as {role}.",
    "Hello. I work as {role} at {name}; it's a {flavor} in {city}.",
    "This is the {role} from {name}. {city} based {flavor}.",
    "Our firm is {name}, a {flavor} in {city}, and I'm its {role}.",
]
INTRO_NOROLE = [
    "We're {name}, a {flavor} in {city}. Just having a look.",
    "{name}, {flavor}, operating in {city}. Curious what this does.",
    "I'm from {name}. We're a {flavor} in {city}.",
]
AG = ["We have {a} agents.", "{a} people on the sales side.", "Team of {a} brokers right now.", "{A} agents, all on the field.",
      "Currently {a} of us work with clients.", "Headcount is {a} agents.", "We're {a} agents strong.", "{A} brokers, including me."]
AG_ABOUT = ["About {a} agents.", "Around {a} brokers, give or take.", "Roughly {a} people in sales.", "Something like {a} agents at the moment."]
AG_SPAN = ["Anywhere between {lo} and {hi} agents, it changes every season.", "It swings from {lo} to {hi} brokers depending on the month.",
           "Somewhere from {lo} to {hi} people, freelancers come and go."]
LE = ["About {l} leads a month, mostly from {src}.", "Roughly {l} enquiries monthly, {src} being the main ones.",
      "We get {l} leads a month through {src}.", "Close to {l} a month. Sources are {src}.", "{L} enquiries in a typical month, from {src}.",
      "Our monthly count is {l}, coming via {src}."]
LE_RANGE = ["Between {lo} and {hi} a month, from {src}.", "Anything from {lo} to {hi} enquiries monthly, largely {src}.",
            "{Lo} to {hi} leads a month, depending on the season. {src} bring most."]
TP = ["Everything sits in {tools}. {pain}.", "We use {tools}. Honestly, {pain}.", "It's all {tools} right now, and {pain}.",
      "{Tools} is what we have. The trouble is {pain}.", "Our agents use {tools}. Biggest issue: {pain}.",
      "Leads go into {tools}, but {pain}."]
TP_NOPAIN = ["We run on {tools} and it works fine for us, no real complaints.", "{Tools} does the job, I can't say we have problems.",
             "We use {tools}; honestly nothing is broken."]
INF = {
    "approver": ["I sign off on tools like this myself.", "It's my decision, I own the budget.", "I approve all software spends at {name}.",
                 "Me. I'm the one who signs.", "I decide, my partner just gets informed.", "The final call is mine."],
    "sponsored_evaluator": ["My director asked me to evaluate this; she will sign.", "I'm shortlisting for the founders, they approve.",
                            "I'm scouting options and my MD takes the final call.", "The owner asked me to check this out and report back.",
                            "I'll recommend it, the partners decide."],
    "none": ["I don't really have a say, I'm just curious.", "Not my decision at all, I only use whatever we're given.",
             "Management picks software, I'm not involved in that."],
}
NEXT = {
    ("within_30_days", True): ["Yes, please. We want something running this month.", "Sure, let's talk this week.",
                               "Go ahead, I'd like to move within the next couple of weeks.", "Yes, have them call me, we're keen to start soon.",
                               "Definitely, we want to decide before the month ends.", "Yes, the sooner the better, ideally next week."],
    ("within_30_days", False): ["We want to decide this month, but no calls please, I'll sign up myself.",
                                "I'd rather not be contacted; I'll come back within a couple of weeks on my own."],
    ("later", True): ["Okay, you can reach out, but we're only looking at this after {q}.", "Sure, get in touch, though we won't buy before {q}.",
                      "Fine, contact me, just know it's a {q} project."],
    ("later", False): ["Not now. Maybe after {q}, I'll come back myself.", "Let me think about it; probably around {q}.",
                       "No call for now, we'll revisit this after {q}.", "I'll hold off till {q}, don't contact me yet."],
    ("declined", False): ["No thanks, please don't have anyone contact me.", "I'm not interested in a follow-up, just wanted to see it.",
                          "Please don't call, we're not planning to buy anything.", "No, I don't want sales reaching out."],
}
QUARTERS = ["Diwali", "the new financial year", "next quarter", "the monsoon", "our office move", "March", "Ramadan", "the summer"]
CONTACT = ["{email}", "Email is {email}.", "You can use {email}, I'm {cname}.", "{phone}, ask for {cname}.",
           "Call me on {phone}.", "{cname}, {phone}.", "{email} works best.", "Phone is {phone}, name {cname}."]

CORR = ["Sorry, I said {a0} earlier but it's actually {a} agents now, we hired recently.",
        "Correction: we're {a} agents, not {a0}. I forgot the new branch.",
        "Actually make that {a}, not {a0}; I left out the leasing team."]

PAINS = ["leads go cold because nobody calls back in time", "two agents end up calling the same buyer", "we can't tell which portal actually converts",
         "site visits get double-booked", "agents leave and take their contacts with them", "follow-ups get forgotten after the first call",
         "I have no view of what each agent did today", "landlord and tenant details are scattered", "duplicate leads from different portals",
         "lease renewals slip past us", "NRI clients in other time zones get missed", "we lose track of which unit is still available",
         "reporting to the owner takes a full day every week", "new agents take weeks to learn our system", "portal leads sit unassigned for hours",
         "we don't know our cost per lead", "rent reminders are done by hand", "commercial requirements get mixed up with residential",
         "luxury clients expect instant replies and we're slow", "franchise offices don't share lead data with head office",
         "WhatsApp chats disappear when an agent changes phone", "the pipeline is invisible to management", "brokerage invoices are chased manually",
         "walk-in details never get written down", "listing photos and details are out of date", "we can't measure agent response time",
         "shared sheets keep getting overwritten", "leads from Instagram are never logged", "callbacks for weekend enquiries are missed",
         "the CRM we have is too slow on mobile", "our current CRM has no portal integration", "the CRM is too complex so agents skip it"]
TOOLS_MANUAL = [["Excel"], ["Google Sheets"], ["WhatsApp"], ["Excel", "WhatsApp"], ["a paper register"], ["Google Sheets", "WhatsApp"], ["notebooks", "WhatsApp"]]
TOOLS_CRM = [["Zoho CRM"], ["Salesforce"], ["HubSpot"], ["a local CRM"], ["Bitrix24"], ["Pipedrive"], ["Freshsales"]]
SRC_IN = ["99acres", "MagicBricks", "Housing.com", "NoBroker", "Facebook ads", "Google ads", "walk-ins", "referrals", "Instagram", "our website", "OLX"]
SRC_AE = ["Property Finder", "Bayut", "Dubizzle", "Facebook ads", "Google ads", "referrals", "our website", "Instagram", "walk-ins"]
CITIES_IN = ["Mumbai", "Pune", "Bengaluru", "Hyderabad", "Gurugram", "Noida", "Delhi", "Ahmedabad", "Chennai", "Kolkata", "Jaipur",
             "Navi Mumbai", "Thane", "Kochi", "Chandigarh", "Lucknow", "Indore", "Surat", "Goa", "Coimbatore"]
CITIES_AE = ["Dubai", "Abu Dhabi"]
FIRST = ["Aarav", "Neha", "Rohit", "Sana", "Imran", "Priya", "Karthik", "Farah", "Vikram", "Ayesha", "Rahul", "Meera", "Zaid", "Tanvi", "Omar",
         "Deepa", "Arjun", "Leena", "Harish", "Nadia", "Sameer", "Kavya", "Yusuf", "Pooja", "Nikhil", "Rhea", "Faisal", "Anita", "Varun", "Hina"]
W1 = ["Skyline", "Harbour", "Crescent", "Keystone", "Bluegate", "Northstar", "Palm", "Urban", "Cedar", "Meridian", "Horizon", "Oakwood", "Silverline",
      "Marina", "Summit", "Lotus", "Coral", "Granite", "Amber", "Riverside", "Evergreen", "Pinnacle", "Sapphire", "Banyan", "Monsoon", "Saffron",
      "Falcon", "Dune", "Ivory", "Laurel", "Orchid", "Terrace", "Compass", "Anchor", "Maple", "Lighthouse", "Gulmohar", "Neem", "Juniper"]
W2 = ["Realty", "Estates", "Properties", "Homes", "Brokers", "Realtors", "Property Consultants", "Spaces", "Living", "Advisory"]
NAMES = [a + " " + b for a in W1 for b in W2]
R.shuffle(NAMES)
PH = [0]


def nm():
    return NAMES.pop()


# (scenario, flavor list, roles [(role, seniority)], market, kinds, agent choices, lead choices)
OWN = [("founder", "owner"), ("owner", "owner"), ("managing partner", "owner"), ("director", "executive"), ("CEO", "executive")]
MGR = [("sales manager", "manager"), ("branch manager", "manager"), ("team lead", "manager"), ("operations head", "manager")]
IC = [("agent", "individual_contributor"), ("leasing executive", "individual_contributor"), ("relationship manager", "individual_contributor")]

FAMS = [
    ("resale_boundary_six", ["resale brokerage"], OWN, "in", "HHHNPP", [6, 6, 5, 6, 5, 6], [120, 99, 100, 150, 180, 140]),
    ("resale_twenty_team", ["resale housing agency"], OWN, "in", "HHNPPG", [20, 19, 20, 21, 19, 20], [500, 499, 520, 480, 600, 510]),
    ("rental_desk_ninety_nine", ["rentals-first agency"], OWN + MGR, "in", "HNNPPR", [8, 9, 7, 10, 12, 11], [99, 100, 99, 100, 98, 101]),
    ("luxury_villas_dubai", ["luxury villa brokerage"], OWN, "ae", "HHNPPG", [14, 22, 9, 30, 18, 25], [250, 400, 180, 600, 300, 350]),
    ("nri_desk_pune", ["brokerage with a dedicated NRI desk"], OWN + MGR, "in", "HHNPRP", [12, 15, 7, 20, 9, 11], [200, 300, 150, 450, 220, 260]),
    ("franchise_network_hq", ["franchise property network"], [("franchise head", "executive"), ("CEO", "executive"), ("COO", "executive")], "in", "HHNNPP", [140, 220, 110, 180, 300, 125], [3000, 5000, 2500, 4000, 8000, 2800]),
    ("two_person_shop", ["two-person resale shop"], OWN, "in", "GGNPPH", [2, 2, 2, 2, 2, 2], [30, 40, 25, 60, 45, 35]),
    ("commercial_leasing_bkc", ["commercial office leasing firm"], OWN + MGR, "in", "HHNPPR", [16, 25, 12, 19, 20, 8], [150, 300, 110, 99, 500, 120]),
    ("abu_dhabi_rentals", ["residential leasing agency"], OWN + MGR, "ae", "HNNPPG", [10, 6, 15, 5, 8, 12], [300, 200, 500, 90, 150, 250]),
    ("big_firm_satisfied_crm", ["large resale brokerage"], OWN + MGR, "in", "NNNPPG", [120, 150, 105, 200, 130, 160], [2000, 3000, 1500, 4000, 2500, 1800]),
    ("declined_browser", ["small rentals office", "resale brokerage"], MGR + IC, "in", "GGGPPG", [4, 7, 3, 9, 5, 6], [40, 80, 20, 120, 60, 50]),
    ("agents_span_review", ["mid-size brokerage"], OWN, "in", "RRRPPR", [None] * 6, [300, 250, 600, 150, 400, 200]),
    ("leads_span_review", ["brokerage"], OWN + MGR, "in", "RRRPPR", [12, 25, 8, 30, 14, 9], [None] * 6),
    ("unsatisfied_zoho", ["resale and rentals agency"], OWN + MGR, "in", "HHNNPP", [18, 24, 11, 35, 7, 21], [400, 700, 150, 900, 110, 650]),
    ("dubai_offplan_resale", ["secondary-market brokerage"], OWN + MGR, "ae", "HHNPPP", [28, 40, 19, 55, 20, 33], [800, 1200, 499, 1500, 500, 900]),
    ("evaluator_for_md", ["resale brokerage"], MGR, "in", "HHNNPP", [9, 16, 23, 11, 7, 19], [200, 350, 500, 140, 100, 300]),
    ("chennai_family_firm", ["family-run property agency"], OWN, "in", "HNNPPG", [6, 8, 5, 7, 6, 4], [100, 130, 99, 110, 105, 70]),
    ("hyderabad_it_corridor", ["rentals and resale brokerage"], OWN + MGR, "in", "HHNPPR", [13, 26, 10, 17, 20, 14], [350, 700, 200, 499, 500, 300]),
    ("kolkata_commercial_retail", ["retail shop leasing agency"], OWN, "in", "HNGPPN", [5, 6, 3, 8, 5, 6], [60, 99, 30, 100, 80, 120]),
    ("gurugram_luxury_floors", ["luxury builder-floor brokerage"], OWN, "in", "HHNPPR", [11, 20, 7, 19, 15, 9], [180, 260, 120, 499, 210, 150]),
    ("walkin_heavy_ahmedabad", ["walk-in heavy resale office"], OWN + MGR, "in", "HNNPPG", [6, 10, 5, 12, 8, 4], [150, 220, 100, 280, 130, 90]),
    ("instagram_first_boutique", ["boutique brokerage"], OWN, "in", "HHNPPG", [5, 6, 6, 5, 7, 3], [100, 140, 99, 120, 160, 70]),
    ("hundred_plus_mumbai", ["brokerage"], [("CEO", "executive"), ("head of sales", "executive"), ("founder", "owner")], "in", "HHHPPN", [110, 180, 250, 140, 160, 300], [2500, 4000, 6000, 3000, 3500, 7000]),
    ("pg_coliving_rentals", ["co-living and PG rental agency"], OWN, "in", "HNNPPG", [7, 5, 9, 6, 8, 4], [300, 150, 500, 200, 250, 120]),
    ("jaipur_plots_resale", ["resale plots and villas agency"], OWN, "in", "HNNPPG", [6, 9, 5, 8, 7, 3], [100, 150, 60, 200, 99, 40]),
    ("dubai_holiday_homes", ["holiday-home and short-let brokerage"], OWN + MGR, "ae", "HHNPPR", [12, 19, 8, 20, 15, 10], [400, 499, 250, 520, 300, 350]),
    ("franchise_outlet_owner", ["franchise outlet of a national brokerage"], OWN, "in", "HNNPPG", [8, 6, 12, 5, 10, 7], [150, 100, 220, 90, 180, 120]),
    ("leasing_agent_ic", ["commercial leasing firm"], IC, "in", "NNGPPG", [25, 14, 40, 18, 30, 9], [300, 200, 600, 180, 450, 100]),
    ("bengaluru_startup_brokerage", ["tech-led rental brokerage"], OWN, "in", "HHNPPR", [15, 22, 9, 30, 12, 18], [600, 900, 300, 1200, 499, 700]),
    ("warehouse_leasing", ["industrial and warehouse leasing brokerage"], OWN + MGR, "in", "HNNPPG", [7, 9, 6, 12, 8, 5], [100, 120, 99, 150, 110, 40]),
    ("abu_dhabi_luxury_sales", ["luxury apartment brokerage"], OWN, "ae", "HHNPPR", [9, 20, 6, 19, 14, 11], [150, 500, 100, 499, 220, 180]),
    ("noida_resale_correction", ["resale brokerage"], OWN, "in", "CCCPPC", [22, 18, 30, 21, 8, 24], [400, 300, 600, 250, 150, 500]),
    ("kochi_nri_resale", ["NRI-focused resale agency"], OWN + MGR, "in", "HNNPPG", [6, 10, 5, 8, 7, 3], [120, 200, 99, 160, 140, 50]),
    ("thane_rental_chain", ["chain of rental offices"], OWN, "in", "HHNPPP", [35, 48, 20, 60, 25, 40], [900, 1500, 500, 2000, 700, 1100]),
    ("goa_second_homes", ["second-home and villa brokerage"], OWN, "in", "HNGPPR", [5, 7, 2, 6, 4, 8], [99, 120, 30, 100, 80, 150]),
    ("dubai_commercial_office", ["office and retail leasing brokerage"], OWN + MGR, "ae", "HHNPPG", [10, 17, 6, 22, 12, 5], [200, 350, 100, 450, 250, 60]),
    ("later_financial_year", ["resale brokerage"], OWN, "in", "NNNNPP", [14, 26, 9, 18, 30, 11], [300, 700, 150, 450, 900, 200]),
    ("chandigarh_about_numbers", ["resale and rentals agency"], OWN + MGR, "in", "HHNPPR", [20, 6, 19, 5, 12, 25], [500, 100, 499, 99, 300, 600]),
    ("delhi_satisfied_small", ["small resale office"], OWN, "in", "GGNPPG", [3, 4, 5, 2, 6, 4], [40, 70, 90, 20, 110, 50]),
    ("surat_diamond_district_leasing", ["commercial leasing agency"], OWN, "in", "HNNPPP", [6, 8, 11, 5, 7, 9], [100, 140, 180, 99, 130, 160]),
    ("indore_growing_team", ["fast-growing resale brokerage"], OWN, "in", "HHNPPG", [19, 20, 15, 21, 12, 4], [499, 500, 300, 520, 250, 60]),
    ("mumbai_nri_luxury", ["luxury sea-view apartment brokerage"], OWN, "in", "HHNPPR", [16, 12, 25, 9, 20, 14], [220, 180, 400, 120, 350, 250]),
    ("lucknow_new_agency", ["newly launched brokerage"], OWN, "in", "HNGPPN", [6, 5, 2, 7, 4, 6], [100, 99, 20, 130, 50, 110]),
    ("coimbatore_rental_resale", ["rental and resale office"], OWN + MGR, "in", "HNNPPG", [8, 6, 10, 5, 7, 3], [150, 100, 200, 99, 120, 45]),
]


def ev_add(ev, key, tid):
    ev.setdefault(key, [])
    if tid not in ev[key]:
        ev[key].append(tid)


ROWS = []


def build(fam, flavors, roles, market, kind, a_in, l_in):
    """kind: H handoff, N nurture, G graceful close, R review (band-spanning), C correction handoff, P partial."""
    ae = market == "ae"
    city = R.choice(CITIES_AE if ae else CITIES_IN)
    countries = ["UAE"] if ae else ["India"]
    role, sen = R.choice(roles)
    name = nm()
    cname = R.choice(FIRST)
    flavor = R.choice(flavors)
    srcs = R.sample(SRC_AE if ae else SRC_IN, R.choice([1, 2, 2, 3]))
    partial = kind == "P"
    base = R.choice("HNG") if partial else kind
    # plan facts
    agents, leads = a_in, l_in
    satisfied = "satisfied_crm" in fam or fam.endswith("small")
    if base in "HRC":
        proc = R.choice(["manual", "manual", "unsatisfied_crm"])
        npain = 2
        inf = "approver" if sen in ("owner", "executive") else "sponsored_evaluator"
        nxt, consent = "within_30_days", True
        if base == "R" and R.random() < 0.3:
            nxt, consent = "later", False
    elif base == "N":
        proc = "satisfied_crm" if satisfied else R.choice(["manual", "unsatisfied_crm"])
        npain = R.choice([1, 2]) if not satisfied else 1
        inf = "approver" if sen in ("owner", "executive") else R.choice(["sponsored_evaluator", "none"])
        nxt, consent = R.choice([("later", True), ("later", False), ("within_30_days", False), ("later", False)])
    else:  # G
        if satisfied or R.random() < 0.5:
            proc, npain = "satisfied_crm", 0
            inf = "approver" if sen == "owner" else "none"
            nxt, consent = R.choice([("declined", False), ("later", False)])
        else:
            proc, npain, inf, nxt, consent = R.choice(["manual", "unsatisfied_crm"]), 1, "approver" if sen == "owner" else "none", "declined", False
    if inf == "approver" and sen in ("manager", "individual_contributor"):
        inf = "sponsored_evaluator"
    if sen == "individual_contributor" and base in "HC":
        inf = "sponsored_evaluator"
    tools = R.choice(TOOLS_MANUAL if proc == "manual" else TOOLS_CRM)
    pains = R.sample([p for p in PAINS if ("CRM" in p) == (proc == "unsatisfied_crm")], npain) if npain else []
    if proc == "unsatisfied_crm" and npain == 2:
        pains = [R.choice([p for p in PAINS if "CRM" in p]), R.choice([p for p in PAINS if "CRM" not in p])]
    use_email = R.random() < 0.55
    PH[0] += 1
    phone = (f"+971 50 000 1{PH[0]:03d}" if ae else f"+91 90000 1{PH[0]:04d}")
    email = f"{cname.lower()}@{name.lower().replace(' ', '')}.example.com"

    L = {"role": None, "sen": "unknown"}
    ev = {}
    turns = [opener()]
    fmt = dict(role=role, name=name, flavor=flavor, city=city)
    CUR.clear(); CUR.update(fmt)

    def V(text):
        turns.append(text)
        return len(turns)

    no_role = base == "G" and sen == "individual_contributor" and R.random() < 0.5
    t = V(pick(INTRO_NOROLE if no_role else INTRO, fmt))
    L.update(name=name, type="brokerage", countries=countries, cities=[city])
    for k in ("organisation.name", "organisation.type", "geography"):
        ev_add(ev, k, t)
    if not no_role:
        L.update(role=role, sen=sen)
        ev_add(ev, "role", t); ev_add(ev, "seniority", t)

    order = ["agents", "leads", "pain", "inf"]
    R.shuffle(order)
    corr_pending = None
    for slot in order:
        turns.append(R.choice(Q[slot]))
        if slot == "agents":
            if agents is None:
                lo = R.choice([4, 5, 15, 17]); hi = {4: 8, 5: 12, 15: 25, 17: 30}[lo]
                t = V(pick(AG_SPAN, dict(lo=lo, hi=hi)))
                L["agents"] = None
            elif kind == "C":
                a0 = R.choice([x for x in (12, 15, 9, 18, 16) if (x >= 20) != (agents >= 20) or x != agents] or [agents - 4])
                if a0 == agents: a0 = agents - 3
                V(pick(AG, dict(a=a0, A=str(a0))))
                corr_pending = a0
                L["agents"] = agents
                continue
            else:
                tmpl = AG_ABOUT if R.random() < 0.35 else AG
                t = V(pick(tmpl, dict(a=agents, A=str(agents))))
                L["agents"] = agents
            if L["agents"] is not None:
                ev_add(ev, "organisation.agents", t)
            else:
                pass
        elif slot == "leads":
            s = ", ".join(srcs[:-1]) + (" and " + srcs[-1] if len(srcs) > 1 else srcs[0])
            if leads is None:
                lo, hi = R.choice([(80, 150), (60, 200), (400, 700), (300, 600), (90, 120), (450, 800)])
                t = V(pick(LE_RANGE, dict(lo=lo, hi=hi, Lo=str(lo), src=s)))
                L["lmin"], L["lmax"] = lo, hi
            elif R.random() < 0.2 and leads >= 120:
                lo, hi = leads - 20, leads + 20
                band = lambda n: 3 if n >= 500 else 2 if n >= 100 else 1
                if band(lo) != band(hi):
                    lo = hi = leads
                t = V(pick(LE_RANGE if lo != hi else LE, dict(lo=lo, hi=hi, Lo=str(lo), l=leads, L=str(leads), src=s)))
                L["lmin"], L["lmax"] = lo, hi
            else:
                t = V(pick(LE, dict(l=leads, L=str(leads), src=s)))
                L["lmin"] = L["lmax"] = leads
            ev_add(ev, "monthly_leads", t); ev_add(ev, "lead_sources", t)
            L["src"] = srcs
        elif slot == "pain":
            ts = " and ".join(tools)
            if npain == 0:
                t = V(pick(TP_NOPAIN, dict(tools=ts, Tools=ts[0].upper() + ts[1:])))
            else:
                p = pains[0] if npain == 1 else f"{pains[0]}, plus {pains[1]}"
                t = V(pick(TP, dict(tools=ts, Tools=ts[0].upper() + ts[1:], pain=p)))
            L.update(tools=tools, proc=proc, pain=pains)
            for k in ("current_tooling", "process", "pain_points"):
                ev_add(ev, k, t)
        else:
            t = V(pick(INF[inf], dict(name=name)))
            L["inf"] = inf
            ev_add(ev, "influence", t)
        if corr_pending is not None and slot != "agents":
            turns.append(R.choice(["Got it, thanks.", "Understood.", "Makes sense."]))
            t = V(pick(CORR, dict(a=agents, a0=corr_pending)))
            ev["organisation.agents"] = [t]
            corr_pending = None
    if corr_pending is not None:
        turns.append("Anything else I should know about the team?")
        t = V(pick(CORR, dict(a=agents, a0=corr_pending)))
        ev["organisation.agents"] = [t]

    if partial:
        # cut after 2-4 visitor turns and relabel from what survives
        nvis = R.choice([2, 3, 3, 4])
        cut = 2 * nvis
        turns = turns[:cut]
        if R.random() < 0.4:
            turns.append(R.choice(SCREENS) + " " + R.choice(["What else should I know?", "Does that look familiar?", "Shall I go on?"]))
        keep = lambda ids: [i for i in ids if i <= cut]
        ev = {k: keep(v) for k, v in ev.items() if keep(v)}
        # agents correction partial edge: if correction was cut, label must reflect earlier statement -> avoid by C never partial
        if "organisation.agents" not in ev: L["agents"] = None
        if "monthly_leads" not in ev: L.pop("lmin", None); L.pop("lmax", None); L.pop("src", None)
        if "pain_points" not in ev: L.pop("tools", None); L.pop("proc", None); L.pop("pain", None)
        if "influence" not in ev: L.pop("inf", None)
    else:
        turns.append(R.choice(SCREENS) + " " + R.choice(ASK))
        q = R.choice(QUARTERS)
        t = V(pick(NEXT[(nxt, consent)], dict(q=q)))
        L.update(nxt=nxt, consent=consent)
        ev_add(ev, "next_step", t)
        if consent:
            ev_add(ev, "consent", t)
            turns.append(R.choice(ASKC))
            tmpl = [c for c in CONTACT if ("{email}" in c) == use_email]
            t = V(pick(tmpl, dict(email=email, phone=phone, cname=cname)))
            L["cname"] = cname if "{cname}" in turns[-1] or cname in turns[-1] else None
            if use_email: L["email"] = email
            else: L["phone"] = phone
            ev_add(ev, "contact", t)
        if inf == "none" and "influence" in ev:
            pass
    tr = [{"turn_id": i + 1, "speaker": "beacon" if i % 2 == 0 else "visitor", "text": x} for i, x in enumerate(turns)]
    lab = {"role": L.get("role"), "seniority": L.get("sen", "unknown"),
           "organisation": {"name": L.get("name"), "type": "brokerage", "agents": L.get("agents")},
           "pain_points": L.get("pain"), "current_tooling": L.get("tools"), "process": L.get("proc", "unknown"),
           "geography": {"countries": L.get("countries"), "cities": L.get("cities")},
           "monthly_leads": {"min": L.get("lmin"), "max": L.get("lmax")}, "lead_sources": L.get("src"),
           "influence": L.get("inf", "unknown"), "next_step": L.get("nxt", "unknown"), "consent": L.get("consent", False),
           "contact": {"name": L.get("cname"), "email": L.get("email"), "phone": L.get("phone")},
           "evidence": {k: sorted(v) for k, v in ev.items()}}
    ROWS.append({"id": f"b11-{len(ROWS) + 1:03d}", "family": f"brokerage/b11_{fam}", "language": "en", "partial": partial,
                 "transcript": tr, "label": lab})


for fam, flavors, roles, market, kinds, A, Lz in FAMS:
    for k, a, l in zip(kinds, A, Lz):
        build(fam, flavors, roles, market, k, a, l)
# top up to 250 with extra partials/handoffs spread across families
extra = "PHPNHP"
i = 0
while len(ROWS) < 250:
    fam, flavors, roles, market, kinds, A, Lz = FAMS[i % len(FAMS)]
    j = (i // len(FAMS)) % 6
    build(fam, flavors, roles, market, extra[i % len(extra)] if "C" not in kinds else "P", A[j], Lz[j])
    i += 1

ROWS = ROWS[:250]
OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ROWS), "utf-8")
print(len(ROWS), "rows ->", OUT)
