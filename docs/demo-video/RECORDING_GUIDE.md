# Beacon demo video — recording guide

Final video ka flow (`build_video.py` khud jodta hai):

| # | Kya chalega | Awaaz |
|---|---|---|
| 1 | Intro slide | Soniox voiceover (aapki cloned voice) |
| 2 | Chapter slide "Visitor registration" → **clip 1** | voiceover → demo ki asli awaaz |
| 3 | Chapter slide "Ask a question" → **clip 2** | voiceover → Beacon ki voice + aapki mic |
| 4 | Chapter slide "Follow-up questions" → **clip 3** | voiceover → Beacon ki voice + aapki mic |
| 5 | Chapter slide "Lead in Surya tenant" → **clip 4** | voiceover → demo ki asli awaaz |
| 6–10 | Architecture, Tech stack, Vector DB (384 dim), Vendors & cost, Summary | Soniox voiceover |

Voiceover sirf slides par bajta hai, demo clips ke upar nahi — isliye Beacon ki voice aur aapki voice saaf sunai degi.

## 1. Recording setup (OBS Studio — free)

1. OBS install karein: `winget install OBSProject.OBSStudio`
2. Settings → Video: Base aur Output **1920×1080**, FPS **30**.
3. Settings → Output → Recording format: **mp4**.
4. Sources: **Display Capture** (ya Window Capture → browser).
5. Audio Mixer mein dono on rakhein:
   - **Desktop Audio** → Beacon ki voice record hogi
   - **Mic/Aux** → aapki voice record hogi
   Test karke dekh lein ki dono meter hil rahe hain. Headphones lagayein, warna speaker ki awaaz mic mein dobara aayegi (echo).
6. Browser zoom 100%, notifications band (Focus Assist on).

Har part ko alag file mein record karein aur `docs/demo-video/clips/` mein ye naam dein:
`1_register.mp4`, `2_question.mp4`, `3_followup.mp4`, `4_surya.mp4`.
(Ek lambi recording ho to OBS mein bas Stop/Start karte rahein har part ke beech.)

## 2. Kya record karna hai

Beacon start karein (`./start.ps1`) aur test website **http://localhost:8011** kholein.

**Clip 1 — Registration (≈30 s)**
- "Start exploring" click karein — left mein live CRM turant dikhega.
- Naam, phone (country code ke saath), email bharein aur Save. Jo details daalein, wahi clip 4 mein dikhani hain — likh kar rakh lein.

**Clip 2 — Product question + live demo (≈1.5–2 min)**
Mic button dabakar bol kar puchhein (taaki aapki voice aur speech-to-text dono dikhein):
1. "How do I add a new lead?" — Beacon Add Lead screen kholega aur bolega.
2. Hinglish mein: "Leads ka status kaise update karte hain?"
3. "Bulk delete kaise karte hain?" — Beacon select-all tick karke Bulk Delete highlight karega, click nahi karega (safety dikhane ke liye accha hai).
Har jawab poora sunne dein, beech mein na bolein.

**Clip 3 — Follow-up questions (≈1–1.5 min)**
Beacon ke business questions ke jawab dein, jaise:
- "Are you a brokerage, a developer or a channel partner?" → "Developer"
- "How many people are on your sales team?" → "25"
- "Roughly how many new leads do you get in a month?" → "around 2000"
- "What is the biggest problem…?" → "Follow-ups miss ho jaate hain"
Beech mein ek product question bhi puchh sakte hain — Beacon pehle jawab dega, phir bacha hua business question "By the way…" se dobara puchhega. Ye context samajhne ki capability dikhata hai.

**Clip 4 — Surya tenant proof (≈30 s)**
- Naye tab mein **https://surya.leadrat.info/** (Surya QA) login karein — login recording shuru karne se *pehle* kar lein, taaki password video mein na aaye.
- Manage Leads kholein, clip 1 wala naam/phone search karein, lead kholkar naam, phone, email aur Source = Website dikhayein.

## 3. Video banana

```bash
python docs/demo-video/make_narration.py
```

```bash
.venv/Scripts/python docs/demo-video/build_video.py
```

Output: `docs/demo-video/Beacon_Demo.mp4`. Voiceover ka text badalna ho to `narration.json` edit karke dono commands dobara chalayein; slides ka text `slides.html` mein hai.

## 4. Bhejne se pehle check

- Video mein koi password, API key ya `.env` file na dikhe.
- Clip 1 ki details aur clip 4 ki lead match karein.
- Beacon ki voice, aapki voice aur voiceover — teenon ki volume ek jaisi lage (build script loudness normalize karta hai).
