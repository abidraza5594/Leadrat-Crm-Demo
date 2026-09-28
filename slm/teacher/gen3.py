import json, os
OUT = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "data" / "raw" / "batch_3.jsonl")
HERE = os.path.dirname(os.path.abspath(__file__))
EX = []
def ex(family, lang, partial, turns, **lab):
    t = [{"turn_id": i+1, "speaker": "beacon" if s.startswith("B:") else "visitor", "text": s[2:].strip()} for i, s in enumerate(turns)]
    label = {"role": None, "seniority": "unknown", "organisation": {"name": None, "type": "unknown", "agents": None},
             "pain_points": None, "current_tooling": None, "process": "unknown", "geography": {"countries": None, "cities": None},
             "monthly_leads": {"min": None, "max": None}, "lead_sources": None, "influence": "unknown", "next_step": "unknown",
             "consent": False, "contact": {"name": None, "email": None, "phone": None}, "evidence": {}}
    for k, v in lab.items():
        if k in ("org", "geo", "leads", "contact"):
            key = {"org": "organisation", "geo": "geography", "leads": "monthly_leads", "contact": "contact"}[k]
            label[key].update(v)
        elif k == "ev": label["evidence"] = v
        else: label[k] = v
    EX.append({"id": f"b3-{len(EX)+1:03d}", "family": family, "language": lang, "partial": partial, "transcript": t, "label": label})

CPH = "channel_partner/multi_developer_high_fit"
ex(CPH, "en", False, [
 "B: Hi, I'm Beacon. Want a quick look at how Leadrat handles leads?",
 "V: Yes. We're Skyline Realty Partners, a channel partner in Pune. We sell inventory for about 12 developers on commission.",
 "B: Nice. How big is the sales team and how many leads come in a month?",
 "V: 34 sales guys. Roughly 900 leads a month from 99acres, MagicBricks and Facebook ads.",
 "B: What are you using to track them today?",
 "V: Excel sheets and WhatsApp groups. Leads get lost between developers and we can't track site visits properly.",
 "B: Here is the Leads list, filtered by project and developer, with site-visit status on each row.",
 "V: That's exactly what we need. I'm the founder, I sign off on this.",
 "B: Great. Can our sales team contact you this week?",
 "V: Yes please. rohan.test@example.com, +91 90000 03101. We want to start within the month."],
 role="founder", seniority="owner", org={"name": "Skyline Realty Partners", "type": "channel_partner", "agents": 34},
 pain_points=["leads lost between developers", "can't track site visits"], current_tooling=["Excel", "WhatsApp"], process="manual",
 geo={"countries": ["India"], "cities": ["Pune"]}, leads={"min": 900, "max": 900}, lead_sources=["99acres", "MagicBricks", "Facebook ads"],
 influence="approver", next_step="within_30_days", consent=True, contact={"email": "rohan.test@example.com", "phone": "+91 90000 03101"},
 ev={"role": [8], "seniority": [8], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [4], "pain_points": [6], "current_tooling": [6],
     "process": [6], "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [10], "consent": [10], "contact": [10]})
ex(CPH, "hinglish", False, [
 "B: Namaste! Main Beacon hoon. Leadrat ka demo dekhna chahenge?",
 "V: Haan. Hum Hyderabad mein channel partner hain, 8-9 builders ka inventory bechte hain. Firm ka naam Deccan Homes Connect.",
 "B: Team kitni badi hai?",
 "V: 25 log hain sales mein. Leads mahine ke 600 ke aas paas aate hain, zyada tar Housing.com aur Google ads se.",
 "B: Abhi leads kahan manage karte ho?",
 "V: Google Sheets mein. Follow-up miss ho jaata hai aur builder ko lead ownership prove karna mushkil hai.",
 "B: Yeh dekhiye Lead Details screen, har lead pe source aur tagging timestamp ke saath.",
 "V: Badhiya. Main director hoon, decision mera hi hai. Sales team call kar sakti hai, 90000 03102 pe. Is mahine hi lena hai."],
 role="director", seniority="executive", org={"name": "Deccan Homes Connect", "type": "channel_partner", "agents": 25},
 pain_points=["missed follow-ups", "hard to prove lead ownership to builders"], current_tooling=["Google Sheets"], process="manual",
 geo={"countries": ["India"], "cities": ["Hyderabad"]}, leads={"min": 600, "max": 600}, lead_sources=["Housing.com", "Google ads"],
 influence="approver", next_step="within_30_days", consent=True, contact={"phone": "+91 90000 03102"},
 ev={"role": [8], "seniority": [8], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [4], "pain_points": [6], "current_tooling": [6],
     "process": [6], "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8], "consent": [8], "contact": [8]})
ex(CPH, "en", False, [
 "B: Hello! I'm Beacon, Leadrat's demo guide. What brings you here?",
 "V: I run sales at Gulf Key Properties in Dubai. We're a channel partner for off-plan projects from several developers.",
 "B: How many agents, and roughly how many leads monthly?",
 "V: 42 agents. Around 1,200 leads a month from Bayut, Property Finder and Instagram.",
 "B: And your current setup?",
 "V: We use Zoho CRM but it can't split leads by developer project, and commission tracking is a mess.",
 "B: Here's the Projects view: every lead mapped to a developer project, with a commission column.",
 "V: Nice. I'm evaluating this for our CEO, he makes the final call.",
 "B: Understood. Shall our team follow up with you?",
 "V: Sure, go ahead. amira.test@example.com. We'd like to move in the next few weeks."],
 role="head of sales", seniority="executive", org={"name": "Gulf Key Properties", "type": "channel_partner", "agents": 42},
 pain_points=["can't split leads by developer project", "commission tracking is a mess"], current_tooling=["Zoho CRM"], process="unsatisfied_crm",
 geo={"countries": ["UAE"], "cities": ["Dubai"]}, leads={"min": 1200, "max": 1200}, lead_sources=["Bayut", "Property Finder", "Instagram"],
 influence="sponsored_evaluator", next_step="within_30_days", consent=True, contact={"email": "amira.test@example.com"},
 ev={"role": [2], "seniority": [2], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [4], "pain_points": [6], "current_tooling": [6],
     "process": [6], "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [10], "consent": [10], "contact": [10]})
ex(CPH, "en", False, [
 "B: Hi, Beacon here. Can I show you how Leadrat works for channel partners?",
 "V: Go ahead. We're a CP firm in Bengaluru, Northgate Estates, working with 15 developers.",
 "B: Team size?",
 "V: We were 20 last quarter, actually 28 now after hiring.",
 "B: Lead volume and sources?",
 "V: About 700 a month. Mostly developer-shared leads plus NoBroker and our website.",
 "B: What's hurting most today?",
 "V: Duplicate leads across developers and no visibility into who called whom. All on Excel.",
 "B: Here's the Duplicate Check screen, it flags the same buyer across projects.",
 "V: Good. I'm a partner in the firm, I can approve it. Have someone call me, 90000 03104, ideally next week."],
 role="partner", seniority="owner", org={"name": "Northgate Estates", "type": "channel_partner", "agents": 28},
 pain_points=["duplicate leads across developers", "no visibility into calls"], current_tooling=["Excel"], process="manual",
 geo={"countries": ["India"], "cities": ["Bengaluru"]}, leads={"min": 700, "max": 700}, lead_sources=["developer-shared leads", "NoBroker", "website"],
 influence="approver", next_step="within_30_days", consent=True, contact={"phone": "+91 90000 03104"},
 ev={"role": [10], "seniority": [10], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [4], "pain_points": [8], "current_tooling": [8],
     "process": [8], "geography": [2], "monthly_leads": [6], "lead_sources": [6], "influence": [10], "next_step": [10], "consent": [10], "contact": [10]})
ex(CPH, "en", False, [
 "B: Welcome! I'm Beacon. What would you like to see?",
 "V: We're Horizon Channel Partners, Gurgaon. We sell for about 10 developers, big and boutique.",
 "B: How many in sales and leads per month?",
 "V: 60 advisors, 2000-2500 leads monthly from portals and Facebook.",
 "B: How do you manage them now?",
 "V: Honestly manually, Excel and WhatsApp. Reporting takes days and managers can't see agent activity.",
 "B: This is the Reports dashboard, agent-wise calls, visits and conversions live.",
 "V: I'm the COO. I'd need our MD to approve but I'll push it.",
 "B: Can sales reach out to you?",
 "V: Not right now, maybe next quarter. I'll come back myself."],
 role="COO", seniority="executive", org={"name": "Horizon Channel Partners", "type": "channel_partner", "agents": 60},
 pain_points=["reporting takes days", "no visibility into agent activity"], current_tooling=["Excel", "WhatsApp"], process="manual",
 geo={"countries": ["India"], "cities": ["Gurgaon"]}, leads={"min": 2000, "max": 2500}, lead_sources=["portals", "Facebook"],
 influence="sponsored_evaluator", next_step="later",
 ev={"role": [8], "seniority": [8], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [4], "pain_points": [6], "current_tooling": [6],
     "process": [6], "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [10]})

SOLO = "channel_partner/solo_agent"
ex(SOLO, "en", False, [
 "B: Hi, I'm Beacon. How can I help?",
 "V: I'm an independent channel partner in Jaipur, just me and one assistant. I sell projects from 3 local builders.",
 "B: How many leads do you handle a month?",
 "V: Maybe 40 or so, from Facebook and referrals.",
 "B: What do you use to keep track?",
 "V: A notebook and WhatsApp. I forget follow-ups sometimes.",
 "B: Here's the mobile app's Today view, showing follow-ups due.",
 "V: Looks neat. I own the business so it's my decision, but I'm not buying right now.",
 "B: Should our team contact you later?",
 "V: No, please don't call. I'll sign up if I need it."],
 role="owner", seniority="owner", org={"type": "channel_partner", "agents": 2}, pain_points=["forgets follow-ups"], current_tooling=["notebook", "WhatsApp"],
 process="manual", geo={"countries": ["India"], "cities": ["Jaipur"]}, leads={"min": 40, "max": 40}, lead_sources=["Facebook", "referrals"],
 influence="approver", next_step="declined",
 ev={"role": [8], "seniority": [8], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6],
     "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [10]})
ex(SOLO, "hinglish", False, [
 "B: Hello! Main Beacon. Kya dekhna chahenge aap?",
 "V: Main akela kaam karta hoon, Ahmedabad mein. Builders ke projects bechta hoon commission pe.",
 "B: Mahine mein kitne leads aate hain?",
 "V: 50-60 ke beech. Zyada tar walk-in aur 99acres se.",
 "B: Abhi kya use karte ho?",
 "V: Excel. Koi badi problem nahi, bas thoda organised rehna hai.",
 "B: Yeh simple Leads list hai, status ke saath.",
 "V: Theek hai. Mera hi business hai. Agle mahine dekhte hain, abhi call mat karna."],
 role="self-employed", seniority="owner", org={"type": "channel_partner", "agents": 1}, pain_points=[], current_tooling=["Excel"], process="manual",
 geo={"countries": ["India"], "cities": ["Ahmedabad"]}, leads={"min": 50, "max": 60}, lead_sources=["walk-ins", "99acres"],
 influence="approver", next_step="later",
 ev={"role": [2], "seniority": [2], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6], "geography": [2],
     "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8]})
ex(SOLO, "en", False, [
 "B: Hi there, Beacon here. What are you looking for?",
 "V: I'm a freelance property consultant in Chennai. I resell developer inventory, basically a one-man channel partner.",
 "B: Roughly how many enquiries a month?",
 "V: About 25.",
 "B: And tracking?",
 "V: Phone contacts and WhatsApp labels. I lose track of which project a buyer liked.",
 "B: Here's the Lead Details page, noting project interest per buyer.",
 "V: Cool. It's just me, I decide. You can email me, karthik.test@example.com, I might start this month."],
 role="freelance property consultant", seniority="owner", org={"type": "channel_partner", "agents": 1},
 pain_points=["loses track of project interest per buyer"], current_tooling=["phone contacts", "WhatsApp"], process="manual",
 geo={"countries": ["India"], "cities": ["Chennai"]}, leads={"min": 25, "max": 25}, influence="approver", next_step="within_30_days", consent=True,
 contact={"email": "karthik.test@example.com"},
 ev={"role": [2], "seniority": [2], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6],
     "geography": [2], "monthly_leads": [4], "influence": [8], "next_step": [8], "consent": [8], "contact": [8]})
ex(SOLO, "en", False, [
 "B: Hello, I'm Beacon. Want a tour?",
 "V: Sure. Small CP outfit in Kolkata, me plus 3 agents. We sell for two developers in Rajarhat.",
 "B: Leads per month?",
 "V: Around 80, mostly from Facebook ads.",
 "B: What do you use?",
 "V: We tried a free CRM but it doesn't have WhatsApp integration so nobody updates it.",
 "B: Here's WhatsApp chat inside the lead timeline.",
 "V: Nice. I'm the proprietor. Maybe after Durga Puja, not now."],
 role="proprietor", seniority="owner", org={"type": "channel_partner", "agents": 4}, pain_points=["no WhatsApp integration"], current_tooling=["free CRM"],
 process="unsatisfied_crm", geo={"countries": ["India"], "cities": ["Kolkata"]}, leads={"min": 80, "max": 80}, lead_sources=["Facebook ads"],
 influence="approver", next_step="later",
 ev={"role": [8], "seniority": [8], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6],
     "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8]})

MID = "channel_partner/partial_mid_demo"
ex(MID, "en", True, [
 "B: Hi, I'm Beacon. What can I show you?",
 "V: We're a channel partner in Navi Mumbai, working with 6 developers. Lead distribution is a pain.",
 "B: How many agents do you have?",
 "V: 18 right now.",
 "B: Here's the Auto-assignment rules screen, round robin by project."],
 org={"type": "channel_partner", "agents": 18}, pain_points=["lead distribution"], geo={"countries": ["India"], "cities": ["Navi Mumbai"]},
 ev={"organisation.type": [2], "organisation.agents": [4], "pain_points": [2], "geography": [2]})
ex(MID, "hinglish", True, [
 "B: Namaste, Beacon yahan. Demo shuru karein?",
 "V: Haan. Hum Noida mein CP hain, builders ke saath tie-up hai.",
 "B: Leads kitne aate hain mahine mein?",
 "V: 300 ke kareeb, portals se.",
 "B: Yeh Leads dashboard hai, source-wise breakdown ke saath...",
 "V: Ruko, ek call aa gaya."],
 org={"type": "channel_partner"}, geo={"countries": ["India"], "cities": ["Noida"]}, leads={"min": 300, "max": 300}, lead_sources=["portals"],
 ev={"organisation.type": [2], "geography": [2], "monthly_leads": [4], "lead_sources": [4]})
ex(MID, "en", True, [
 "B: Hello! Beacon here. Tell me a bit about your business?",
 "V: I manage the sales desk at Coastal Realty Links in Goa. We market second-home projects for developers from Mumbai and Pune.",
 "B: Great. What do you use today?",
 "V: LeadSquared, but it's too generic and the agents hate the app.",
 "B: Got it. Here is the Leadrat agent app home screen."],
 role="sales desk manager", seniority="manager", org={"name": "Coastal Realty Links", "type": "channel_partner"},
 pain_points=["CRM too generic", "agents dislike the app"], current_tooling=["LeadSquared"], process="unsatisfied_crm",
 geo={"countries": ["India"], "cities": ["Goa"]},
 ev={"role": [2], "seniority": [2], "organisation.name": [2], "organisation.type": [2], "pain_points": [4], "current_tooling": [4], "process": [4], "geography": [2]})
ex(MID, "en", True, [
 "B: Hi, I'm Beacon. Want a quick walkthrough?",
 "V: yes pls. we sell under-construction flats for multiple builders in Thane",
 "B: How big is the team?",
 "V: around 10 to 25 depending on the season",
 "B: And monthly leads?",
 "V: 400ish",
 "B: Here's the Leads list, you can bulk-upload builder sheets here."],
 org={"type": "channel_partner"}, geo={"countries": ["India"], "cities": ["Thane"]}, leads={"min": 400, "max": 400},
 ev={"organisation.type": [2], "geography": [2], "monthly_leads": [6]})
ex(MID, "en", True, [
 "B: Hello, Beacon here. What brings you by?",
 "V: Our CP firm in Lucknow is growing. 12 agents, three developer mandates.",
 "B: What's the biggest headache?",
 "V: Site visit scheduling, and agents poaching each other's leads.",
 "B: Let me show the Site Visit calendar..."],
 org={"type": "channel_partner", "agents": 12}, pain_points=["site visit scheduling", "agents poaching each other's leads"],
 geo={"countries": ["India"], "cities": ["Lucknow"]},
 ev={"organisation.type": [2], "organisation.agents": [2], "pain_points": [4], "geography": [2]})
ex(MID, "hinglish", True, [
 "B: Hi! Main Beacon hoon. Aapka business kya hai?",
 "V: Indore mein channel partner firm hai hamari, Malwa Property Point. 7 log hain team mein.",
 "B: Leads kahan se aate hain?",
 "V: Facebook aur MagicBricks. Sab Excel mein daalte hain abhi.",
 "B: Achha. Yeh dekhiye Integrations page, Facebook aur MagicBricks direct connect hote hain."],
 org={"name": "Malwa Property Point", "type": "channel_partner", "agents": 7}, current_tooling=["Excel"], process="manual",
 geo={"countries": ["India"], "cities": ["Indore"]}, lead_sources=["Facebook", "MagicBricks"],
 ev={"organisation.name": [2], "organisation.type": [2], "organisation.agents": [2], "current_tooling": [4], "process": [4], "geography": [2], "lead_sources": [4]})

NC = "channel_partner/no_consent"
ex(NC, "en", False, [
 "B: Hi, I'm Beacon. Can I help you explore Leadrat?",
 "V: Just browsing. We're a channel partner in Mumbai, around 30 agents, selling for maybe 20 developers.",
 "B: How many leads a month?",
 "V: 1000+, from 99acres, Housing and our own campaigns.",
 "B: Current tool?",
 "V: Salesforce, but it's expensive and customising for real estate is painful.",
 "B: Here's the Leadrat pipeline, built for property sales out of the box.",
 "V: I'm the VP sales and I sign contracts. We're renewing next month so timing is right.",
 "B: Would you like our team to contact you?",
 "V: No thanks, I'll reach out myself if needed."],
 role="VP sales", seniority="executive", org={"type": "channel_partner", "agents": 30}, pain_points=["expensive", "painful to customise for real estate"],
 current_tooling=["Salesforce"], process="unsatisfied_crm", geo={"countries": ["India"], "cities": ["Mumbai"]}, leads={"min": 1000, "max": None},
 lead_sources=["99acres", "Housing.com", "own campaigns"], influence="approver", next_step="within_30_days",
 ev={"role": [8], "seniority": [8], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6],
     "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8]})
ex(NC, "en", False, [
 "B: Hello! Beacon here.",
 "V: Hi. I'm a team lead at a CP firm in Pune. We have 9 agents and sell for 4 developers.",
 "B: Leads per month?",
 "V: 150 to 200.",
 "B: What's the main problem?",
 "V: Slow response to new leads, we reply hours later.",
 "B: Here's instant lead alerts with auto-assignment.",
 "V: Good, but I don't decide, I'm just checking it out. And please don't share my number with sales."],
 role="team lead", seniority="manager", org={"type": "channel_partner", "agents": 9}, pain_points=["slow response to new leads"],
 geo={"countries": ["India"], "cities": ["Pune"]}, leads={"min": 150, "max": 200}, influence="none",
 ev={"role": [2], "seniority": [2], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "geography": [2], "monthly_leads": [4], "influence": [8]})
ex(NC, "hinglish", False, [
 "B: Namaste, Beacon yahan. Demo dekhna hai?",
 "V: Haan dikhao. Hum Bengaluru mein channel partner hain, 22 agents hain.",
 "B: Leads kitne?",
 "V: 500 mahina, Google aur Facebook ads se.",
 "B: Abhi kya use karte ho?",
 "V: Sell.Do use kar rahe hain, theek hai, koi khaas problem nahi.",
 "B: Yeh hamara Leads screen hai...",
 "V: Main owner hoon. Abhi switch karne ka plan nahi hai. Contact mat karna please."],
 role="owner", seniority="owner", org={"type": "channel_partner", "agents": 22}, pain_points=[], current_tooling=["Sell.Do"], process="satisfied_crm",
 geo={"countries": ["India"], "cities": ["Bengaluru"]}, leads={"min": 500, "max": 500}, lead_sources=["Google ads", "Facebook ads"],
 influence="approver", next_step="declined",
 ev={"role": [8], "seniority": [8], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6],
     "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8]})
ex(NC, "en", False, [
 "B: Hi, I'm Beacon. Anything specific you want to see?",
 "V: We're Marina Gate Realty, a channel partner in Dubai. 15 agents, off-plan only.",
 "B: Leads a month?",
 "V: Around 350 from Property Finder and TikTok.",
 "B: Tools?",
 "V: HubSpot free tier. It doesn't track developer payment plans or commissions.",
 "B: Here's the Deal view with payment plan and commission fields.",
 "V: I'm the managing partner. We'd look at it next year, not now. Don't need a call."],
 role="managing partner", seniority="owner", org={"name": "Marina Gate Realty", "type": "channel_partner", "agents": 15},
 pain_points=["doesn't track developer payment plans", "doesn't track commissions"], current_tooling=["HubSpot"], process="unsatisfied_crm",
 geo={"countries": ["UAE"], "cities": ["Dubai"]}, leads={"min": 350, "max": 350}, lead_sources=["Property Finder", "TikTok"],
 influence="approver", next_step="later",
 ev={"role": [8], "seniority": [8], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6],
     "process": [6], "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8]})

UI = "channel_partner/unknown_influence"
ex(UI, "en", False, [
 "B: Hi! I'm Beacon. What would you like to explore?",
 "V: I work at a channel partner company in Hyderabad. We have 45 people in sales.",
 "B: How many leads?",
 "V: 800 to 1000 a month from 99acres, Facebook and developer referrals.",
 "B: What's the current process?",
 "V: Excel plus WhatsApp. No tracking of calls, and leads slip through.",
 "B: Here's call logging with recordings attached to each lead.",
 "V: Useful. I'll share this with the team.",
 "B: Can sales reach you to set up a trial?",
 "V: Yes, you can call me. 90000 03120. Soon would be good, within two weeks."],
 org={"type": "channel_partner", "agents": 45}, pain_points=["no call tracking", "leads slip through"], current_tooling=["Excel", "WhatsApp"], process="manual",
 geo={"countries": ["India"], "cities": ["Hyderabad"]}, leads={"min": 800, "max": 1000}, lead_sources=["99acres", "Facebook", "developer referrals"],
 next_step="within_30_days", consent=True, contact={"phone": "+91 90000 03120"},
 ev={"organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6], "geography": [2], "monthly_leads": [4],
     "lead_sources": [4], "next_step": [10], "consent": [10], "contact": [10]})
ex(UI, "en", False, [
 "B: Hello, Beacon here.",
 "V: Hi, I'm from Pinnacle Property Advisors, a CP in Delhi. Around 20 agents.",
 "B: Leads a month?",
 "V: 250.",
 "B: What tool?",
 "V: Kylas CRM. Reports are weak.",
 "B: Here's our Reports dashboard.",
 "V: Nice. Who signs off isn't clear yet, several people weigh in. Email me: neha.test@example.com, sales can write to me."],
 org={"name": "Pinnacle Property Advisors", "type": "channel_partner", "agents": 20}, pain_points=["weak reports"], current_tooling=["Kylas CRM"],
 process="unsatisfied_crm", geo={"countries": ["India"], "cities": ["Delhi"]}, leads={"min": 250, "max": 250}, consent=True,
 contact={"email": "neha.test@example.com"},
 ev={"organisation.name": [2], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6],
     "geography": [2], "monthly_leads": [4], "consent": [8], "contact": [8]})
ex(UI, "hinglish", False, [
 "B: Hi, Beacon hoon. Kaise help karun?",
 "V: Hum Pune aur Mumbai dono mein channel partner hain. 35 agents.",
 "B: Leads kitne aate hain?",
 "V: Kabhi 400, kabhi 700. Depend karta hai launch pe.",
 "B: Problem kya hai sabse badi?",
 "V: Lead leakage aur manager ko pata hi nahi chalta kaun kya kar raha hai. Sheets pe hai sab.",
 "B: Yeh Team Activity screen hai.",
 "V: Achha hai. Mujhe details bhej do, mera naam Vikram, vikram.test@example.com. Sales wale contact kar sakte hain."],
 org={"type": "channel_partner", "agents": 35}, pain_points=["lead leakage", "no visibility into team activity"], current_tooling=["Google Sheets"],
 process="manual", geo={"countries": ["India"], "cities": ["Pune", "Mumbai"]}, leads={"min": 400, "max": 700}, consent=True,
 contact={"name": "Vikram", "email": "vikram.test@example.com"},
 ev={"organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6], "geography": [2],
     "monthly_leads": [4], "consent": [8], "contact": [8]})
ex(UI, "en", True, [
 "B: Hi, I'm Beacon.",
 "V: hey. CP firm in Chandigarh, 14 agents, we sell for Tricity developers",
 "B: What do you use today?",
 "V: excel, and it's chaos when the developer sends 200 leads in one go",
 "B: Here's bulk import with auto-assignment."],
 org={"type": "channel_partner", "agents": 14}, pain_points=["chaos handling bulk developer leads"], current_tooling=["Excel"], process="manual",
 geo={"countries": ["India"], "cities": ["Chandigarh"]},
 ev={"organisation.type": [2], "organisation.agents": [2], "pain_points": [4], "current_tooling": [4], "process": [4], "geography": [2]})
ex(UI, "en", True, [
 "B: Welcome, I'm Beacon.",
 "V: We're Crest Channel Partners, Mumbai. I want to see lead tracking.",
 "B: Sure. How many leads monthly?",
 "V: 120 or so from Housing.com.",
 "B: Here's the Leads list..."],
 org={"name": "Crest Channel Partners", "type": "channel_partner"}, geo={"countries": ["India"], "cities": ["Mumbai"]}, leads={"min": 120, "max": 120},
 lead_sources=["Housing.com"],
 ev={"organisation.name": [2], "organisation.type": [2], "geography": [2], "monthly_leads": [4], "lead_sources": [4]})
ex(UI, "en", True, [
 "B: Hi, Beacon here. Tell me about your team?",
 "V: CP in Coimbatore. We're 6 agents. Actually 5, one just left.",
 "B: What's the main pain?",
 "V: Following up with buyers after site visits.",
 "B: Here's the follow-up reminders screen."],
 org={"type": "channel_partner", "agents": 5}, pain_points=["post-site-visit follow-ups"], geo={"countries": ["India"], "cities": ["Coimbatore"]},
 ev={"organisation.type": [2], "organisation.agents": [2], "pain_points": [4], "geography": [2]})

PM = "other_real_estate/property_management"
ex(PM, "en", False, [
 "B: Hi, I'm Beacon. What brings you here?",
 "V: We run a property management company in Bengaluru, TenantNest Services. We manage about 1,500 rental flats.",
 "B: How many people handle tenant and owner enquiries?",
 "V: 12 relationship managers.",
 "B: How many new enquiries a month?",
 "V: About 300, from NoBroker, our website and owner referrals.",
 "B: How do you track them?",
 "V: Freshdesk for tickets and Excel for leasing leads. Leasing leads go cold.",
 "B: Here's the Leads list with a leasing pipeline and reminders.",
 "V: I'm the co-founder, I decide. Yes, have sales contact me: priya.test@example.com. This month works."],
 role="co-founder", seniority="owner", org={"name": "TenantNest Services", "type": "other_real_estate", "agents": 12}, pain_points=["leasing leads go cold"],
 current_tooling=["Freshdesk", "Excel"], process="manual", geo={"countries": ["India"], "cities": ["Bengaluru"]}, leads={"min": 300, "max": 300},
 lead_sources=["NoBroker", "website", "owner referrals"], influence="approver", next_step="within_30_days", consent=True, contact={"email": "priya.test@example.com"},
 ev={"role": [10], "seniority": [10], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [4], "pain_points": [8], "current_tooling": [8],
     "process": [8], "geography": [2], "monthly_leads": [6], "lead_sources": [6], "influence": [10], "next_step": [10], "consent": [10], "contact": [10]})
ex(PM, "en", False, [
 "B: Hello, Beacon here.",
 "V: Hi. I handle operations for a property management firm in Dubai Marina. 8 leasing agents.",
 "B: Lead volume?",
 "V: 150-ish a month, Bayut and Dubizzle.",
 "B: Tools?",
 "V: Yardi for property ops. For leads we have nothing, just WhatsApp.",
 "B: Here's the WhatsApp inbox linked to leads.",
 "V: Good. My GM decides; I'm shortlisting for him. I'll send him the link."],
 role="operations", seniority="unknown", org={"type": "other_real_estate", "agents": 8}, current_tooling=["Yardi", "WhatsApp"], process="manual",
 geo={"countries": ["UAE"], "cities": ["Dubai"]}, leads={"min": 150, "max": 150}, lead_sources=["Bayut", "Dubizzle"], influence="sponsored_evaluator",
 ev={"role": [2], "organisation.type": [2], "organisation.agents": [2], "current_tooling": [6], "process": [6], "geography": [2], "monthly_leads": [4],
     "lead_sources": [4], "influence": [8]})
ex(PM, "hinglish", True, [
 "B: Namaste! Beacon yahan.",
 "V: Hum Gurgaon mein PG aur rental properties manage karte hain. Owners aur tenants dono ke leads aate hain.",
 "B: Kitne log hain team mein?",
 "V: 4 log.",
 "B: Yeh Leads screen dekhiye..."],
 org={"type": "other_real_estate", "agents": 4}, geo={"countries": ["India"], "cities": ["Gurgaon"]},
 ev={"organisation.type": [2], "organisation.agents": [4], "geography": [2]})
ex(PM, "en", False, [
 "B: Hi! I'm Beacon.",
 "V: Hello. We're a co-living operator, StayHive, with 14 properties across Pune and Hyderabad.",
 "B: How many in your sales team, and leads per month?",
 "V: 9 in sales. Around 600 leads a month from Google ads and Instagram.",
 "B: How do you manage them?",
 "V: We're on Zoho, happy with it mostly, no real complaints. Just exploring.",
 "B: Here's our Leads list for comparison.",
 "V: Thanks. I'm the marketing manager, no authority on software. We'll look again later in the year."],
 role="marketing manager", seniority="manager", org={"name": "StayHive", "type": "other_real_estate", "agents": 9}, pain_points=[],
 current_tooling=["Zoho"], process="satisfied_crm", geo={"countries": ["India"], "cities": ["Pune", "Hyderabad"]}, leads={"min": 600, "max": 600},
 lead_sources=["Google ads", "Instagram"], influence="none", next_step="later",
 ev={"role": [8], "seniority": [8], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [4], "pain_points": [6], "current_tooling": [6],
     "process": [6], "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8]})

INT = "other_real_estate/interior_firm"
ex(INT, "en", False, [
 "B: Hi, I'm Beacon. How can I help?",
 "V: We're an interior design and fit-out firm in Mumbai, Casa Craft Interiors. We get leads from new home buyers.",
 "B: How big is your sales team?",
 "V: 7 designers who also do sales.",
 "B: Leads per month?",
 "V: About 200 from Instagram, Houzz and builder tie-ups.",
 "B: How do you track them?",
 "V: Trello and WhatsApp. Quotes get lost and we don't know conversion rate.",
 "B: Here's the Pipeline view, with quote stages and a conversion report.",
 "V: I'm the owner. Yes, call me this week: 90000 03130."],
 role="owner", seniority="owner", org={"name": "Casa Craft Interiors", "type": "other_real_estate", "agents": 7},
 pain_points=["quotes get lost", "unknown conversion rate"], current_tooling=["Trello", "WhatsApp"], process="manual",
 geo={"countries": ["India"], "cities": ["Mumbai"]}, leads={"min": 200, "max": 200}, lead_sources=["Instagram", "Houzz", "builder tie-ups"],
 influence="approver", next_step="within_30_days", consent=True, contact={"phone": "+91 90000 03130"},
 ev={"role": [10], "seniority": [10], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [4], "pain_points": [8], "current_tooling": [8],
     "process": [8], "geography": [2], "monthly_leads": [6], "lead_sources": [6], "influence": [10], "next_step": [10], "consent": [10], "contact": [10]})
ex(INT, "hinglish", False, [
 "B: Hello, main Beacon.",
 "V: Hum Jaipur mein modular kitchen aur interiors ka kaam karte hain. 3 sales log hain.",
 "B: Leads kitne aate hain?",
 "V: 60-70 mahine ke, JustDial aur Facebook se.",
 "B: Tracking kaise karte ho?",
 "V: Diary mein likhte hain. Follow-up bhool jaate hain.",
 "B: Yeh follow-up reminder screen hai.",
 "V: Achha hai, par abhi budget nahi hai. Main malik hoon. Baad mein dekhenge."],
 role="owner", seniority="owner", org={"type": "other_real_estate", "agents": 3}, pain_points=["forget follow-ups"], current_tooling=["diary"], process="manual",
 geo={"countries": ["India"], "cities": ["Jaipur"]}, leads={"min": 60, "max": 70}, lead_sources=["JustDial", "Facebook"], influence="approver", next_step="later",
 ev={"role": [8], "seniority": [8], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6], "process": [6],
     "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8]})
ex(INT, "en", True, [
 "B: Hi there, Beacon here.",
 "V: We do office fit-outs in Chennai. Mainly commercial leads.",
 "B: How many leads a month?",
 "V: maybe 30-40",
 "B: Here's the Leads list with a commercial project tag..."],
 org={"type": "other_real_estate"}, geo={"countries": ["India"], "cities": ["Chennai"]}, leads={"min": 30, "max": 40},
 ev={"organisation.type": [2], "geography": [2], "monthly_leads": [4]})
ex(INT, "en", False, [
 "B: Hello! I'm Beacon.",
 "V: I'm the sales manager at Nook & Nest Interiors, Hyderabad. 11 sales consultants.",
 "B: Leads per month and sources?",
 "V: 450, mostly Facebook lead forms and home expos.",
 "B: Current system?",
 "V: Pipedrive. It's OK but no site measurement scheduling, and no WhatsApp.",
 "B: Here's the Site Visit scheduler and WhatsApp integration.",
 "V: I'm evaluating on behalf of our founder. Sure, send details to sameer.test@example.com and have someone reach out in a couple of weeks."],
 role="sales manager", seniority="manager", org={"name": "Nook & Nest Interiors", "type": "other_real_estate", "agents": 11},
 pain_points=["no site measurement scheduling", "no WhatsApp"], current_tooling=["Pipedrive"], process="unsatisfied_crm",
 geo={"countries": ["India"], "cities": ["Hyderabad"]}, leads={"min": 450, "max": 450}, lead_sources=["Facebook lead forms", "home expos"],
 influence="sponsored_evaluator", next_step="within_30_days", consent=True, contact={"email": "sameer.test@example.com"},
 ev={"role": [2], "seniority": [2], "organisation.name": [2], "organisation.type": [2], "organisation.agents": [2], "pain_points": [6], "current_tooling": [6],
     "process": [6], "geography": [2], "monthly_leads": [4], "lead_sources": [4], "influence": [8], "next_step": [8], "consent": [8], "contact": [8]})

exec(open(os.path.join(HERE, "extra.py"), encoding="utf-8").read())

ORP = "other_real_estate/partial"
ex(ORP, "en", True, [
 "B: Hi, I'm Beacon.",
 "V: Hi, I'm a home loan DSA in Pune. We get leads from builders and CPs.",
 "B: How many people on your team?",
 "V: 5 executives.",
 "B: Here's how leads show up in the Leads list..."],
 org={"type": "other_real_estate", "agents": 5}, geo={"countries": ["India"], "cities": ["Pune"]},
 ev={"organisation.type": [2], "organisation.agents": [4], "geography": [2]})
ex(ORP, "en", True, [
 "B: Hello, Beacon here. What do you do?",
 "V: Real estate consultancy in Delhi NCR. We advise investors on land and commercial deals.",
 "B: What do you use for tracking?",
 "V: Excel. And follow-ups are all over the place.",
 "B: Let me pull up the Leads dashboard..."],
 org={"type": "other_real_estate"}, pain_points=["follow-ups all over the place"], current_tooling=["Excel"], process="manual",
 geo={"countries": ["India"], "cities": ["Delhi NCR"]},
 ev={"organisation.type": [2], "pain_points": [4], "current_tooling": [4], "process": [4], "geography": [2]})
ex(ORP, "hinglish", True, [
 "B: Namaste, Beacon yahan.",
 "V: Hum home loans ka kaam karte hain, DSA hain, Ahmedabad mein. Leads 250 mahine ke.",
 "B: Leads kahan se aate hain?",
 "V: Builders ke site office se aur referrals.",
 "B: Yeh dekhiye..."],
 org={"type": "other_real_estate"}, geo={"countries": ["India"], "cities": ["Ahmedabad"]}, leads={"min": 250, "max": 250},
 lead_sources=["builder site offices", "referrals"],
 ev={"organisation.type": [2], "geography": [2], "monthly_leads": [2], "lead_sources": [4]})
ex(ORP, "en", True, [
 "B: Hi! I'm Beacon.",
 "V: We're a facility and property management company in Abu Dhabi, around 20 staff in leasing.",
 "B: What's the main problem you want to solve?",
 "V: Tracking renewals and enquiries in one place.",
 "B: Here's the Leads list with renewal reminders..."],
 org={"type": "other_real_estate", "agents": 20}, pain_points=["tracking renewals and enquiries in one place"],
 geo={"countries": ["UAE"], "cities": ["Abu Dhabi"]},
 ev={"organisation.type": [2], "organisation.agents": [2], "pain_points": [4], "geography": [2]})
ex(ORP, "en", True, [
 "B: Hello, I'm Beacon. What brings you here?",
 "V: I'm the founder of a real estate consulting startup in Kochi. Tiny team.",
 "B: How many leads a month?",
 "V: A lot, honestly, can't say a number.",
 "B: Let me show the Integrations page..."],
 role="founder", seniority="owner", org={"type": "other_real_estate"}, geo={"countries": ["India"], "cities": ["Kochi"]},
 ev={"role": [2], "seniority": [2], "organisation.type": [2], "geography": [2]})

assert len(EX) == 40, len(EX)
with open(OUT, "w", encoding="utf-8") as f:
    for e in EX: f.write(json.dumps(e, ensure_ascii=False) + "\n")
print(sum(e["label"]["organisation"]["type"] == "channel_partner" for e in EX), sum(e["partial"] for e in EX), sum(e["language"] == "hinglish" for e in EX))
