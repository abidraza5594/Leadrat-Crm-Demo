"""Batch 10: code-mixed Indian conversations (Hinglish, Devanagari, Indian number words, Tamil/Telugu/Marathi mix).

Each visitor turn carries the facts it states; labels and evidence are accumulated from those turns, so a
partial transcript (cut after a visitor turn) is labelled only with what was said so far, and a correction
simply overrides the earlier value and its evidence.
"""
import json
from pathlib import Path

OUT = str(Path(__file__).resolve().parents[1] / "data" / "raw" / "batch_10.jsonl")
rows = []

B = lambda t: ('b', t, {})
def V(t, **facts): return ('v', t, facts)

PATH = {'role': 'role', 'sen': 'seniority', 'name': 'organisation.name', 'typ': 'organisation.type',
        'agents': 'organisation.agents', 'pains': 'pain_points', 'tools': 'current_tooling', 'proc': 'process',
        'cities': 'geography', 'leads': 'monthly_leads', 'src': 'lead_sources', 'inf': 'influence',
        'nxt': 'next_step', 'consent': 'consent', 'cname': 'contact', 'email': 'contact', 'phone': 'contact'}

def build(turns):
    f, ev = {}, {}
    for i, (s, _, facts) in enumerate(turns, 1):
        for k, val in facts.items():
            if k == 'pains_add':
                f['pains'] = (f.get('pains') or []) + val
                ev.setdefault('pain_points', []).append(i); continue
            if val in (None, 'unknown'): continue
            f[k] = val
            p = PATH[k]
            if p == 'contact': ev.setdefault('contact', []); ev['contact'] = sorted(set(ev['contact'] + [i]))
            else: ev[p] = [i]
    lmin, lmax = f.get('leads', (None, None))
    cities = f.get('cities')
    return {"role": f.get('role'), "seniority": f.get('sen', 'unknown'),
            "organisation": {"name": f.get('name'), "type": f.get('typ', 'unknown'), "agents": f.get('agents')},
            "pain_points": f.get('pains'), "current_tooling": f.get('tools'), "process": f.get('proc', 'unknown'),
            "geography": {"countries": ["India"] if cities else None, "cities": cities},
            "monthly_leads": {"min": lmin, "max": lmax}, "lead_sources": f.get('src'),
            "influence": f.get('inf', 'unknown'), "next_step": f.get('nxt', 'unknown'), "consent": f.get('consent', False),
            "contact": {"name": f.get('cname'), "email": f.get('email'), "phone": f.get('phone')}, "evidence": ev}

SEEN = set()
TAGS = {"hinglish": [" yaar", ", sach bolu toh", " bhai", ", seedhi baat", " ji", ", haan", ", samjhe na", " boss", ", bas"],
        "hi": [" जी", ", सच कहूँ तो", " भाई", ", बस"],
        "en": [", honestly", " to be frank", ", basically", ", that's it", " really"]}

def uniq(text, lang):
    """Chat fillers keep repeated template lines distinct across examples."""
    base, n = text, 0
    while text.lower() in SEEN:
        tag = TAGS[lang][n % len(TAGS[lang])] + ("" if n < len(TAGS[lang]) else " " + "!" * (n // len(TAGS[lang])))
        text = base.rstrip(".") + tag; n += 1
    SEEN.add(text.lower()); return text

def E(fam, lang, turns, cut=None):
    if cut: turns = turns[:cut]
    turns = [(s, uniq(x, lang) if s == 'v' else x, f) for s, x, f in turns]
    t = [{"turn_id": i + 1, "speaker": "beacon" if s == 'b' else "visitor", "text": x} for i, (s, x, _) in enumerate(turns)]
    rows.append({"id": "b10-%03d" % (len(rows) + 1), "family": fam, "language": lang, "partial": bool(cut),
                 "transcript": t, "label": build(turns)})

CUTS = [None, None, None, None, 6, 4]      # last two of every family are partial
CUTS3 = [None, None, None, 8, 6, 4]        # last three partial

# ---------------- Hinglish (70) ----------------
# H1 brokerage: Mumbai-style WhatsApp chaos, consent in Hindi
for i, (nm, co, area, ag, lw, ln, ph) in enumerate([
    ("Sameer", "Harbour Line Realty", "Mumbai", 22, "saadhe teen sau", 350, "+91 90000 10101"),
    ("Kunal", "Borivali Nest Brokers", "Mumbai", 14, "dhai sau", 250, "+91 90000 10102"),
    ("Firoz", "Mira Road Homes", "Mumbai", 9, "dedh sau", 150, "+91 90000 10103"),
    ("Pritesh", "Thane Keys Realty", "Thane", 31, "paanch sau", 500, "+91 90000 10104"),
    ("Aslam", "Kurla Square Properties", "Mumbai", 17, "chaar sau", 400, "+91 90000 10105"),
    ("Hemant", "Vashi Crest Realtors", "Navi Mumbai", 26, "teen sau", 300, "+91 90000 10106")]):
    T = [B("Namaste! Beacon here, Leadrat ka demo assistant. Aapka business kya hai?"),
         V(f"Boss, {co} naam hai, {area} mein resale ka kaam, main {nm}, owner.", role="owner", sen="owner", name=co, typ="brokerage", cities=[area]),
         B("Sales team kitni badi hai?"),
         V(f"{ag} bande hai field pe, sab ka alag WhatsApp group bana hua hai", agents=ag),
         B("Aur mahine ki leads kitni aati hai, kahan se?"),
         V(f"Approx {lw} leads, zyada tar MagicBricks aur Instagram se", leads=(ln, ln), src=["MagicBricks", "Instagram"]),
         B("Abhi leads kaise manage hoti hai?"),
         V(f"Sab WhatsApp pe forward hota hai bhai, {ag} groups mein lead kho jaati hai aur koi follow-up nahi karta",
           tools=["WhatsApp"], proc="manual", pains=["leads get lost across WhatsApp groups", "no follow-up"]),
         B("Here is the unified Lead Inbox with WhatsApp built in. Decision aap hi loge?"),
         V(f"Haan, paisa mera hai, main hi final karunga. {nm} bol raha hoon, is mahine setup chahiye", inf="approver", nxt="within_30_days", cname=nm),
         B("Should our sales team give you a call?"),
         V(f"Haan call kar lena, {ph} pe, shaam ke baad", consent=True, phone=ph)]
    E("brokerage/mumbai_whatsapp_chaos", "hinglish", T, CUTS[i])

# H2 developer: Pune launch, crore budget (not leads), sponsored evaluator
for i, (co, prj, cr, ln, lw, ag, boss) in enumerate([
    ("Sahyadri Constructions", "Hinjewadi", "80 crore", 700, "saat sau", 20, "MD sir"),
    ("Mulshi Greens Developers", "Baner", "120 crore", 450, "saadhe chaar sau", 12, "chairman"),
    ("Kharadi Heights Infra", "Kharadi", "45 crore", 300, "teen sau", 8, "director sahab"),
    ("Wakad Skyline Projects", "Wakad", "200 crore", 900, "nau sau", 35, "promoter"),
    ("Hadapsar Vista Builders", "Hadapsar", "60 crore", 250, "dhai sau", 10, "owner"),
    ("Undri Meadows Realty", "Undri", "30 crore", 180, "ek sau assi", 6, "CMD")]):
    T = [B("Hi, I'm Beacon. Kaunsa project hai aapka?"),
         V(f"Hum {co} hai, Pune ke {prj} mein naya tower launch ho raha hai, project ka size {cr} ka hai", name=co, typ="developer", cities=["Pune"]),
         B("Launch ke time leads kitni expect kar rahe ho?"),
         V(f"Abhi {lw} leads per month aa rahi hai, Google ads aur channel partners se. {cr} budget ka matlab leads nahi hai haan", leads=(ln, ln), src=["Google ads", "channel partners"]),
         B("Sales mein kitne log hai?"),
         V(f"In-house sales {ag} log. Main sales manager hoon", agents=ag, role="sales manager", sen="manager"),
         B("Biggest problem kya lag raha hai?"),
         V("CP ki leads aur direct leads overlap hoti hai, aur site visit ka data Excel mein hai",
           pains=["channel partner and direct leads overlap", "site visit data scattered"], tools=["Excel"], proc="manual"),
         B("Here's the project-wise pipeline and CP attribution. Final approval kiska hoga?"),
         V(f"Main evaluate kar raha hoon, final {boss} karenge", inf="sponsored_evaluator"),
         B("Would you like a follow-up from our team?"),
         V("Launch ke baad dekhenge, do teen mahine baad", nxt="later")]
    E("developer/pune_launch_crore_budget", "hinglish", T, CUTS3[i])

# H3 channel partner: Delhi NCR, correction on team size
for i, (co, city, a1, a2, ln, lw) in enumerate([
    ("Dwarka Link Associates", "Delhi", 30, 45, 600, "chhe sau"),
    ("Sohna Road Partners", "Gurgaon", 12, 18, 220, "do sau bees"),
    ("Greater Noida Realty Hub", "Greater Noida", 8, 11, 130, "ek sau tees"),
    ("Faridabad Prime CP", "Faridabad", 25, 21, 400, "chaar sau"),
    ("Noida Expressway Advisors", "Noida", 40, 52, 800, "aath sau"),
    ("Ghaziabad Key Partners", "Ghaziabad", 5, 7, 90, "nabbe")]):
    T = [B("Hello ji! Beacon here. Aap developer ho ya channel partner?"),
         V(f"Channel partner hai, {co}, {city} side, kai builders ka inventory bechte hai", typ="channel_partner", name=co, cities=[city]),
         B("Team kitni hai?"),
         V(f"{a1} log hai", agents=a1),
         B("Leads kitni aati hai?"),
         V(f"Nahi nahi, {a1} nahi, {a2} log hai team mein, naye joinees bhool gaya. Leads {lw} ke aas paas", agents=a2, leads=(ln, ln)),
         B("Leads kahan se aati hai aur kaise track karte ho?"),
         V("Builders ke portal se aur Facebook campaigns se, track Google Sheets pe, builder ko registration proof dena mushkil hota hai",
           src=["builder portals", "Facebook campaigns"], tools=["Google Sheets"], proc="manual", pains=["hard to give builders registration proof"]),
         B("Here's lead registration with timestamps per builder. Aap decide karte ho?"),
         V("Main partner hoon, sign main hi karunga, agle hafte se chalu karna hai", role="partner", sen="owner", inf="approver", nxt="within_30_days")]
    E("channel_partner/ncr_team_size_correction", "hinglish", T, CUTS[i])

# H4 brokerage: Lucknow, explicit decline
for i, (co, ag, ln, lw, area) in enumerate([
    ("Gomti Nagar Estates", 10, 120, "ek sau bees", "Gomti Nagar"),
    ("Hazratganj Property Mart", 6, 80, "assi", "Hazratganj"),
    ("Aliganj Homes", 15, 200, "do sau", "Aliganj"),
    ("Indira Nagar Realty", 4, 60, "saath", "Indira Nagar"),
    ("Awadh Space Brokers", 20, 300, "teen sau", "Jankipuram"),
    ("Charbagh Plot Deals", 7, 100, "sau", "Charbagh")]):
    T = [B("Aadaab! Beacon here. Aap kya dekhna chahenge?"),
         V(f"Hum Lucknow mein {area} se {co} chalate hai, plots aur flats", name=co, typ="brokerage", cities=["Lucknow"]),
         B("Team size aur monthly leads?"),
         V(f"{ag} agent hai, leads mahine mein {lw} ke kareeb, zyadatar reference se", agents=ag, leads=(ln, ln), src=["references"]),
         B("Abhi kya use karte ho?"),
         V("Register aur diary, kabhi kabhi WhatsApp. Koi dikkat nahi hai waise", tools=["register", "diary", "WhatsApp"], proc="manual", pains=[]),
         B("Here's how the mobile app logs calls. Kya sales team aapse baat kare?"),
         V(f"Nahi bhai, mat karna call. Bas dekh raha tha, {co} ko abhi zaroorat nahi", nxt="declined")]
    E("brokerage/lucknow_decline_call", "hinglish", T, CUTS[i])

# H5 other real estate: Indore property management / co-living
for i, (co, kind, units, ag, ln, lw) in enumerate([
    ("Malwa Stay Co-living", "co-living", "400 beds", 9, 250, "dhai sau"),
    ("Vijay Nagar Rentals", "rental management", "150 flats", 5, 90, "nabbe"),
    ("Rajwada PG Network", "PG chain", "600 beds", 12, 350, "saadhe teen sau"),
    ("Indore Facility Keepers", "property management", "80 buildings", 18, 60, "saath"),
    ("Palasia Hostels", "student housing", "300 beds", 7, 150, "dedh sau"),
    ("Super Corridor Leasing", "commercial leasing", "40 offices", 4, 40, "chaalis")]):
    T = [B("Hi! Beacon here. Aapka business batao?"),
         V(f"Hum Indore mein {kind} karte hai, {co}, total {units} manage karte hai", name=co, typ="other_real_estate", cities=["Indore"]),
         B("Enquiries kitni aati hai?"),
         V(f"Mahine ki {lw} enquiries, NoBroker aur Google Maps se", leads=(ln, ln), src=["NoBroker", "Google Maps"]),
         B("Team?"),
         V(f"{ag} log handle karte hai calls", agents=ag),
         B("Main problem kya hai?"),
         V("Visit ke baad koi follow-up nahi hota, aur rent renewal ka reminder bhi manual hai",
           pains=["no follow-up after visits", "manual rent renewal reminders"], proc="manual"),
         B("Here's the follow-up scheduler. Kaun decide karega?"),
         V("Operations head hoon, owner se baat karni padegi", role="operations head", sen="manager", inf="sponsored_evaluator")]
    E("other_real_estate/indore_rental_ops", "hinglish", T, CUTS3[i])

# H6 developer: Hyderabad, unhappy with current CRM
for i, (co, crm, ag, ln, lw, area) in enumerate([
    ("Kokapet Towers Pvt Ltd", "LeadSquared", 28, 1200, "barah sau", "Kokapet"),
    ("Tellapur Greens", "Zoho CRM", 14, 500, "paanch sau", "Tellapur"),
    ("Nizampet Habitat", "HubSpot", 9, 260, "do sau saath", "Nizampet"),
    ("Shamshabad Infra", "Salesforce", 40, 1500, "pandrah sau", "Shamshabad"),
    ("Kompally Crest Homes", "Zoho CRM", 11, 320, "teen sau bees", "Kompally"),
    ("Miyapur Metro Residency", "Freshsales", 16, 700, "saat sau", "Miyapur")]):
    T = [B("Hello, I'm Beacon. What should I show you first?"),
         V(f"Hum {co} hai, Hyderabad {area} mein gated community bana rahe hai", name=co, typ="developer", cities=["Hyderabad"]),
         B("Currently kaunsa tool hai?"),
         V(f"{crm} use karte hai but site visit tracking nahi hai usme aur WhatsApp alag chalta hai",
           tools=[crm, "WhatsApp"], proc="unsatisfied_crm", pains=["no site visit tracking", "WhatsApp is separate from CRM"]),
         B("Team size and leads?"),
         V(f"{ag} sales executives, leads {lw} per month, Housing.com aur Facebook se", agents=ag, leads=(ln, ln), src=["Housing.com", "Facebook"]),
         B("Here's the site-visit calendar. Kab tak switch karna hai?"),
         V("Main VP sales hoon, budget mera hai. Is mahine hi shift karna hai", role="VP sales", sen="executive", inf="approver", nxt="within_30_days"),
         B("Can we share your details with sales?"),
         V(f"Haan, email karo vp@{co.split()[0].lower()}.example.com", consent=True, email=f"vp@{co.split()[0].lower()}.example.com")]
    E("developer/hyderabad_crm_switch", "hinglish", T, CUTS[i])

# H7 brokerage: Bengaluru, numbers in words
for i, (co, area, ag_w, ag, lw, ln) in enumerate([
    ("Sarjapur Roots Realty", "Sarjapur", "baara", 12, "dedh sau", 150),
    ("HSR Keystone Brokers", "HSR Layout", "pachees", 25, "saadhe paanch sau", 550),
    ("Hebbal Lakeview Homes", "Hebbal", "aath", 8, "sawa sau", 125),
    ("Yelahanka Plot Point", "Yelahanka", "bees", 20, "ek hazaar", 1000),
    ("Electronic City Nest", "Electronic City", "chhe", 6, "pauney do sau", 175),
    ("Marathahalli Home Hub", "Marathahalli", "tees", 30, "saadhe saat sau", 750)]):
    T = [B("Hey, Beacon here! Kis type ka business hai?"),
         V(f"Bengaluru {area} mein brokerage hai, {co}", name=co, typ="brokerage", cities=["Bengaluru"]),
         B("How many agents?"),
         V(f"{ag_w} agents hai abhi", agents=ag),
         B("Monthly leads?"),
         V(f"Har mahine {lw} leads, Square Yards aur walk-ins", leads=(ln, ln), src=["Square Yards", "walk-ins"]),
         B("Kya dikkat hai abhi?"),
         V("Excel mein data duplicate ho jata hai aur agents apne phone pe leads rakh lete hai",
           tools=["Excel"], proc="manual", pains=["duplicate data in Excel", "agents keep leads on personal phones"]),
         B("Here is duplicate detection and lead ownership. Aap decide karte ho?"),
         V("Main co-founder hoon, dono founders milke sign karenge, next month dekhte hai", role="co-founder", sen="owner", inf="approver", nxt="later")]
    E("brokerage/bengaluru_number_words", "hinglish", T, CUTS[i])

# H8 channel partner: Mumbai, evaluating for boss
for i, (co, city, ag, ln, lw) in enumerate([
    ("Powai Channel Connect", "Mumbai", 24, 480, "chaar sau assi"),
    ("Panvel Realty Partners", "Panvel", 13, 210, "do sau das"),
    ("Kalyan CP Network", "Kalyan", 9, 140, "ek sau chaalis"),
    ("Chembur Deal Makers", "Mumbai", 33, 650, "saadhe chhe sau"),
    ("Dombivli Property Link", "Dombivli", 7, 110, "ek sau das"),
    ("Ghatkopar Realty Associates", "Mumbai", 19, 390, "teen sau nabbe")]):
    T = [B("Hi, Beacon here. Kya explore karna hai aaj?"),
         V(f"Main {co} mein team lead hoon, hum channel partner hai {city} mein", role="team lead", sen="manager", name=co, typ="channel_partner", cities=[city]),
         B("Kitne log hai team mein?"),
         V(f"Total {ag} sourcing managers", agents=ag),
         B("Leads per month?"),
         V(f"Karib {lw}, Meta ads aur builder referrals", leads=(ln, ln), src=["Meta ads", "builder referrals"]),
         B("Abhi kaise track hota hai?"),
         V("WhatsApp broadcast aur ek Excel, commission ka hisaab baar baar galat hota hai",
           tools=["WhatsApp", "Excel"], proc="manual", pains=["commission calculations go wrong"]),
         B("Here is the commission tracker. Decision kaun lega?"),
         V("Mere boss lenge, main unke liye shortlist bana raha hoon", inf="sponsored_evaluator")]
    E("channel_partner/mumbai_evaluating_for_boss", "hinglish", T, CUTS3[i])

# H9 brokerage: Pune, later next quarter
for i, (co, area, ag, ln, lw) in enumerate([
    ("Kothrud Corner Realty", "Kothrud", 11, 160, "ek sau saath"),
    ("Viman Nagar Leasing Co", "Viman Nagar", 23, 520, "paanch sau bees"),
    ("Aundh Address Brokers", "Aundh", 7, 95, "pachanave"),
    ("Magarpatta Move-in", "Magarpatta", 16, 280, "do sau assi"),
    ("PCMC Homes Direct", "Pimpri", 28, 610, "chhe sau das"),
    ("Sinhagad Road Estates", "Sinhagad Road", 5, 70, "sattar")]):
    T = [B("Namaskar! Beacon here. Tell me about your firm?"),
         V(f"{co}, Pune {area}, rental aur resale dono", name=co, typ="brokerage", cities=["Pune"]),
         B("Team aur leads?"),
         V(f"{ag} agents, aur {lw} leads monthly", agents=ag, leads=(ln, ln)),
         B("What's not working today?"),
         V("Leads ka response late hota hai, raat ki enquiry subah tak koi nahi dekhta", pains=["late lead response", "night enquiries unattended"]),
         B("Here's auto-assignment with instant WhatsApp reply. When would you want to start?"),
         V("Abhi season busy hai, Diwali ke baad next quarter mein sochenge. Main proprietor hoon", nxt="later", role="proprietor", sen="owner", inf="approver")]
    E("brokerage/pune_after_diwali", "hinglish", T, CUTS[i])

# H10 developer: NCR, lead volume correction
for i, (co, city, l1, l2, lw2, ag) in enumerate([
    ("Aravali Crest Developers", "Gurgaon", 300, 800, "aath sau", 22),
    ("Yamuna Park Infratech", "Noida", 1000, 600, "chhe sau", 18),
    ("Golf Course Extension Homes", "Gurgaon", 150, 250, "dhai sau", 10),
    ("Raj Nagar Extension Builders", "Ghaziabad", 500, 350, "saadhe teen sau", 14),
    ("Dwarka Expressway Towers", "Gurgaon", 2000, 1200, "barah sau", 45),
    ("Bhiwadi Affordable Homes", "Bhiwadi", 80, 120, "ek sau bees", 6)]):
    T = [B("Welcome, main Beacon hoon. Project ke baare mein batao?"),
         V(f"{co}, {city} mein affordable housing project hai, 2 aur 3 BHK", name=co, typ="developer", cities=[city]),
         B("Monthly leads?"),
         V(f"{l1} leads aati hai", leads=(l1, l1)),
         B("Aur sales team?"),
         V(f"Nahi nahi, {l1} nahi yaar, pichle mahine {lw2} thi, wahi average hai. Team {ag} logon ki hai", leads=(l2, l2), agents=ag),
         B("Kya use karte ho aur kya problem hai?"),
         V("Purana in-house software hai, usme ads ka ROI nahi dikhta", tools=["in-house software"], proc="unsatisfied_crm", pains=["cannot see ad ROI"]),
         B("Here's the source-wise ROI report. Can our sales team call you?"),
         V(f"Theek hai, haan call kar lena. Main GM marketing hoon, gm@{co.split()[0].lower()}.example.com",
           consent=True, role="GM marketing", sen="executive", email=f"gm@{co.split()[0].lower()}.example.com")]
    E("developer/ncr_lead_count_correction", "hinglish", T, CUTS3[i])

# H11 other real estate: home loan DSAs / interiors
for i, (co, kind, city, ag, ln, lw) in enumerate([
    ("EMI Saathi Loans", "home loan DSA", "Lucknow", 15, 300, "teen sau"),
    ("Grihapravesh Interiors", "home interiors", "Pune", 8, 120, "ek sau bees"),
    ("Sukoon Vastu Consultants", "vastu consultancy", "Indore", 3, 40, "chaalis"),
    ("Chabi Loan Point", "home loan DSA", "Delhi", 25, 900, "nau sau"),
    ("Nayi Deewar Interiors", "modular interiors", "Hyderabad", 12, 200, "do sau"),
    ("Registry Mitra Services", "property legal services", "Mumbai", 6, 80, "assi")]):
    T = [B("Hi, Beacon here. Aap real estate mein kya karte ho?"),
         V(f"Hum {kind} hai, {co}, {city} mein builders ke customers ko serve karte hai", name=co, typ="other_real_estate", cities=[city]),
         B("Kitni leads aur team?"),
         V(f"{lw} leads mahine ki, {ag} log ki team", leads=(ln, ln), agents=ag),
         B("How do you manage them?"),
         V("Sab WhatsApp aur paper files pe, customer documents dhoondhne mein time jata hai",
           tools=["WhatsApp", "paper files"], proc="manual", pains=["time wasted finding customer documents"]),
         B("Here's the document checklist per lead. Decision kiska hai?"),
         V("Mera hi business hai, main owner", role="owner", sen="owner", inf="approver")]
    E("other_real_estate/allied_services_hinglish", "hinglish", T, CUTS[i])

# H12 brokerage: mixed Hinglish/Devanagari, with budgets in lakh
for i, (lang, co, city, ag, ln, lw, bud) in enumerate([
    ("hinglish", "Banjara Hills Luxe Realty", "Hyderabad", 21, 330, "teen sau tees", "80 lakh se 2 crore"),
    ("hinglish", "Rajendra Nagar Property Hub", "Indore", 9, 140, "ek sau chaalis", "30 se 60 lakh"),
    ("hi", "Kanpur Road Realty", "Lucknow", 12, 180, "एक सौ अस्सी", "40 से 70 लाख"),
    ("hinglish", "Wagholi Starter Homes", "Pune", 6, 75, "pachattar", "35 lakh"),
    ("hi", "Saket Vihar Estates", "Delhi", 18, 260, "दो सौ साठ", "1.5 करोड़"),
    ("hinglish", "Jubilee Keys Brokers", "Hyderabad", 27, 560, "paanch sau saath", "1 se 3 crore")]):
    if lang == "hi":
        T = [B("नमस्ते! मैं Beacon हूँ। आपका काम क्या है?"),
             V(f"हम {city} में brokerage करते हैं, {co}. हमारे ज़्यादातर buyers {bud} budget वाले हैं", name=co, typ="brokerage", cities=[city]),
             B("Leads per month कितनी हैं?"),
             V(f"महीने की {lw} leads, 99acres से", leads=(ln, ln), src=["99acres"]),
             B("Team size?"),
             V(f"{ag} agents हैं", agents=ag),
             B("अभी leads कहाँ रखते हैं?"),
             V("Excel में, और follow-up की तारीख अक्सर भूल जाते हैं", tools=["Excel"], proc="manual", pains=["follow-up dates forgotten"])]
    else:
        T = [B("Hi there! Beacon from Leadrat. Aapka setup kya hai?"),
             V(f"{co}, {city}. Buyers ka budget {bud} hota hai, woh leads nahi hai, budget hai", name=co, typ="brokerage", cities=[city]),
             B("Samjha. Leads kitni aati hai?"),
             V(f"{lw} leads per month, 99acres se", leads=(ln, ln), src=["99acres"]),
             B("Team size?"),
             V(f"{ag} agents", agents=ag),
             B("Leads kahan rakhte ho?"),
             V("Excel mein, follow-up date yaad nahi rehti", tools=["Excel"], proc="manual", pains=["follow-up dates forgotten"])]
    T += [B("Here's the follow-up calendar. Who signs off?"),
          V("मैं owner हूँ, फैसला मेरा" if lang == "hi" else f"Main owner hoon {co} ka, faisla mera", role="owner", sen="owner", inf="approver")]
    E("brokerage/lakh_budget_not_leads", lang, T, CUTS[i])

# ---------------- Devanagari (18 more) ----------------
for i, (co, city, ag, ln, lw, nm, ph) in enumerate([
    ("सरस्वती रियल्टी", "Lucknow", 14, 220, "दो सौ बीस", "Vivek", "+91 90000 10201"),
    ("गंगा होम्स", "Delhi", 32, 700, "सात सौ", "Rakesh", "+91 90000 10202"),
    ("नर्मदा प्रॉपर्टीज़", "Indore", 8, 130, "एक सौ तीस", "Anil", "+91 90000 10203"),
    ("यमुना एस्टेट्स", "Noida", 19, 350, "साढ़े तीन सौ", "Deepak", "+91 90000 10204"),
    ("कावेरी रियल एस्टेट", "Bengaluru", 11, 180, "एक सौ अस्सी", "Sunil", "+91 90000 10205"),
    ("चंबल लैंड डील्स", "Gwalior", 5, 60, "साठ", "Manoj", "+91 90000 10206")]):
    T = [B("नमस्ते, मैं Beacon हूँ। बताइए कैसे मदद करूँ?"),
         V(f"मैं {nm}, {co} का मालिक, {city} में brokerage है", role="owner", sen="owner", name=co, typ="brokerage", cities=[city], cname=nm),
         B("आपकी team कितनी बड़ी है?"),
         V(f"{ag} agents हैं हमारे पास", agents=ag),
         B("और हर महीने कितनी leads आती हैं?"),
         V(f"लगभग {lw} leads, Facebook और 99acres से", leads=(ln, ln), src=["Facebook", "99acres"]),
         B("सबसे बड़ी परेशानी क्या है?"),
         V("सब कुछ WhatsApp पर चलता है, कौन सा agent किस lead पर है पता ही नहीं चलता",
           tools=["WhatsApp"], proc="manual", pains=["no visibility on which agent owns which lead"]),
         B("यह रहा Leads list, हर lead का owner साफ़ दिखता है। कब शुरू करना चाहेंगे?"),
         V("इसी महीने शुरू करना है, फैसला मेरा ही है", inf="approver", nxt="within_30_days"),
         B("क्या हमारी sales team आपको call कर सकती है?"),
         V(f"हाँ call कर लेना, नंबर {ph}", consent=True, phone=ph)]
    E("brokerage/devanagari_owner_consent", "hi", T, CUTS[i])

for i, (co, city, ag, ln, lw, role) in enumerate([
    ("श्री बालाजी डेवलपर्स", "Jaipur", 15, 400, "चार सौ", "sales head"),
    ("अन्नपूर्णा बिल्डकॉन", "Indore", 9, 250, "ढाई सौ", "marketing manager"),
    ("शिवालिक इंफ्रा", "Chandigarh", 20, 600, "छह सौ", "sales head"),
    ("विंध्य होम्स", "Bhopal", 7, 150, "डेढ़ सौ", "CRM manager"),
    ("गोमती ग्रीन्स", "Lucknow", 12, 300, "तीन सौ", "sales manager"),
    ("अरावली टाउनशिप", "Gurgaon", 25, 900, "नौ सौ", "sales head")]):
    T = [B("नमस्ते! Beacon यहाँ। आप developer हैं?"),
         V(f"जी हाँ, {co}, {city} में हमारा township project है। मैं {role} हूँ", name=co, typ="developer", cities=[city], role=role, sen="manager"),
         B("Sales team और leads?"),
         V(f"{ag} लोग sales में, और महीने में {lw} enquiries", agents=ag, leads=(ln, ln)),
         B("Site visits कैसे manage होते हैं?"),
         V("रजिस्टर में लिखते हैं, visit के बाद follow-up नहीं होता और no-show बहुत है",
           tools=["register"], proc="manual", pains=["no follow-up after site visits", "many site visit no-shows"]),
         B("यह Site Visit screen है, reminders अपने आप जाते हैं। Final decision कौन लेगा?"),
         V("मैं देख रहा हूँ, MD साहब final करेंगे", inf="sponsored_evaluator")]
    E("developer/devanagari_site_visits", "hi", T, CUTS3[i])

# Only 2 devanagari examples came from H12, so this family has 6 -> 2+6+6+6 = 20
for i, (co, city, ag, ln, lw) in enumerate([
    ("भारत रियल्टी पार्टनर्स", "Delhi", 16, 320, "तीन सौ बीस"),
    ("मालवा चैनल नेटवर्क", "Indore", 10, 150, "डेढ़ सौ"),
    ("अवध प्रॉपर्टी लिंक", "Lucknow", 6, 90, "नब्बे"),
    ("सह्याद्रि पार्टनर्स", "Pune", 22, 450, "साढ़े चार सौ"),
    ("गोदावरी रियल्टी", "Nashik", 8, 120, "एक सौ बीस"),
    ("दक्कन चैनल पार्टनर्स", "Hyderabad", 13, 260, "दो सौ साठ")]):
    T = [B("नमस्कार, मैं Beacon हूँ। आप किस तरह का काम करते हैं?"),
         V(f"हम {city} में channel partner हैं, {co}", name=co, typ="channel_partner", cities=[city]),
         B("कितने लोग और कितनी leads?"),
         V(f"{ag} लोग हैं, {lw} leads हर महीने", agents=ag, leads=(ln, ln)),
         B("Leads कहाँ से आती हैं?"),
         V("Builders से और Instagram ads से। Google Sheets में रखते हैं, ठीक चल रहा है",
           src=["builders", "Instagram ads"], tools=["Google Sheets"], proc="manual"),
         B("यह Leadrat का CP dashboard है। क्या हमारी team आपसे संपर्क करे?"),
         V("नहीं, call मत करना। अभी ज़रूरत नहीं है", nxt="declined")]
    E("channel_partner/devanagari_decline", "hi", T, CUTS[i])

# ---------------- English with Indian number words (15) ----------------
for i, (co, city, ag_w, ag, lw, ln, src) in enumerate([
    ("Coastal Keys Realty", "Chennai", "two dozen", 24, "do sau", 200, ["99acres", "walk-ins"]),
    ("Lakeside Brokers", "Bhopal", "ten", 10, "dedh hazaar", 1500, ["Facebook ads"]),
    ("Silver Oak Realtors", "Ahmedabad", "fifteen", 15, "saadhe teen sau", 350, ["MagicBricks"]),
    ("Metro Nest Realty", "Kolkata", "thirty", 30, "ek hazaar", 1000, ["Google ads", "portals"]),
    ("Riverbend Properties", "Surat", "eight", 8, "dhai sau", 250, ["Instagram"]),
    ("Hilltop Homes Realty", "Dehradun", "five", 5, "pachaas", 50, ["references"])]):
    T = [B("Hello, I'm Beacon. What does your company do?"),
         V(f"We're {co}, a brokerage in {city}. I'm the managing partner.", name=co, typ="brokerage", cities=[city], role="managing partner", sen="owner"),
         B("How big is the team?"),
         V(f"About {ag_w} agents.", agents=ag),
         B("And monthly leads?"),
         V(f"Roughly {lw} leads a month, mostly from {' and '.join(src)}.", leads=(ln, ln), src=src),
         B("What's the main pain?"),
         V("Nobody knows which leads went cold. We run everything on Excel and phone calls.", pains=["cannot see which leads went cold"], tools=["Excel"], proc="manual"),
         B("Here's the lead ageing report. Who decides?"),
         V("I sign. Let's do it within a couple of weeks.", inf="approver", nxt="within_30_days"),
         B("May our sales team contact you?"),
         V(f"Sure, write to me at partner@{co.split()[0].lower()}.example.com", consent=True, email=f"partner@{co.split()[0].lower()}.example.com")]
    E("brokerage/english_indian_number_words", "en", T, CUTS[i])

for i, (co, city, bud, lw, ln, ag) in enumerate([
    ("Evergreen Habitat Developers", "Nagpur", "sixty lakh per unit, not per square foot", "do sau pachaas", 250, 14),
    ("Blue Horizon Constructions", "Coimbatore", "forty lakh to one crore", "chaar sau", 400, 11),
    ("Sunmark Infra", "Vadodara", "fifty-five lakh", "saadhe paanch sau", 550, 19),
    ("Ridgeline Estates", "Mysuru", "one and a half crore", "sau", 100, 7),
    ("Crescent Bay Builders", "Visakhapatnam", "seventy lakh", "teen sau", 300, 9),
    ("Orchid Valley Projects", "Kochi", "two crore plus", "dedh sau", 150, 6)]):
    T = [B("Hi, Beacon here. Tell me about your project."),
         V(f"{co}, residential project in {city}. Ticket size is {bud}, just so you know.", name=co, typ="developer", cities=[city]),
         B("How many enquiries per month?"),
         V(f"About {lw} enquiries a month right now.", leads=(ln, ln)),
         B("Sales team?"),
         V(f"{ag} people in-house.", agents=ag),
         B("What are you using?"),
         V("We have Zoho but the team doesn't update it and follow-ups slip.", tools=["Zoho"], proc="unsatisfied_crm", pains=["team doesn't update the CRM", "follow-ups slip"])]
    T += [B("Here's the mobile app with one-tap call logging. Who is the decision maker?"),
          V(f"I'm the director at {co}, my call. Maybe next quarter.", role="director", sen="executive", inf="approver", nxt="later")]
    E("developer/english_lakh_ticket_size", "en", T, CUTS3[i])

# Channel partner family: 3 English number words, 3 regional mix
CP = [
    ("en", "Primeway Channel Partners", "Chennai", "twenty", 20, "teen sau", 300,
     "Hi, we're Primeway Channel Partners in Chennai, we sell for five builders.",
     "Registration disputes with builders, every month we lose ek do deals.", ["registration disputes with builders"]),
    ("en", "Keystone CP Network", "Pune", "twelve", 12, "dedh sau", 150,
     "Keystone CP Network, Pune. We're a channel partner firm.",
     "Site visit proof is on WhatsApp photos, builders reject half of it.", ["builders reject site visit proof"]),
    ("en", "Unity Realty Partners", "Ahmedabad", "nine", 9, "sau", 100,
     "Unity Realty Partners from Ahmedabad, channel partner.",
     "Leads from different builders get mixed and we double-call people.", ["leads from different builders get mixed", "double calling"]),
    ("en", "Chennai Gateway Partners", "Chennai", "padinaaru", 16, "irunooru", 200,
     "Vanakkam, Chennai Gateway Partners, channel partner for OMR projects.",
     "Romba confusion in commission, and follow-up miss aagudhu.", ["commission confusion", "missed follow-ups"]),
    ("en", "Godavari Link Partners", "Hyderabad", "padi", 10, "nooru yabhai", 150,
     "Namaskaram, Godavari Link Partners, Hyderabad, we are channel partners.",
     "Chaala leads waste avuthunnayi, no tracking at all.", ["leads wasted", "no tracking"]),
    ("en", "Mauli Realty Partners", "Pune", "pandhra", 15, "don she", 200,
     "Namaskar, Mauli Realty Partners, Pune madhe channel partner aahe.",
     "Khup leads WhatsApp var harvtat, follow-up hot nahi.", ["leads lost on WhatsApp", "no follow-up"])]
for i, (lang, co, city, ag_w, ag, lw, ln, intro, pain, pains) in enumerate(CP):
    T = [B("Hello! I'm Beacon. What's your business?"),
         V(intro, name=co, typ="channel_partner", cities=[city]),
         B("How many people and how many leads?"),
         V(f"Team is {ag_w} people, leads around {lw} monthly", agents=ag, leads=(ln, ln)),
         B("What's the biggest issue?"),
         V(pain, pains=pains),
         B("Here's builder-wise lead registration. Are you the decision maker?"),
         V(f"Yes, I own {co}. Send someone next week.", role="owner", sen="owner", inf="approver", nxt="within_30_days")]
    E("channel_partner/cp_number_words_regional", lang, T, [None, None, 6, None, None, 4][i])

# ---------------- Tamil / Telugu / Marathi mix (12 more) ----------------
for i, (co, city, greet, ag, ln, lw, pain_line, pains, tools, proc) in enumerate([
    ("Anna Nagar Realty", "Chennai", "Vanakkam", 18, 300, "munnooru",
     "Ellam Excel la dhaan, follow-up romba late aagudhu.", ["late follow-ups"], ["Excel"], "manual"),
    ("Velachery Homes", "Chennai", "Vanakkam sir", 7, 100, "nooru",
     "WhatsApp la leads miss aagudhu, yaarum track pannala.", ["leads missed on WhatsApp"], ["WhatsApp"], "manual"),
    ("Madhapur Realty Point", "Hyderabad", "Namaskaram", 22, 450, "naalugu vandala yabhai",
     "Maaku CRM undi kani reports correct ga raavu.", ["reports are inaccurate"], ["CRM"], "unsatisfied_crm"),
    ("Gachibowli Nest Brokers", "Hyderabad", "Hello andi", 12, 200, "rendu vandalu",
     "Agents leads ni personal phone lo pettukuntunnaru, chaala problem.", ["agents keep leads on personal phones"], None, "unknown"),
    ("Tambaram Plot Hub", "Chennai", "Vanakkam", 5, 60, "arubadhu",
     "Diary la ezhudhuvom, site visit maranthu poyidum.", ["site visits forgotten"], ["diary"], "manual"),
    ("Kukatpally Keys Realty", "Hyderabad", "Namaskaram andi", 30, 800, "enimidi vandalu",
     "Excel lo duplicate leads, same customer ki mugguru call chestaru.", ["duplicate leads", "same customer called by several agents"], ["Excel"], "manual")]):
    T = [B("Hi! Beacon here. What kind of real estate business?"),
         V(f"{greet}, {co}, {city}, resale brokerage.", name=co, typ="brokerage", cities=[city]),
         B("Team size?"),
         V(f"{ag} agents in the team", agents=ag),
         B("Monthly leads?"),
         V(f"Around {lw} leads per month", leads=(ln, ln)),
         B("What's the main problem?"),
         V(pain_line, **({"pains": pains, "proc": proc} | ({"tools": tools} if tools else {}))),
         B("Here's round-robin assignment and follow-up reminders. Can sales contact you?"),
         V("Ippo vendaam, call pannadheenga please." if city == "Chennai" and i % 2 else "Sure, next week call cheyyandi, owner nene." if city == "Hyderabad" else "Yes, call me, I'm the owner, this month itself.",
           **({"nxt": "declined"} if city == "Chennai" and i % 2 else {"nxt": "within_30_days", "consent": True, "role": "owner", "sen": "owner", "inf": "approver"}))]
    E("brokerage/tamil_telugu_mix", "en", T, CUTS3[i])

for i, (co, city, ag, ln, lw, bud) in enumerate([
    ("Shivneri Developers", "Pune", 14, 350, "saadhe teen she", "75 lakh"),
    ("Sahyadri Heights", "Nashik", 8, 150, "dedhshe", "45 lakh"),
    ("Konkan Coast Projects", "Ratnagiri", 5, 80, "ainshi", "1 crore"),
    ("Deccan Plateau Infra", "Aurangabad", 11, 220, "donshe vees", "50 lakh"),
    ("Panchganga Homes", "Kolhapur", 9, 180, "ekshe ainshi", "40 lakh"),
    ("Vidarbha Greens", "Nagpur", 17, 400, "chaarshe", "65 lakh")]):
    T = [B("Namaskar! I'm Beacon. What are you building?"),
         V(f"Aamhi {co}, {city} madhe residential project aahe, flat price around {bud}", name=co, typ="developer", cities=[city]),
         B("How many leads a month?"),
         V(f"Mahinyala {lw} leads yetat, mostly Facebook ani newspaper", leads=(ln, ln), src=["Facebook", "newspaper"]),
         B("Sales team?"),
         V(f"{ag} lok aahet sales madhe", agents=ag),
         B("What's hard today?"),
         V("Sagla Excel madhe aahe, site visit nantar follow-up hot nahi", tools=["Excel"], proc="manual", pains=["no follow-up after site visits"]),
         B("Here's the site-visit follow-up flow. Who takes the final call?"),
         V("Mi sales head aahe, pan final nirnay maalak ghetil", role="sales head", sen="manager", inf="sponsored_evaluator")]
    E("developer/marathi_mix", "en", T, CUTS[i])

with open(OUT, "w", encoding="utf-8") as fh:
    for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(len(rows), "rows ->", OUT)
