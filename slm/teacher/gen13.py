"""Batch 13: organisation-type discrimination in English.

The first visitor turn(s) carry the phrase that decides organisation.type: developer mandates vs resale
commission, CP vs brokerage, adjacent real-estate services (other_real_estate), businesses outside real
estate (unrelated) and visitors who never say what they do (unknown). Families share sentence frames so
near-miss pairs differ only in the key phrase. Facts ride on visitor turns; labels and evidence are
accumulated from them, so partial transcripts are labelled with what was said so far.
"""
import json
import random
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = RAW / "batch_13.jsonl"
R = random.Random(1313)

# Visitor lines already used in other batches (must not be repeated).
SEEN = set()
for f in RAW.glob("batch_*.jsonl"):
    if f.name == OUT.name: continue
    for line in f.read_text("utf-8").splitlines():
        if line.strip():
            for t in json.loads(line)["transcript"]:
                if t["speaker"] == "visitor": SEEN.add(t["text"].strip().lower())

PATH = {'role': 'role', 'sen': 'seniority', 'name': 'organisation.name', 'typ': 'organisation.type',
        'agents': 'organisation.agents', 'pains': 'pain_points', 'tools': 'current_tooling', 'proc': 'process',
        'cities': 'geography', 'leads': 'monthly_leads', 'src': 'lead_sources', 'inf': 'influence',
        'nxt': 'next_step', 'consent': 'consent', 'cname': 'contact', 'email': 'contact', 'phone': 'contact'}
UAE = {"Dubai", "Abu Dhabi", "Sharjah"}


def label(turns):
    f, ev = {}, {}
    for i, (s, _, facts) in enumerate(turns, 1):
        for k, val in facts.items():
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


TAILS = [" Hope that helps.", " That's the short version.", " Happy to explain more.", " Anyway, that's us.",
         " Does that make sense?", " Just so you have the context.", " That's roughly the picture.", " Let me know if you need more."]


def uniq(text):
    base, n = text, 0
    while text.strip().lower() in SEEN:
        text = base + TAILS[n % len(TAILS)] + (" " * (n // len(TAILS))); n += 1
        if n > 30: text = base + f" (note {n})"
    SEEN.add(text.strip().lower()); return text


OPENERS = [
    "Hi, I'm Beacon, Leadrat's demo assistant. What does your business do?",
    "Hello! Beacon here. Before I show any screens, tell me what kind of company you're with.",
    "Welcome to Leadrat. I'm Beacon. What brings you here today?",
    "Hey there, Beacon from Leadrat. Who am I chatting with, and what do you do?",
    "Good to have you. I'm Beacon and I run live demos. What's your line of work?",
    "Hi! No forms here, just a chat. What does your team sell or manage?",
    "Hello, this is Beacon. Can you describe your business in a sentence or two?",
    "Hi, Beacon here. Are you in real estate sales, or something adjacent?",
    "Welcome! I'm Beacon. What would you like Leadrat to help with?",
    "Hey, I'm Beacon. Tell me a little about your company and I'll tailor the tour.",
    "Hi there. Beacon, Leadrat's guide. What does a normal day look like for your team?",
    "Hello and welcome. I'm Beacon. What sort of work does your firm do?",
    "Hi! I'm Beacon. Is this for your own business or someone else's?",
    "Good morning, Beacon here. Where do you fit in the property world?",
    "Hi, I'm Beacon. Quick question first: what does your organisation do?",
    "Hey! Beacon from Leadrat here. What made you open the demo?",
    "Welcome in. I'm Beacon and I can show Leadrat live. What's your business about?",
    "Hi, Beacon speaking. Tell me who your customers are and I'll pick the right screens.",
    "Hello! I'm Beacon. What problem are you hoping a CRM solves?",
    "Hi there, Beacon here. How would you describe what your company does?",
    "Hey, welcome. I'm Beacon. Are you a builder, a broker, a partner, or something else?",
    "Hi! Beacon here, happy to help. What's your role and company?",
    "Hello, I'm Beacon. Let's start simple: what do you do?",
    "Welcome to the Leadrat demo. I'm Beacon. What should I know about your team?",
    "Hi, I'm Beacon. What kind of leads does your business deal with?",
    "Hey there! Beacon here. What's your business, in your own words?",
    "Hello! Beacon, Leadrat's assistant. What are you hoping to see today?",
    "Hi, Beacon here. Tell me about the company you work for.",
    "Welcome! I'm Beacon. Who are you with, and what do they do?",
    "Hi there, I'm Beacon. What does your firm spend most of its time on?"]
OUSE = {}


def opener():
    pool = sorted(range(len(OPENERS)), key=lambda i: (OUSE.get(i, 0), R.random()))
    i = pool[0]; OUSE[i] = OUSE.get(i, 0) + 1
    return OPENERS[i]


# ---------- families: (family, [key sentences], staff noun, is real business) ----------
# Each key sentence carries {name} and {city}.
F = []
def fam(name, sentences, staff="sales", biz=True): F.append((name, sentences, staff, biz))

# channel partners
fam("channel_partner/b13_mandate_launches", [
    "We're {name}, a channel partner in {city}. We sell new launches for three developers on mandate.",
    "{name} is empanelled with a couple of big builders in {city}; we push their fresh inventory and earn brokerage from the developer.",
    "Our model is simple: developers give us sole mandate on a tower in {city} and we sell it out for a commission.",
    "I run {name}. We don't do resale at all, only primary sales for builders in {city} as their CP.",
    "We're a mandate company in {city}. The developer hands us unsold units and we close them for a fee.",
    "At {name} we work as the developer's outsourced sales arm in {city}, paid per booking."])
fam("channel_partner/b13_sourcing_partner", [
    "We're a sourcing partner for developers in {city}. We bring walk-ins to their sites and get paid on bookings.",
    "{name} sources buyers for builder projects around {city}; the developer pays our commission once the booking is done.",
    "Basically we're a CP firm in {city}. We tag customers on the developer's portal and take them for site visits.",
    "My company, {name}, is registered as a channel partner with about twelve builders in {city}.",
    "We generate footfall for under-construction projects in {city} and invoice the developer for every conversion.",
    "Think of {name} as a lead-sourcing partner: builders in {city} pay us per closed unit."])
fam("channel_partner/b13_nri_cp_desk", [
    "We're a channel partner focused on NRI buyers; we sell developer projects in {city} to clients in the Gulf.",
    "{name} is empanelled with developers in {city} and we market their launches to NRIs abroad.",
    "We do NRI sales for builders in {city} on commission, mostly primary inventory.",
    "Our desk at {name} sells new-launch apartments in {city} to overseas Indians, paid by the developer.",
    "We tie up with builders in {city} and run roadshows for NRIs. Developer pays us on each booking.",
    "{name} handles overseas marketing and sales for {city} developers as their authorised partner."])
fam("channel_partner/b13_uae_offplan_agent", [
    "We're registered agents with a few Dubai master developers, selling off-plan units in {city} for their commission.",
    "{name} sells off-plan launches in {city} as an authorised developer partner; no secondary market for us.",
    "We get allocation from developers at launch events in {city} and earn a percentage from them per unit.",
    "Our business is off-plan only in {city}; we're on the developers' agent lists and they pay us on SPA signing.",
    "At {name} we're a developer's channel partner in {city}, pushing new launches to investors.",
    "We sell primary off-plan stock for builders in {city} and the commission comes from the developer."])
fam("channel_partner/b13_cp_aggregator", [
    "We run a network of sub-brokers in {city} and together we sell developer inventory as one big CP.",
    "{name} aggregates small channel partners in {city} so builders deal with one empanelled entity.",
    "We're a CP aggregator in {city}. Developers give us mandates and our sub-partners close the deals.",
    "Our company sits between developers and hundreds of freelance CPs in {city}.",
    "{name} manages mandates for builders in {city} and distributes the leads to partner brokers.",
    "We sign mandate agreements with developers in {city} and then sell through our sub-broker network."])
fam("channel_partner/b13_plotted_mandate", [
    "We sell plotted developments on mandate for landowners and developers around {city}.",
    "{name} has exclusive marketing rights for two plotted layouts near {city}; we get a cut of every plot sold.",
    "We're the sole selling agent for a developer's villa-plot project outside {city}.",
    "Our business is mandate sales of farm plots and gated layouts for builders near {city}.",
    "The developer gave {name} the sales mandate for a township near {city} and we're paid per registration.",
    "We market and sell plotted projects in {city} on behalf of the promoters, commission basis."])

# brokerages (near misses of CP)
fam("brokerage/b13_resale_commission", [
    "We're {name}, a brokerage in {city}. We sell resale flats between owners and buyers and take commission from both sides.",
    "{name} does secondary-market deals in {city}; an owner lists with us and we find the buyer.",
    "Our model is simple: homeowners in {city} give us their flat to sell and we charge one percent on closing.",
    "I run {name}. We don't do new launches at all, only resale for individual owners in {city}.",
    "We're a resale agency in {city}. People who want to sell their homes come to us and we match buyers.",
    "At {name} we broker ready-to-move resale homes in {city} between families."])
fam("brokerage/b13_rental_agency", [
    "We're a rental agency in {city}. Landlords list flats with us and we find tenants for a month's rent as fee.",
    "{name} handles leasing between individual owners and tenants in {city}.",
    "We match tenants to landlords in {city}; our fee is one month of rent from each side.",
    "Mostly rentals in {city}. Owners give us their keys, we show the flat and close the lease.",
    "Our agency, {name}, rents out apartments for private landlords across {city}.",
    "We broker residential leases in {city}, nothing primary, just tenant and landlord deals."])
fam("brokerage/b13_uae_secondary", [
    "We're a Dubai brokerage doing secondary sales and leasing in {city}; we list owners' units on the portals.",
    "{name} lists ready properties for individual owners in {city} and takes a two percent fee from the buyer.",
    "Secondary market only for us in {city}; sellers sign Form A with us and we market the unit.",
    "Our agents in {city} list owners' villas on Bayut and Property Finder and close resale deals.",
    "At {name} we do resale and rentals between private parties in {city}.",
    "We're a RERA brokerage in {city} handling ready units for landlords and sellers."])
fam("brokerage/b13_commercial_leasing", [
    "We're commercial leasing brokers in {city}; we find office space for companies and charge them a fee.",
    "{name} does office and retail leasing in {city} between landlords and corporate tenants.",
    "Our team brokers shop and office leases in {city}; the landlord usually pays our fee.",
    "We place businesses into commercial spaces in {city} and earn a leasing commission.",
    "Commercial brokerage in {city}: warehouses, offices, showrooms, between owners and occupiers.",
    "At {name} we represent tenants looking for office space across {city}."])
fam("brokerage/b13_broker_built_once", [
    "We're brokers mainly. We did build one small building in {city} years ago, but almost all our income is resale commission.",
    "{name} is a brokerage in {city}; there was one joint development we did once, but that's history, we broker deals.",
    "People call us builders because of one project in {city}, but honestly we're a resale and rental agency.",
    "We built a single apartment block in {city} back in 2016. Today we only broker resale and rentals.",
    "Our firm constructed one building long ago, but {name} runs as a brokerage in {city} now.",
    "We once developed a small plot in {city}; since then we've only been agents for owners."])
fam("brokerage/b13_franchise_office", [
    "We're a franchise office of a real estate brokerage brand in {city}, doing resale and rentals.",
    "{name} runs two franchise branches in {city} for secondary sales and leasing.",
    "Our office in {city} is a brokerage franchise; owners list homes and we sell or rent them.",
    "We operate a brokerage franchise in {city}, mostly resale apartments for families.",
    "I own the {city} franchise of a brokerage network; we're paid by buyers and sellers.",
    "At {name} we're a franchised agency in {city} brokering resale deals."])

# developers
fam("developer/b13_inhouse_resale_desk", [
    "We're {name}, a developer in {city}. We build our own projects, and we also run a small resale desk for past buyers.",
    "{name} builds residential towers in {city}; there's a resale desk too, but that's a side service for our owners.",
    "We're builders in {city}. Our main business is our own projects; the resale team just helps old customers exit.",
    "Our company develops apartments in {city} and has an in-house team that resells units in our completed projects.",
    "We construct and sell our own projects in {city}. We also help our existing buyers resell, but that's small.",
    "I'm with {name}. We develop housing in {city} and sell it through our own sales team."])
fam("developer/b13_developer_with_cps", [
    "We're a developer in {city}. We have our own sales team and also work with channel partners.",
    "{name} builds and sells its own projects in {city}; CPs bring us some of the buyers.",
    "We develop mid-income housing in {city}. Channel partners sell part of our inventory, our team sells the rest.",
    "Our company is the builder of two towers in {city}; we pay CPs a commission on the units they sell.",
    "We're the promoter of a township in {city} and we manage a panel of channel partners.",
    "At {name} we're the developer; our in-house team plus empanelled CPs sell our projects in {city}."])
fam("developer/b13_landowner_jd", [
    "We're a real estate developer in {city}. We sign joint developments with landowners and build the projects ourselves.",
    "{name} does JD projects in {city}; we construct and sell, the landowner gets a share of units.",
    "We've built four projects in {city} on joint development land and sell them directly.",
    "Our company develops villas in {city} under joint development agreements and runs its own sales.",
    "We're builders in {city}; most of our land comes through JDAs with families.",
    "At {name} we develop and market our own gated communities around {city}."])
fam("developer/b13_uae_master_developer", [
    "We're a developer in {city}; we build and launch our own off-plan communities.",
    "{name} is a property developer in {city} with two off-plan towers under construction.",
    "We develop boutique residential buildings in {city} and sell through our sales centre and agents.",
    "Our company builds and sells its own projects in {city}; brokers sell some units for us.",
    "We're the developer behind a townhouse community in {city}.",
    "At {name} we build mid-rise apartments in {city} and handle the launch sales ourselves."])

# other_real_estate
fam("other_real_estate/b13_interior_design", [
    "We're an interior design firm in {city}. Most of our clients just bought a new flat.",
    "{name} does home interiors in {city}: modular kitchens, wardrobes, full fit-outs for new homeowners.",
    "We design and execute interiors for apartments in {city}; we get leads from builders' handover events.",
    "Our business is turnkey interiors for new flats in {city}.",
    "We're interior designers in {city}, working mostly with people moving into new projects.",
    "At {name} we do residential interior design and execution across {city}."])
fam("other_real_estate/b13_property_management", [
    "We're a property management company in {city}; we look after flats for owners who live abroad.",
    "{name} manages rented homes for NRI owners in {city}: rent collection, repairs, tenant issues.",
    "We handle day-to-day management of rented apartments in {city} for a monthly fee.",
    "Our company manages about 400 homes in {city} on behalf of their owners.",
    "We do property management in {city}, not sales: maintenance, inspections, rent.",
    "At {name} we take care of owners' properties in {city} after they're rented out."])
fam("other_real_estate/b13_facility_management", [
    "We're a facility management company in {city}; we run housekeeping and security for residential societies.",
    "{name} provides facility management for gated communities in {city}.",
    "We manage maintenance, security and amenities for apartment complexes in {city}.",
    "Our business is FM contracts with builders and RWAs in {city}.",
    "We do facility management for commercial buildings in {city}.",
    "At {name} we run the upkeep of society campuses across {city}."])
fam("other_real_estate/b13_home_loan_dsa", [
    "We're a home-loan DSA in {city}. We help property buyers get mortgages from banks.",
    "{name} is a direct selling agent for home loans in {city}; banks pay us on disbursal.",
    "We arrange home loans for people buying flats in {city}; our leads come from builders and brokers.",
    "Our firm processes mortgage files for buyers in {city} with a dozen banks.",
    "We're mortgage advisors in {city}, working with home buyers and developers.",
    "At {name} we do home loan sourcing for property purchases in {city}."])
fam("other_real_estate/b13_coworking_operator", [
    "We run co-working spaces in {city}; we lease desks and cabins to startups.",
    "{name} operates three co-working centres in {city}.",
    "Our business is managed offices and hot desks in {city}.",
    "We're a flexible workspace operator in {city}, selling memberships to companies.",
    "We take whole floors on lease in {city} and run them as co-working.",
    "At {name} we operate shared offices across {city}."])
fam("other_real_estate/b13_proptech_reseller", [
    "We're a proptech reseller in {city}; we sell software and virtual tours to builders.",
    "{name} resells real estate software to agencies in {city}.",
    "We build 3D walkthroughs and sell them to developers in {city}.",
    "Our company implements CRMs and portals for real estate firms in {city}.",
    "We're a technology partner for builders in {city}, reselling tools.",
    "At {name} we sell digital tools to property firms around {city}."])
fam("other_real_estate/b13_valuation_firm", [
    "We're a property valuation firm in {city}; banks send us homes to value before loans.",
    "{name} does valuation and technical due diligence for property in {city}.",
    "We value land and buildings in {city} for lenders and courts.",
    "Our business is property appraisal reports in {city}.",
    "We're registered valuers in {city}, mostly residential.",
    "At {name} we do valuations for property buyers and banks in {city}."])
fam("other_real_estate/b13_re_marketing_agency", [
    "We're a marketing agency that only works with real estate developers in {city}; we run their ad campaigns.",
    "{name} runs Facebook and Google ads for builders in {city}, we generate their leads.",
    "We do digital marketing for property launches in {city}.",
    "Our agency builds landing pages and ad funnels for real estate clients in {city}.",
    "We're a performance marketing shop for developers in {city}.",
    "At {name} we handle branding and lead generation for builders across {city}."])
fam("other_real_estate/b13_landowner", [
    "I'm a landowner in {city}. I have a few acres and I'm looking to sell plots myself.",
    "My family owns land near {city} and we're planning to sell it off in plots.",
    "We own a large parcel near {city} and want to market it to buyers directly.",
    "I inherited land outside {city} and I'm trying to find buyers for it.",
    "We're landowners in {city} looking at a joint development or selling outright.",
    "My family holds farmland near {city} and we want to sell it plot by plot."])

# unrelated
fam("unrelated/b13_edtech", [
    "We're an edtech company in {city}; we sell online coding courses to college students.",
    "{name} runs test-prep coaching in {city}; our counsellors call hundreds of leads a day.",
    "We sell online MBA programmes; our admissions team is in {city}.",
    "Our business is a coaching institute chain in {city}.",
    "We're an online tutoring startup in {city}.",
    "At {name} we sell language courses from our {city} office."], staff="counsellors")
fam("unrelated/b13_car_dealer", [
    "We're a car dealership in {city}; we sell new cars and take test-drive enquiries.",
    "{name} is an automobile dealer in {city} with two showrooms.",
    "We sell used cars in {city} and get leads from classifieds.",
    "Our business is a two-wheeler dealership in {city}.",
    "We're a multi-brand car showroom in {city}.",
    "At {name} we sell electric scooters in {city}."], staff="sales executives")
fam("unrelated/b13_insurance_agency", [
    "We're an insurance agency in {city}; we sell health and life policies.",
    "{name} sells motor and health insurance in {city}.",
    "We're insurance brokers in {city}, mostly corporate group cover.",
    "Our business is life insurance advisory in {city}.",
    "We sell term plans and health cover from {city}.",
    "At {name} we're a general insurance agency in {city}."], staff="advisors")
fam("unrelated/b13_clinic_gym", [
    "We run a dental clinic chain in {city}.",
    "{name} is a gym chain in {city}; memberships are our sales.",
    "We're a dermatology clinic in {city} with a call centre for appointments.",
    "Our business is a fitness studio in {city}.",
    "We run physiotherapy centres in {city}.",
    "At {name} we're a diagnostics lab in {city}."], staff="front desk")
fam("unrelated/b13_student_jobseeker", [
    "I'm a student in {city} doing a college project on CRMs.",
    "I'm looking for a job in sales and wanted to learn how real estate CRMs work.",
    "I'm an MBA student in {city} writing a report on proptech.",
    "Honestly I'm job hunting and wanted to understand your product before an interview.",
    "I'm a fresher in {city} learning about software products.",
    "I'm a student and just curious how this works."], biz=False)
fam("unrelated/b13_competitor_research", [
    "I work at another CRM company and I'm checking out your features.",
    "I'm a product manager at a software firm in {city}, researching competitors.",
    "We build a competing sales tool; I'm just comparing.",
    "I'm doing competitive research for a SaaS company in {city}.",
    "Full disclosure, I'm from a rival CRM vendor.",
    "I'm an analyst at a software company comparing CRMs."], biz=False)

# unknown
fam("unknown/b13_vague_team", [
    "Just looking around for my team.",
    "I'm exploring CRMs for the company, nothing specific yet.",
    "Someone asked me to check this out.",
    "We need something to manage enquiries better.",
    "I'd rather not say what we do yet, just show me the product.",
    "Just browsing, want to see the dashboard."])
fam("unknown/b13_features_only", [
    "Does this integrate with WhatsApp?",
    "Can you show me the reports first?",
    "How does lead assignment work?",
    "What does it cost per user?",
    "Can I import a spreadsheet of contacts?",
    "Is there a mobile app?"])


# extra near-miss families
fam("channel_partner/b13_ex_broker_now_cp", [
    "We used to do resale, but now {name} only sells developer inventory in {city} as an empanelled CP.",
    "We stopped rentals last year; today we're a channel partner for builders in {city}, commission from the developer.",
    "{name} moved from secondary deals to primary: we sell new projects for developers in {city}.",
    "Resale was too slow, so we became a CP. Now builders in {city} pay us per booking.",
    "Our agency switched to developer mandates in {city}; no owner listings anymore.",
    "These days {name} earns only from developers' launches in {city}, as their sales partner."])
fam("brokerage/b13_cp_turned_resale", [
    "We used to be a CP for builders, but now {name} does only resale for homeowners in {city}.",
    "We stopped working on developer mandates; today we broker resale flats in {city} between families.",
    "{name} moved from primary to secondary: owners in {city} list with us and we find buyers.",
    "Builder payouts were too late, so we went back to resale and rentals in {city}.",
    "Our agency dropped developer tie-ups; now it's owner listings only in {city}.",
    "These days {name} earns commission from buyers and sellers of resale homes in {city}."])
fam("developer/b13_builder_selling_direct", [
    "We're builders in {city} and we sell our own flats directly, no brokers involved.",
    "{name} constructs apartments in {city}; our sales office handles every booking.",
    "We develop our own land in {city} and sell straight to buyers.",
    "Our company builds row houses in {city} and markets them itself.",
    "We're a small developer in {city}, two projects running, own sales team.",
    "At {name} we build and sell our own projects around {city}."])
fam("other_real_estate/b13_legal_documentation", [
    "We're a property legal firm in {city}; we do title checks and sale deed registration for buyers.",
    "{name} handles property documentation and registration in {city}.",
    "We do title search and agreement drafting for property deals in {city}.",
    "Our business is conveyancing for home buyers in {city}.",
    "We help buyers in {city} with stamp duty, registration and khata transfer.",
    "At {name} we're property lawyers in {city}."])
fam("other_real_estate/b13_home_staging_photo", [
    "We do real estate photography and home staging in {city} for listings.",
    "{name} shoots property videos and drone footage for sellers in {city}.",
    "We stage homes before they're listed for sale in {city}.",
    "Our business is listing photography for agencies in {city}.",
    "We make virtual staging images for property listings in {city}.",
    "At {name} we do property photo shoots and floor plans in {city}."])
fam("other_real_estate/b13_packers_movers_re", [
    "We're a relocation and tenant-onboarding service in {city}, partnering with rental landlords.",
    "{name} handles move-in services for new home buyers in {city}.",
    "We do home inspections and snagging for buyers taking possession in {city}.",
    "Our company does pre-handover snag checks for new apartments in {city}.",
    "We inspect new flats for defects before possession in {city}.",
    "At {name} we offer possession and snagging services across {city}."])
fam("unrelated/b13_restaurant_retail", [
    "We run a restaurant chain in {city} and want to track catering enquiries.",
    "{name} is a furniture retail store in {city}.",
    "We sell solar panels to homeowners in {city}.",
    "Our business is a travel agency in {city}.",
    "We're a wedding planning company in {city}.",
    "At {name} we sell water purifiers door to door in {city}."], staff="sales")
fam("unrelated/b13_it_services", [
    "We're an IT services company in {city}; we sell software projects to SMEs.",
    "{name} is a digital agency in {city} for e-commerce brands.",
    "We make accounting software for small businesses in {city}.",
    "Our business is cloud hosting for startups from {city}.",
    "We're a cybersecurity consultancy in {city}.",
    "At {name} we build mobile apps for retailers in {city}."], staff="sales")
fam("unrelated/b13_loan_personal", [
    "We're a personal loan DSA in {city}; nothing to do with property, just personal and business loans.",
    "{name} sells credit cards and personal loans in {city}.",
    "We do gold loans in {city}.",
    "Our business is vehicle finance in {city}.",
    "We're a microfinance company around {city}.",
    "At {name} we arrange business loans for traders in {city}."], staff="field")
fam("unknown/b13_team_numbers_only", [
    "We've got a lot of enquiries and a messy process.",
    "My boss wants a CRM, I'm just collecting options.",
    "We're growing fast and need structure.",
    "Show me how leads get assigned.",
    "I need a tool for my team, that's all I can say.",
    "Let me see the product before I tell you about us."])
fam("unknown/b13_ambiguous_property_word", [
    "We deal with properties in a way, it's complicated.",
    "We're sort of in the housing space, loosely.",
    "It's a family business, we do a bit of everything.",
    "We handle some property things among other stuff.",
    "Our work touches real estate sometimes.",
    "Let's just say we have customers who call a lot."])
fam("channel_partner/b13_commercial_mandate", [
    "We sell pre-leased commercial units for developers in {city} on mandate.",
    "{name} is the exclusive sales partner for a developer's office tower in {city}.",
    "We market retail shops in new commercial projects in {city}; the builder pays our commission.",
    "Our firm sells developer-owned commercial inventory in {city} as a CP.",
    "We're empanelled with commercial developers in {city} to sell their office spaces.",
    "At {name} we close commercial launches in {city} for builders, paid per unit."])

NAMES = ["Skyline", "Harbour", "Crestview", "Northstar", "Blue Arch", "Keystone", "Orchid", "Silverline", "Maple",
         "Summit", "Riverbend", "Greenfield", "Lotus", "Sterling", "Evergreen", "Cedar", "Horizon", "Aspen", "Pinnacle",
         "Coral", "Granite", "Meridian", "Sapphire", "Banyan", "Monsoon", "Saffron", "Juniper", "Vantage", "Tidewater"]
SUFFIX = {"channel_partner": ["Realty Partners", "Sales Associates", "Property Advisors"],
          "brokerage": ["Realty", "Homes", "Estates"], "developer": ["Developers", "Constructions", "Builders"],
          "other_real_estate": ["Services", "Solutions", "Studio"], "unrelated": ["Group", "Labs", "Ventures"],
          "unknown": ["Co"]}
CITIES_IN = ["Mumbai", "Pune", "Bengaluru", "Hyderabad", "Delhi", "Gurgaon", "Noida", "Ahmedabad", "Chennai",
             "Kolkata", "Jaipur", "Kochi", "Lucknow", "Indore", "Chandigarh", "Nagpur", "Surat", "Thane"]
CITIES_AE = ["Dubai", "Abu Dhabi", "Sharjah"]
ROLES = [("founder", "owner", "approver"), ("owner", "owner", "approver"), ("managing director", "executive", "approver"),
         ("director", "executive", "approver"), ("sales head", "executive", "sponsored_evaluator"),
         ("sales manager", "manager", "sponsored_evaluator"), ("operations manager", "manager", "sponsored_evaluator"),
         ("team lead", "manager", "none"), ("marketing executive", "individual_contributor", "none"),
         ("co-founder", "owner", "approver")]
FIRST = ["Aarav", "Neha", "Rohan", "Priya", "Imran", "Kavya", "Vikram", "Sana", "Arjun", "Meera", "Farhan", "Divya",
         "Rahul", "Ananya", "Kabir", "Ishita", "Nikhil", "Zoya", "Tarun", "Pooja"]
SOURCES = ["99acres", "MagicBricks", "Housing.com", "Facebook ads", "Google ads", "Instagram", "walk-ins", "referrals",
           "website", "Bayut", "Property Finder", "JustDial", "LinkedIn"]
TOOLS = [("We keep everything in Excel.", ["Excel"], "manual"),
         ("It's all on WhatsApp and a shared Google Sheet.", ["WhatsApp", "Google Sheets"], "manual"),
         ("Our agents write things in notebooks, honestly.", ["notebook"], "manual"),
         ("We use Zoho CRM but nobody updates it.", ["Zoho CRM"], "unsatisfied_crm"),
         ("We're on Salesforce, which is too complicated for the team.", ["Salesforce"], "unsatisfied_crm"),
         ("We use HubSpot and it's mostly fine.", ["HubSpot"], "satisfied_crm"),
         ("There's a local CRM we paid for, but it has no mobile app.", ["CRM"], "unsatisfied_crm")]
PAINS = [("leads fall through the cracks", "leads fall through the cracks"),
         ("follow-ups get missed", "missed follow-ups"),
         ("we can't see which person is handling which enquiry", "no visibility into lead ownership"),
         ("duplicate enquiries from different sources", "duplicate leads"),
         ("reporting takes hours every week", "manual reporting"),
         ("response time to new enquiries is slow", "slow response to new leads"),
         ("when someone leaves, their contacts leave with them", "contacts lost when staff leave")]

Q_TEAM = ["How big is the team handling enquiries?", "How many people are on your side?", "What's your team size?",
          "Roughly how many people work the leads?", "And your role, plus how many people are on the team?"]
Q_LEADS = ["How many enquiries come in a month, and from where?", "What's the monthly lead volume and main sources?",
           "Where do leads come from, and how many?", "About how many new enquiries per month?"]
Q_TOOLS = ["How do you track all of this today?", "What are you using right now to manage leads?",
           "What's the current setup, and what hurts most?", "Tell me about your tools and the biggest headache."]
Q_AUTH = ["Here is the Leads list with owner and status. Who makes the call on software?",
          "This is the Pipeline board. Who decides on buying a tool like this?",
          "Here's the follow-up reminder view. Are you the one who signs off?",
          "Here's the source-wise report. Who else is involved in the decision?"]
Q_CONSENT = ["Would you like our sales team to follow up?", "Shall I have someone from sales reach out?",
             "Can our team contact you with pricing?", "Would a call from our sales team help?"]
Q_CONTACT = ["What's the best email or number?", "Where should they reach you?", "Could you share a contact?"]

rows, phone_n = [], [0]


def phone(city):
    phone_n[0] += 1
    return f"+971 50 000 3{phone_n[0]:03d}" if city in UAE else f"+91 90000 3{phone_n[0]:04d}"


def example(famname, sentences, staff, biz, v, profile):
    typ = famname.split("/")[0]
    uae = "uae" in famname and typ != "other_real_estate"
    city = R.choice(CITIES_AE if uae else CITIES_IN)
    name = f"{R.choice(NAMES)} {R.choice(SUFFIX[typ])}"
    key = sentences[v].format(name=name, city=city)
    facts = {}
    if typ != "unknown":
        facts["typ"] = typ
    if "{name}" in sentences[v]: facts["name"] = name
    if "{city}" in sentences[v]: facts["cities"] = [city]
    T = [('b', opener(), {}), ('v', key, facts)]
    role, sen, inf = R.choice(ROLES)
    if typ == "unknown" and v % 2 == 0:
        T += [('b', "Sure. What kind of business is it, so I can show the right screens?", {}),
              ('v', R.choice(["I'll keep that to myself for now.", "Doesn't matter much, just show me the basics.",
                              "Let's skip that part.", "Rather not get into it."]), {})]
    if not biz:
        T += [('b', "Happy to show you around. Is this for a business evaluation?", {}),
              ('v', R.choice(["No, nothing to buy here.", "No purchase planned, just learning.",
                              "Not buying anything, sorry."]) + " Please don't have anyone call me.", {"nxt": "declined"}),
              ('b', "No problem. Here's the Leads list so you can see how it works.", {}),
              ('v', R.choice(["Thanks, that's useful.", "Got it, thank you.", "Nice, that's clear."]), {})]
        return T, profile == "partial" and len(T) >= 4
    agents = R.choice([3, 5, 8, 12, 15, 22, 30, 45, 60])
    T += [('b', R.choice(Q_TEAM), {}),
          ('v', f"I'm the {role}. We have {agents} people on the {staff} side.", {"role": role, "sen": sen, "agents": agents})]
    if profile != "review":
        n = R.choice([60, 90, 150, 250, 400, 600, 900, 1500])
        srcs = R.sample([s for s in SOURCES if (s in ("Bayut", "Property Finder")) == (city in UAE) or s in ("referrals", "website")], 2)
        T += [('b', R.choice(Q_LEADS), {}),
              ('v', f"Around {n} a month, mostly {srcs[0]} and {srcs[1]}.", {"leads": (n, n), "src": srcs})]
    else:
        T += [('b', R.choice(Q_LEADS), {}),
              ('v', R.choice(["It varies a lot, hard to put a number on it.", "Depends on the month, really.",
                              "No idea, nobody counts them properly."]), {})]
    tl = R.choice(TOOLS); ps = R.sample(PAINS, 2)
    T += [('b', R.choice(Q_TOOLS), {}),
          ('v', f"{tl[0]} The problem is {ps[0][0]}, and {ps[1][0]}.", {"tools": tl[1], "proc": tl[2], "pains": [ps[0][1], ps[1][1]]})]
    if profile == "hot":
        inf, role_line = "approver", "I decide, it's my budget."
    else:
        role_line = {"approver": "I sign off on it myself.", "sponsored_evaluator": "I'm evaluating this for my boss, who will decide.",
                     "none": "I don't have any say, I just collect options."}[inf]
    nxt = {"hot": "within_30_days", "review": "within_30_days", "nurture": "later", "close": "declined", "partial": "within_30_days"}[profile]
    nl = {"within_30_days": R.choice(["We want something running within a few weeks.", "Ideally we start this month."]),
          "later": R.choice(["We'd look at this next quarter.", "Maybe in a few months."]),
          "declined": R.choice(["We're not moving forward, and please don't follow up.", "Not interested in a follow-up, thanks."])}[nxt]
    T += [('b', R.choice(Q_AUTH), {}), ('v', f"{role_line} {nl}", {"inf": inf, "nxt": nxt})]
    if profile in ("hot", "review", "partial"):
        first = R.choice(FIRST); ph = phone(city)
        email = f"{first.lower()}.{R.randint(10,99)}@example.com"
        T += [('b', R.choice(Q_CONSENT), {}), ('v', "Yes, please have them reach out.", {"consent": True}),
              ('b', R.choice(Q_CONTACT), {}), ('v', f"{first}, {email} or {ph}.", {"cname": first, "email": email, "phone": ph})]
    elif profile == "nurture":
        T += [('b', R.choice(Q_CONSENT), {}), ('v', "Not right now, I'll come back when we're ready.", {})]
    return T, profile == "partial"


PROFILES = ["hot", "partial", "nurture", "partial", "review", "close"]
for fi, (fname, sents, staff, biz) in enumerate(F):
    nvar = 6 if fi < 25 else 5
    for v in range(nvar):
        prof = PROFILES[v] if v < 5 or nvar == 6 else "close"
        T, part = example(fname, sents, staff, biz, v, prof)
        if part:
            vis = [i for i, t in enumerate(T) if t[0] == 'v']
            k = R.choice(vis[1:max(2, len(vis) - 1)])
            T = T[:k + 1]
        T = [(s, uniq(x) if s == 'v' else x, f) for s, x, f in T]
        rows.append({"id": "b13-%03d" % (len(rows) + 1), "family": fname, "language": "en", "partial": part,
                     "transcript": [{"turn_id": i + 1, "speaker": "beacon" if s == 'b' else "visitor", "text": x}
                                    for i, (s, x, _) in enumerate(T)], "label": label(T)})

rows = rows[:250]
OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
print(len(rows), "rows,", len(F), "families")
