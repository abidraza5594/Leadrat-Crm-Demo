import json
OUT = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "data" / "raw" / "batch_5.jsonl")
rows=[]
def L(role=None,sen='unknown',name=None,typ='unknown',agents=None,pains=None,tools=None,proc='unknown',countries=None,cities=None,lmin=None,lmax=None,src=None,inf='unknown',nxt='unknown',consent=False,cname=None,email=None,phone=None,ev=None):
    return {"role":role,"seniority":sen,"organisation":{"name":name,"type":typ,"agents":agents},"pain_points":pains,"current_tooling":tools,"process":proc,
     "geography":{"countries":countries,"cities":cities},"monthly_leads":{"min":lmin,"max":lmax},"lead_sources":src,"influence":inf,"next_step":nxt,
     "consent":consent,"contact":{"name":cname,"email":email,"phone":phone},"evidence":ev or {}}
def E(fam,lang,partial,turns,label):
    t=[{"turn_id":i+1,"speaker":"beacon" if s=='b' else "visitor","text":x} for i,(s,x) in enumerate(turns)]
    rows.append({"id":"b5-%03d"%(len(rows)+1),"family":fam,"language":lang,"partial":partial,"transcript":t,"label":label})
B=lambda x:('b',x); V=lambda x:('v',x)

# ---- brokerage/hinglish_high_fit
E("brokerage/hinglish_high_fit","hinglish",False,[
B("Hi, I'm Beacon from Leadrat. What brings you here today?"),
V("Hi, main Rohit, founder hoon Skyline Realty ka, Pune mein. Hum 25 log hai sales mein."),
B("Nice. Roughly how many leads do you get per month, and from where?"),
V("Around 600 leads mahine ke, mostly 99acres aur Housing.com se aati hai."),
B("And what's the biggest problem today?"),
V("Follow-up miss ho jata hai, aur leads Excel mein hi padi rehti hai, koi track nahi karta ki kaun kis ko call kar raha hai."),
B("Here is the Leads list with auto-assignment and follow-up reminders. Who would decide on buying?"),
V("Main hi decide karunga. Agle do hafte mein start karna hai."),
B("Great. Shall our sales team contact you?"),
V("Haan bilkul, call karo. rohit@skylinerealty.example.com, +91 90000 01111")],
L("founder","owner","Skyline Realty","brokerage",25,["follow-ups get missed","no visibility on who is calling which lead"],["Excel"],"manual",["India"],["Pune"],600,600,["99acres","Housing.com"],"approver","within_30_days",True,"Rohit","rohit@skylinerealty.example.com","+91 90000 01111",
 {"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"organisation.agents":[2],"geography":[2],"monthly_leads":[4],"lead_sources":[4],"pain_points":[6],"current_tooling":[6],"process":[6],"influence":[8],"next_step":[8],"consent":[10],"contact":[2,10]}))
E("brokerage/hinglish_high_fit","hinglish",False,[
B("Hello! Beacon here. Tell me a bit about your business?"),
V("Hello ji, hum Hyderabad mein resale aur rental brokerage chalate hai, naam hai Deccan Homes. Main owner hoon."),
B("How big is the sales team?"),
V("Chalees agents hai, Gachibowli aur Kondapur mein do offices."),
B("And lead volume?"),
V("Do sau se teen sau leads per month, Facebook ads aur MagicBricks se."),
B("What tools are you using now?"),
V("Ek purana CRM hai but usme WhatsApp integration nahi hai aur reports bekaar hai."),
B("Here's the WhatsApp inbox and the Reports dashboard. When are you looking to move?"),
V("Is month ke end tak decide kar lunga, main hi sign karta hoon."),
B("Can our team reach out to set up a trial?"),
V("Yes please. Email: owner@deccanhomes.example.com")],
L("owner","owner","Deccan Homes","brokerage",40,["no WhatsApp integration in CRM","poor reports"],["CRM"],"unsatisfied_crm",["India"],["Hyderabad"],200,300,["Facebook ads","MagicBricks"],"approver","within_30_days",True,None,"owner@deccanhomes.example.com",None,
 {"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2,4],"organisation.agents":[4],"monthly_leads":[6],"lead_sources":[6],"current_tooling":[8],"pain_points":[8],"process":[8],"influence":[10],"next_step":[10],"consent":[12],"contact":[12]}))
E("brokerage/hinglish_high_fit","hinglish",True,[
B("Hi, I'm Beacon. What would you like to see?"),
V("Bhai hum Mumbai mein brokerage hai, Andheri se operate karte hai. 18 agents hai."),
B("Got it. How many enquiries a month?"),
V("Lagbhag 350, walk-ins aur 99acres se."),
B("Here is the Leads list. What's hurting most today?"),
V("Leads ka duplicate ho jana, same client ko teen agent call kar dete hai")],
L(None,"unknown",None,"brokerage",18,["duplicate leads","same client called by multiple agents"],None,"unknown",["India"],["Mumbai"],350,350,["walk-ins","99acres"],"unknown","unknown",False,
 ev={"organisation.type":[2],"organisation.agents":[2],"geography":[2],"monthly_leads":[4],"lead_sources":[4],"pain_points":[6]}))
E("brokerage/hinglish_high_fit","hinglish",False,[
B("Welcome! I'm Beacon, Leadrat's demo assistant. What's your role?"),
V("Main director hoon, NCR Property Point, Gurgaon aur Noida dono jagah kaam hai."),
B("Team size?"),
V("Pachaas sales log, plus 5 telecallers."),
B("Lead volume and sources?"),
V("1000 ke aas paas, Google ads, Facebook aur portals se."),
B("How do you manage them now?"),
V("Google Sheets aur WhatsApp groups. Report banane mein pura din lag jata hai, aur leads ka response time slow hai."),
B("Here's the auto-assignment rule screen and live dashboard. Would you like sales to call?"),
V("Haan, next week call karo. Main final decision maker hoon. 90000 02222 pe call karna.")],
L("director","executive","NCR Property Point","brokerage",50,["reports take a full day","slow lead response time"],["Google Sheets","WhatsApp"],"manual",["India"],["Gurgaon","Noida"],1000,1000,["Google ads","Facebook","portals"],"approver","within_30_days",True,None,None,"+91 90000 02222",
 {"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[4],"monthly_leads":[6],"lead_sources":[6],"current_tooling":[8],"process":[8],"pain_points":[8],"influence":[10],"next_step":[10],"consent":[10],"contact":[10]}))
E("brokerage/hinglish_high_fit","hinglish",True,[
B("Hi there, Beacon here. How can I help?"),
V("Hum Jaipur ke brokers hai, Pink City Estates. Team chhoti hai, 8 log."),
B("What's the main challenge?"),
V("Site visit schedule karna aur yaad rakhna mushkil hai, sab diary mein likhte hai.")],
L(None,"unknown","Pink City Estates","brokerage",8,["site visit scheduling is hard to track"],["diary"],"manual",["India"],["Jaipur"],ev={"organisation.name":[2],"organisation.type":[2],"organisation.agents":[2],"geography":[2],"pain_points":[4],"current_tooling":[4],"process":[4]}))

# ---- developer/hinglish_partial
E("developer/hinglish_partial","hinglish",True,[
B("Hi! I'm Beacon. Are you a developer or a broker?"),
V("Developer hai hum, Ahmedabad mein do residential projects chal rahe hai."),
B("Nice. How many people in sales?"),
V("In-house 12 log hai, baaki channel partners.")],
L(None,"unknown",None,"developer",12,None,None,"unknown",["India"],["Ahmedabad"],ev={"organisation.type":[2],"geography":[2],"organisation.agents":[4]}))
E("developer/hinglish_partial","hinglish",True,[
B("Hello, Beacon here. What would you like to explore?"),
V("Main marketing manager hoon Sunrise Buildcon mein, Bengaluru. Hamara Salesforce hai but bahut mehenga aur complex hai."),
B("Understood. How many leads do you handle monthly?"),
V("Kaafi zyada, exact number nahi pata."),
B("Here's the project-wise lead view...")],
L("marketing manager","manager","Sunrise Buildcon","developer",None,["Salesforce is expensive","Salesforce is complex"],["Salesforce"],"unsatisfied_crm",["India"],["Bengaluru"],ev={"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"current_tooling":[2],"pain_points":[2],"process":[2]}))
E("developer/hinglish_partial","hinglish",True,[
B("Hi, I'm Beacon from Leadrat."),
V("Hi. Hum Chennai mein villa projects banate hai. CRM dekhna tha."),
B("Sure. Where do your leads come from?"),
V("Mostly Facebook ads aur newspaper ads se, around 400 per month."),
B("And the team?"),
V("Sales team 10 se 30 ke beech rehti hai, project pe depend karta hai.")],
L(None,"unknown",None,"developer",None,None,None,"unknown",["India"],["Chennai"],400,400,["Facebook ads","newspaper ads"],ev={"organisation.type":[2],"geography":[2],"monthly_leads":[4],"lead_sources":[4]}))
E("developer/hinglish_partial","hinglish",True,[
B("Welcome! What's your role?"),
V("Sales head, Greenfield Developers, Kolkata."),
B("What's the biggest issue in your sales process?"),
V("Channel partners ke leads aur direct leads mix ho jaate hai, brokerage dispute hota hai."),
B("Let me show the source attribution screen. How are you tracking this now?"),
V("Abhi Excel mein, ek banda manually update karta hai.")],
L("sales head","manager","Greenfield Developers","developer",None,["channel partner and direct leads get mixed up","brokerage disputes"],["Excel"],"manual",["India"],["Kolkata"],ev={"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"pain_points":[4],"current_tooling":[6],"process":[6]}))
E("developer/hinglish_partial","hinglish",True,[
B("Hi, Beacon here. Tell me about your company?"),
V("Hum Pune mein township developer hai, 60 log sales mein."),
B("Great. Monthly leads?"),
V("Paanch sau ke upar, 500-700 easily.")],
L(None,"unknown",None,"developer",60,None,None,"unknown",["India"],["Pune"],500,700,ev={"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[4]}))

# ---- channel_partner/hinglish_whatsapp
E("channel_partner/hinglish_whatsapp","hinglish",False,[
B("Hi! I'm Beacon. What kind of business are you?"),
V("Hum channel partner hai, 4-5 developers ke projects bechte hai Thane mein."),
B("How do you manage leads now?"),
V("Sab WhatsApp pe. Leads ka koi record nahi rehta, phone badla to data gaya."),
B("Here's our WhatsApp integration. Team size and lead count?"),
V("15 agents, aur 150 leads mahine ka."),
B("Who decides on software?"),
V("Main partner hoon, main aur mera bhai milke decide karte hai. Abhi jaldi nahi hai, 2-3 mahine baad dekhenge."),
B("Should our team follow up later?"),
V("Nahi abhi call mat karo, main khud contact karunga.")],
L("partner","owner",None,"channel_partner",15,["no record of leads","data lost when phone changes"],["WhatsApp"],"manual",["India"],["Thane"],150,150,None,"approver","later",False,
 ev={"organisation.type":[2],"geography":[2],"current_tooling":[4],"process":[4],"pain_points":[4],"organisation.agents":[6],"monthly_leads":[6],"role":[8],"seniority":[8],"influence":[8],"next_step":[8]}))
E("channel_partner/hinglish_whatsapp","hinglish",False,[
B("Hello, I'm Beacon. What brings you here?"),
V("Hello, main Dubai mein channel partner hoon, off-plan projects bechte hai. Firm ka naam Gulf Key Properties."),
B("Nice. How many agents?"),
V("22 agents. Leads WhatsApp aur Instagram se aati hai, around 800 monthly."),
B("What's the main pain?"),
V("WhatsApp pe chats lost ho jaati hai aur manager ko pata nahi chalta kaun agent reply nahi kar raha."),
B("Here's the shared WhatsApp inbox with agent-level tracking. Who signs off?"),
V("I'm the MD, main sign karunga. This month hi chahiye."),
B("Shall sales contact you?"),
V("Yes, email karo md@gulfkey.example.com")],
L("MD","executive","Gulf Key Properties","channel_partner",22,["WhatsApp chats get lost","no visibility on agents not replying"],["WhatsApp","Instagram"],"manual",["UAE"],["Dubai"],800,800,["WhatsApp","Instagram"],"approver","within_30_days",True,None,"md@gulfkey.example.com",None,
 {"geography":[2],"organisation.type":[2],"organisation.name":[2],"organisation.agents":[4],"lead_sources":[4],"current_tooling":[4,6],"monthly_leads":[4],"pain_points":[6],"process":[6],"role":[8],"seniority":[8],"influence":[8],"next_step":[8],"consent":[10],"contact":[10]}))
E("channel_partner/hinglish_whatsapp","hinglish",True,[
B("Hi, Beacon here."),
V("hi, CP hu Navi Mumbai me. whatsapp broadcast bhejte hai clients ko"),
B("Nice. How many leads do you get?"),
V("pata nahi exactly, kaafi hai")],
L(None,"unknown",None,"channel_partner",None,None,["WhatsApp"],"unknown",["India"],["Navi Mumbai"],ev={"organisation.type":[2],"geography":[2],"current_tooling":[2]}))
E("channel_partner/hinglish_whatsapp","hinglish",False,[
B("Hello! I'm Beacon. What's your role?"),
V("Main ek sales executive hoon, Metro Link Realty mein, channel partner firm hai Bengaluru mein."),
B("What problems do you face?"),
V("WhatsApp pe leads aati hai aur hum manually sheet mein daalte hai, time waste hota hai."),
B("Here's auto-capture from WhatsApp into Leads. Who would decide on a CRM?"),
V("Mera boss decide karega, main bas dekh raha hoon options unke liye."),
B("Would you like sales to reach out?"),
V("Abhi nahi, pehle boss ko dikhata hoon.")],
L("sales executive","individual_contributor","Metro Link Realty","channel_partner",None,["manual entry of WhatsApp leads into sheets wastes time"],["WhatsApp","spreadsheet"],"manual",["India"],["Bengaluru"],None,None,["WhatsApp"],"sponsored_evaluator","later",False,
 ev={"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"pain_points":[4],"current_tooling":[4],"process":[4],"lead_sources":[4],"influence":[6],"next_step":[8]}))
E("channel_partner/hinglish_whatsapp","hinglish",True,[
B("Hi, Beacon here. What would you like to see?"),
V("Hum Lucknow mein channel partner hai, 6 log ki team."),
B("And your tools?"),
V("WhatsApp aur ek diary. Follow-up bhool jaate hai log."),
B("Let me show reminders...")],
L(None,"unknown",None,"channel_partner",6,["follow-ups forgotten"],["WhatsApp","diary"],"manual",["India"],["Lucknow"],ev={"organisation.type":[2],"geography":[2],"organisation.agents":[2],"current_tooling":[4],"process":[4],"pain_points":[4]}))

# ---- brokerage/hindi_devanagari
E("brokerage/hindi_devanagari","hi",False,[
B("Namaste! I'm Beacon from Leadrat. How can I help?"),
V("नमस्ते, मैं इंदौर में प्रॉपर्टी ब्रोकर हूँ, मालिक हूँ। हमारी टीम में 12 लोग हैं।"),
B("How many leads per month?"),
V("लगभग 200 लीड्स, ज़्यादातर 99acres और walk-in से।"),
B("What's the main problem?"),
V("फॉलो-अप छूट जाते हैं, सब कुछ रजिस्टर में लिखते हैं।"),
B("Here is the follow-up reminder screen. When would you like to start?"),
V("अगले महीने के बाद सोचेंगे।"),
B("Can our team contact you then?"),
V("नहीं, अभी नहीं।")],
L("owner","owner",None,"brokerage",12,["follow-ups get missed"],["paper register"],"manual",["India"],["Indore"],200,200,["99acres","walk-ins"],"approver","later",False,
 ev={"role":[2],"seniority":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[4],"lead_sources":[4],"pain_points":[6],"current_tooling":[6],"process":[6],"influence":[2],"next_step":[8]}))
E("brokerage/hindi_devanagari","hi",True,[
B("Hello, Beacon here."),
V("हम दिल्ली में ब्रोकरेज चलाते हैं, नाम है राजधानी एस्टेट्स।"),
B("How big is your team?"),
V("30 एजेंट हैं। लीड्स Facebook से आती हैं।")],
L(None,"unknown","Rajdhani Estates","brokerage",30,None,None,"unknown",["India"],["Delhi"],None,None,["Facebook"],ev={"organisation.type":[2],"organisation.name":[2],"geography":[2],"organisation.agents":[4],"lead_sources":[4]}))
E("brokerage/hindi_devanagari","hi",False,[
B("Hi! I'm Beacon. What would you like to see?"),
V("मैं सेल्स मैनेजर हूँ, जयपुर की एक ब्रोकरेज फर्म में। हमारे पास पहले से CRM है लेकिन रिपोर्ट्स ठीक नहीं हैं।"),
B("Understood. Team and volume?"),
V("20 लोग, और महीने में करीब तीन सौ लीड्स।"),
B("Here's the reports dashboard. Who decides?"),
V("फैसला डायरेक्टर साहब करेंगे, मैं उनके लिए देख रहा हूँ।"),
B("Shall we have sales contact you?"),
V("हाँ, ठीक है, कॉल कर लीजिए। मेरा नंबर +91 90000 03333 है। इस हफ्ते बात कर लेते हैं।")],
L("sales manager","manager",None,"brokerage",20,["reports are not good"],["CRM"],"unsatisfied_crm",["India"],["Jaipur"],300,300,None,"sponsored_evaluator","within_30_days",True,None,None,"+91 90000 03333",
 {"role":[2],"seniority":[2],"organisation.type":[2],"geography":[2],"current_tooling":[2],"pain_points":[2],"process":[2],"organisation.agents":[4],"monthly_leads":[4],"influence":[6],"consent":[8],"contact":[8],"next_step":[8]}))
E("brokerage/hindi_devanagari","hi",True,[
B("Namaste, Beacon here. Aap kya karte hain?"),
V("मैं पटना में प्रॉपर्टी डीलर हूँ। मेरे साथ 2 लोग और हैं, कुल 3 की टीम।"),
B("How do you manage leads?"),
V("Excel और WhatsApp पर।")],
L(None,"unknown",None,"brokerage",3,None,["Excel","WhatsApp"],"manual",["India"],["Patna"],ev={"organisation.type":[2],"geography":[2],"organisation.agents":[2],"current_tooling":[4],"process":[4]}))

# ---- developer/hinglish_consent
E("developer/hinglish_consent","hinglish",False,[
B("Hi, I'm Beacon. What brings you here?"),
V("Hum Hyderabad mein developer hai, Aurum Heights. Main VP Sales hoon."),
B("Team size and lead volume?"),
V("35 log sales mein, aur 900 leads monthly, portals aur Google ads se."),
B("What's broken today?"),
V("LeadSquared use karte hai but site visit tracking aur inventory link nahi hai."),
B("Here's the site visit calendar and inventory view. Who approves?"),
V("Budget mere haath mein hai, main approve kar sakta hoon. Is mahine rollout chahiye."),
B("Can our sales team contact you?"),
V("Haan zaroor, vp.sales@aurumheights.example.com pe mail karo.")],
L("VP Sales","executive","Aurum Heights","developer",35,["no site visit tracking","inventory not linked"],["LeadSquared"],"unsatisfied_crm",["India"],["Hyderabad"],900,900,["portals","Google ads"],"approver","within_30_days",True,None,"vp.sales@aurumheights.example.com",None,
 {"organisation.type":[2],"geography":[2],"organisation.name":[2],"role":[2],"seniority":[2],"organisation.agents":[4],"monthly_leads":[4],"lead_sources":[4],"current_tooling":[6],"pain_points":[6],"process":[6],"influence":[8],"next_step":[8],"consent":[10],"contact":[10]}))
E("developer/hinglish_consent","hinglish",False,[
B("Hello! Beacon here. Tell me about your company."),
V("Hum Mumbai mein redevelopment projects karte hai. 10 sales log hai."),
B("Leads per month?"),
V("Sau ke aas paas, mostly referrals."),
B("Pain points?"),
V("Koi khaas problem nahi hai, Excel se chal raha hai theek."),
B("Here's the Leads list anyway. Would you like sales to contact you?"),
V("Nahi thanks, contact mat karna. Bas dekh raha tha.")],
L(None,"unknown",None,"developer",10,[],["Excel"],"manual",["India"],["Mumbai"],100,100,["referrals"],"unknown","declined",False,
 ev={"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[4],"lead_sources":[4],"pain_points":[6],"current_tooling":[6],"process":[6],"next_step":[8]}))
E("developer/hinglish_consent","hinglish",False,[
B("Hi, I'm Beacon."),
V("Hi, main CEO hoon Coastal Crest Developers ka, Goa mein holiday homes banate hai."),
B("Team and leads?"),
V("8 log sales mein, 150 leads monthly Instagram aur Facebook se."),
B("Main challenge?"),
V("NRI clients ko time pe follow-up nahi hota, aur leads sheet mein kho jaati hai."),
B("Here's the follow-up automation. Next steps?"),
V("Main decide karunga, par shayad 2 mahine baad."),
B("Okay to have sales follow up then?"),
V("Haan, theek hai, contact kar lena. +91 90000 04444")],
L("CEO","owner","Coastal Crest Developers","developer",8,["NRI clients not followed up on time","leads get lost in sheets"],["spreadsheet"],"manual",["India"],["Goa"],150,150,["Instagram","Facebook"],"approver","later",True,None,None,"+91 90000 04444",
 {"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[4],"monthly_leads":[4],"lead_sources":[4],"pain_points":[6],"current_tooling":[6],"process":[6],"influence":[8],"next_step":[8],"consent":[10],"contact":[10]}))
E("developer/hinglish_consent","hinglish",False,[
B("Welcome, Beacon here. What's your role?"),
V("Main CRM executive hoon, Vistara Infra, Noida. Hum residential developer hai."),
B("What's the challenge?"),
V("Hamare paas Zoho hai but callers ki call recording link nahi hoti."),
B("Here's call logging. Who decides purchases?"),
V("Mera koi say nahi hai, management decide karega."),
B("Shall sales contact your team?"),
V("Maybe, mujhe nahi pata. Aap brochure bhej do bas.")],
L("CRM executive","individual_contributor","Vistara Infra","developer",None,["call recordings not linked"],["Zoho"],"unsatisfied_crm",["India"],["Noida"],None,None,None,"none","unknown",False,
 ev={"role":[2],"seniority":[2],"organisation.name":[2],"geography":[2],"organisation.type":[2],"current_tooling":[4],"pain_points":[4],"process":[4],"influence":[6]}))
E("developer/hinglish_consent","hinglish",True,[
B("Hi! I'm Beacon."),
V("Hello, hum Bengaluru ke developer hai, 45 sales staff."),
B("Monthly leads?"),
V("Do hazaar ke aas paas."),
B("Here is the lead distribution screen...")],
L(None,"unknown",None,"developer",45,None,None,"unknown",["India"],["Bengaluru"],2000,2000,ev={"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[4]}))

# ---- brokerage/correction_team_size
E("brokerage/correction_team_size","en",False,[
B("Hi, I'm Beacon. Tell me about your brokerage."),
V("We're Harbour Line Realty in Mumbai, about 20 agents."),
B("How many leads a month?"),
V("Around 400 from 99acres and Facebook."),
V("Sorry, actually we're 40 agents now, we merged with another office last month."),
B("Noted, 40. What's the main pain?"),
V("Leads aren't assigned fairly and follow-ups get missed. We use Excel."),
B("Here's round-robin assignment. Who decides?"),
V("I'm the owner, I decide. Want to start within two weeks."),
B("Can sales contact you?"),
V("Yes, owner@harbourline.example.com")],
L("owner","owner","Harbour Line Realty","brokerage",40,["unfair lead assignment","follow-ups get missed"],["Excel"],"manual",["India"],["Mumbai"],400,400,["99acres","Facebook"],"approver","within_30_days",True,None,"owner@harbourline.example.com",None,
 {"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[5],"monthly_leads":[4],"lead_sources":[4],"pain_points":[7],"current_tooling":[7],"process":[7],"role":[9],"seniority":[9],"influence":[9],"next_step":[9],"consent":[11],"contact":[11]}))
E("brokerage/correction_team_size","hinglish",True,[
B("Hello, Beacon here."),
V("Hum Pune brokerage hai, 10 log hai team mein."),
B("Nice. Lead sources?"),
V("Arre sorry, 10 nahi, 16 log hai, naye joinees bhool gaya. Leads Housing.com se aati hai.")],
L(None,"unknown",None,"brokerage",16,None,None,"unknown",["India"],["Pune"],None,None,["Housing.com"],ev={"organisation.type":[2],"geography":[2],"organisation.agents":[4],"lead_sources":[4]}))
E("brokerage/correction_team_size","en",False,[
B("Hi! Beacon from Leadrat. What's your role?"),
V("Operations manager at Bluestone Brokers, Chennai."),
B("Team size?"),
V("We have 25 agents."),
B("And lead volume?"),
V("About 250 a month. Wait, correction on the team, it's 12 agents, the rest are telecallers who don't sell."),
B("Got it. What's the main issue?"),
V("Our current CRM is slow and doesn't show lead source ROI."),
B("Here's the source-wise report. Who decides?"),
V("I'll recommend it to our MD, he signs."),
B("Should sales follow up?"),
V("Not now, maybe next quarter.")],
L("operations manager","manager","Bluestone Brokers","brokerage",12,["CRM is slow","no lead source ROI"],["CRM"],"unsatisfied_crm",["India"],["Chennai"],250,250,None,"sponsored_evaluator","later",False,
 ev={"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[6],"monthly_leads":[6],"pain_points":[8],"current_tooling":[8],"process":[8],"influence":[10],"next_step":[12]}))
E("brokerage/correction_team_size","hinglish",False,[
B("Hi, I'm Beacon."),
V("Hi, main Kolkata mein Eastern Nest Realty chalata hoon, founder. Team 5 logon ki hai."),
B("Leads per month?"),
V("Ek sau pachaas, MagicBricks se. Aur haan, team 5 nahi, 25 hai, 5 toh sirf managers hai."),
B("Thanks. Tools and pains?"),
V("WhatsApp aur Excel. Duplicate leads aur missed calls sabse bada issue."),
B("Here's duplicate detection. Would you like sales to call you this month?"),
V("Haan, is mahine hi. Main decide karta hoon. 90000 05555.")],
L("founder","owner","Eastern Nest Realty","brokerage",25,["duplicate leads","missed calls"],["WhatsApp","Excel"],"manual",["India"],["Kolkata"],150,150,["MagicBricks"],"approver","within_30_days",True,None,None,"+91 90000 05555",
 {"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[4],"monthly_leads":[4],"lead_sources":[4],"current_tooling":[6],"process":[6],"pain_points":[6],"influence":[8],"next_step":[8],"consent":[8],"contact":[8]}))
E("brokerage/correction_team_size","en",True,[
B("Welcome! I'm Beacon."),
V("Hi, we're a brokerage in Ahmedabad with 30 agents."),
B("Great, what tools do you use?"),
V("Oops, I meant 13 agents, not 30. We use Google Sheets.")],
L(None,"unknown",None,"brokerage",13,None,["Google Sheets"],"manual",["India"],["Ahmedabad"],ev={"organisation.type":[2],"geography":[2],"organisation.agents":[4],"current_tooling":[4],"process":[4]}))

# ---- developer/correction_authority
E("developer/correction_authority","en",False,[
B("Hi, Beacon here. What's your role?"),
V("I'm the owner of Silver Oak Developers in Bengaluru."),
B("Great. Team and leads?"),
V("20 in sales, around 700 leads a month from portals."),
V("Actually I'm not the owner, sorry, I'm the sales manager. My boss decides on software."),
B("No problem. What's the pain?"),
V("Leads get lost between Excel and WhatsApp, and site visit no-shows."),
B("Here's the site visit tracker. Should sales contact you?"),
V("Yes, send details to salesmgr@silveroak.example.com, we want to decide in 3 weeks.")],
L("sales manager","manager","Silver Oak Developers","developer",20,["leads lost between Excel and WhatsApp","site visit no-shows"],["Excel","WhatsApp"],"manual",["India"],["Bengaluru"],700,700,["portals"],"sponsored_evaluator","within_30_days",True,None,"salesmgr@silveroak.example.com",None,
 {"role":[5],"seniority":[5],"influence":[5],"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[4],"monthly_leads":[4],"lead_sources":[4],"pain_points":[7],"current_tooling":[7],"process":[7],"consent":[9],"contact":[9],"next_step":[9]}))
E("developer/correction_authority","hinglish",False,[
B("Hello, Beacon here."),
V("Main Terra Nova Homes se hoon, Pune developer. Main decide karunga CRM ka."),
B("Nice. Team?"),
V("15 log. Leads 300 per month, Facebook aur 99acres."),
B("Pain?"),
V("Excel mein data mess hai, reporting nahi hoti."),
B("Here's the dashboard. So you'd sign off?"),
V("Actually nahi, final approval chairman sir ka hai, main sirf evaluate kar raha hoon unke liye."),
B("Understood. Should sales reach out?"),
V("Haan, is month call karo. +91 90000 06666")],
L(None,"unknown","Terra Nova Homes","developer",15,["messy data in Excel","no reporting"],["Excel"],"manual",["India"],["Pune"],300,300,["Facebook","99acres"],"sponsored_evaluator","within_30_days",True,None,None,"+91 90000 06666",
 {"organisation.name":[2],"organisation.type":[2],"geography":[2],"influence":[8],"organisation.agents":[4],"monthly_leads":[4],"lead_sources":[4],"pain_points":[6],"current_tooling":[6],"process":[6],"next_step":[10],"consent":[10],"contact":[10]}))
E("developer/correction_authority","en",True,[
B("Hi, I'm Beacon."),
V("I'm evaluating CRMs for my boss at Lakeview Estates, a developer in Hyderabad."),
B("Got it. Team size?"),
V("Correction, I actually own the company now, my father handed it over. I make the call. We have 28 sales staff.")],
L("owner","owner","Lakeview Estates","developer",28,None,None,"unknown",["India"],["Hyderabad"],None,None,None,"approver",ev={"organisation.name":[2],"organisation.type":[2],"geography":[2],"role":[4],"seniority":[4],"influence":[4],"organisation.agents":[4]}))
E("developer/correction_authority","en",False,[
B("Welcome! What's your role?"),
V("Director at Riverstone Realty Developers, Kolkata. I approve purchases."),
B("Team and leads?"),
V("18 sales people, 120 leads monthly from newspaper and Facebook."),
B("Pain?"),
V("We use Sell.Do but follow-ups still slip."),
V("Also, to be clear, purchases above a lakh need board approval, so I can only recommend."),
B("Fine. Should sales contact you?"),
V("No, please don't contact me. I'll reach out if needed.")],
L("director","executive","Riverstone Realty Developers","developer",18,["follow-ups slip"],["Sell.Do"],"unsatisfied_crm",["India"],["Kolkata"],120,120,["newspaper","Facebook"],"sponsored_evaluator","declined",False,
 ev={"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[4],"monthly_leads":[4],"lead_sources":[4],"current_tooling":[6],"pain_points":[6],"process":[6],"influence":[7],"next_step":[9]}))
E("developer/correction_authority","hinglish",True,[
B("Hi, Beacon here."),
V("Hum Nagpur mein developer hai. Main MD hoon."),
B("Do you decide on tools?"),
V("Haan... actually nahi, mere partner decide karte hai tech wale cheezon pe, mera koi role nahi.")],
L("MD","executive",None,"developer",None,None,None,"unknown",["India"],["Nagpur"],None,None,None,"none",ev={"organisation.type":[2],"geography":[2],"role":[2],"seniority":[2],"influence":[4]}))

# ---- mixed/correction_volume
E("mixed/correction_volume","hinglish",False,[
B("Hi, I'm Beacon."),
V("Hi, hum Delhi mein brokerage hai, Capital Keys. 22 agents."),
B("Leads per month?"),
V("50 leads per month."),
V("Sorry, 50 nahi 150 leads per month. Mostly 99acres se."),
B("Thanks. Tools and pains?"),
V("Excel. Follow-up miss ho jata hai."),
B("Here's reminders. Who decides and when?"),
V("Main owner hoon. Next month ke baad dekhte hai, abhi rush nahi."),
B("Should sales contact you?"),
V("Haan theek hai, owner@capitalkeys.example.com")],
L("owner","owner","Capital Keys","brokerage",22,["follow-ups get missed"],["Excel"],"manual",["India"],["Delhi"],150,150,["99acres"],"approver","later",True,None,"owner@capitalkeys.example.com",None,
 {"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[5],"lead_sources":[5],"current_tooling":[7],"process":[7],"pain_points":[7],"role":[9],"seniority":[9],"influence":[9],"next_step":[9],"consent":[11],"contact":[11]}))
E("mixed/correction_volume","en",True,[
B("Hello, Beacon here."),
V("We're a channel partner in Dubai, 9 agents, getting around 1000 leads a month."),
B("That's a lot for 9 agents!"),
V("Ha, you're right, I meant 100, not 1000.")],
L(None,"unknown",None,"channel_partner",9,None,None,"unknown",["UAE"],["Dubai"],100,100,ev={"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[4]}))
E("mixed/correction_volume","en",False,[
B("Hi, I'm Beacon. Tell me about your company."),
V("Marketing head at Prestige Arc Developers, Mumbai. 50 in sales."),
B("Leads?"),
V("Roughly 300 a month from Google ads and portals."),
B("And pains?"),
V("Our CRM can't dedupe, and managers can't see agent activity."),
V("Correction on leads: it's more like 600 to 800, I checked the dashboard."),
B("Here's dedupe and the activity view. Who decides?"),
V("The CEO, I'm shortlisting for him."),
B("Can sales contact you?"),
V("Yes, this month please. mktg@prestigearc.example.com")],
L("marketing head","manager","Prestige Arc Developers","developer",50,["CRM cannot dedupe","no visibility on agent activity"],["CRM"],"unsatisfied_crm",["India"],["Mumbai"],600,800,["Google ads","portals"],"sponsored_evaluator","within_30_days",True,None,"mktg@prestigearc.example.com",None,
 {"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[7],"lead_sources":[4],"pain_points":[6],"current_tooling":[6],"process":[6],"influence":[9],"next_step":[11],"consent":[11],"contact":[11]}))
E("mixed/correction_volume","hinglish",True,[
B("Hi, Beacon here."),
V("Hum Surat mein brokerage hai, 7 log. Mahine ki do sau leads aati hai."),
B("Okay, 200 a month. Sources?"),
V("Nahi nahi, do sau nahi, bees-pachees hi aati hai, 20-25. Walk-ins se.")],
L(None,"unknown",None,"brokerage",7,None,None,"unknown",["India"],["Surat"],20,25,["walk-ins"],ev={"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[4],"lead_sources":[4]}))
E("mixed/correction_volume","en",False,[
B("Hi, I'm Beacon."),
V("I run a channel partner firm in Gurgaon, Northstar Advisory. Founder. 30 agents."),
B("Leads per month?"),
V("About 2000."),
B("Tools and pain?"),
V("HubSpot, but it doesn't fit real estate, no inventory or site visits."),
V("Oh, and my 2000 was quarterly. Monthly it's around 700."),
B("Here's inventory mapping. When would you decide?"),
V("I decide, within this month."),
B("Should sales call you?"),
V("Yes. +91 90000 07777")],
L("founder","owner","Northstar Advisory","channel_partner",30,["HubSpot doesn't fit real estate","no inventory or site visit tracking"],["HubSpot"],"unsatisfied_crm",["India"],["Gurgaon"],700,700,None,"approver","within_30_days",True,None,None,"+91 90000 07777",
 {"role":[2],"seniority":[2],"organisation.name":[2],"organisation.type":[2],"geography":[2],"organisation.agents":[2],"monthly_leads":[7],"current_tooling":[6],"pain_points":[6],"process":[6],"influence":[9],"next_step":[9],"consent":[11],"contact":[11]}))
E("mixed/correction_volume","hinglish",False,[
B("Hello, Beacon here."),
V("Main Chandigarh mein broker hoon, 4 log ki team, Excel use karte hai."),
B("Leads per month?"),
V("Tees ke aas paas. Actually nahi, pichle mahine assi aayi thi, toh 80 bolo."),
B("What's the pain?"),
V("Koi bada pain nahi, bas dekh raha tha."),
B("Would you like sales to contact you?"),
V("Nahi, zarurat nahi. Thanks.")],
L(None,"unknown",None,"brokerage",4,[],["Excel"],"manual",["India"],["Chandigarh"],80,80,None,"unknown","declined",False,
 ev={"organisation.type":[2],"geography":[2],"organisation.agents":[2],"current_tooling":[2],"process":[2],"monthly_leads":[4],"pain_points":[6],"next_step":[8]}))
assert len(rows)==40
open(OUT,'w',encoding='utf-8').write("\n".join(json.dumps(r,ensure_ascii=False) for r in rows)+"\n")
