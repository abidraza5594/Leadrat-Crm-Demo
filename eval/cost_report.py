"""Explicit capacity and usage assumptions, separate from measured API billing."""
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass
class Assumptions:
    visitors:int=10000
    engagement:float=.10
    sessions_per_visitor:float=1.1
    questions:int=20
    voice_share:float=.60
    soniox_tts_enabled:bool=False
    input_tokens_per_turn:int=12000
    output_tokens_per_turn:int=1000
    qualification_input:int=4000
    qualification_output:int=300
    stt_stream_seconds:float=30
    user_speech_seconds:float=10
    tts_seconds:float=20
    answer_characters:int=350
    greeting_seconds:float=8
    greeting_characters:int=120
    preview_seconds_per_turn:float=50
    preview_fps:float=3
    frame_kb:float=60
    site_mb_per_visit:float=3
    egress_usd_per_gb:float=.09
    hosting_usd:float=100
    database_usd:float=25
    monitoring_usd:float=10
    reserve:float=.20
    usd_inr:float=90

def estimate(a):
    sessions=a.visitors*a.engagement*a.sessions_per_visitor
    turns=sessions*a.questions;voice_turns=turns*a.voice_share;voice_sessions=sessions*a.voice_share
    input_tokens=turns*a.input_tokens_per_turn+sessions*a.qualification_input
    output_tokens=turns*a.output_tokens_per_turn+sessions*a.qualification_output
    llm_peak=(input_tokens*.30+output_tokens*1.20)/1e6
    llm_off=llm_peak/2
    # Soniox's published reference: 30k audio tokens/hour; 15k speech text tokens/hour.
    stt_audio=voice_turns*a.stt_stream_seconds/3600*30000
    stt_text=voice_turns*a.user_speech_seconds/3600*15000
    stt=(stt_audio*2+stt_text*4)/1e6
    tts_audio=(voice_turns*a.tts_seconds+voice_sessions*a.greeting_seconds)/3600*30000
    tts_text=(voice_turns*a.answer_characters+voice_sessions*a.greeting_characters)*.3
    tts=(tts_audio*21.50+tts_text*4)/1e6 if a.soniox_tts_enabled else 0
    # Decimal GB for planning; actual hosting billing units and allowances may differ.
    egress_gb=(turns*a.preview_seconds_per_turn*a.preview_fps*a.frame_kb/1e6
               +a.visitors*a.site_mb_per_visit/1000)
    network=egress_gb*a.egress_usd_per_gb
    fixed=a.hosting_usd+a.database_usd+a.monitoring_usd
    variable_peak=llm_peak+stt+tts+network
    variable_off=llm_off+stt+tts+network
    return dict(sessions=sessions,turns=turns,llm_off=llm_off,llm_peak=llm_peak,stt=stt,tts=tts,
                egress_gb=egress_gb,network=network,fixed=fixed,
                total_off=fixed+variable_off*(1+a.reserve),total_peak=fixed+variable_peak*(1+a.reserve),
                api_per_text_turn=(a.input_tokens_per_turn*.30+a.output_tokens_per_turn*1.20)/1e6)

def main():
    out=Path('outputs/feedback-2026-10-12');out.mkdir(parents=True,exist_ok=True)
    a=Assumptions();rows=[]
    for visitors,engagement,hosting in [(1000,.05,40),(10000,.10,100),(50000,.20,400)]:
        for questions in [20,30,50]:
            scenario=Assumptions(visitors=visitors,engagement=engagement,questions=questions,hosting_usd=hosting)
            rows.append({'assumptions':asdict(scenario),'result':estimate(scenario)})
    (out/'cost-scenarios.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    template=Path('eval/cost_report_template.html').read_text('utf8')
    (out/'Beacon_Feedback_and_Cost.html').write_text(template.replace('__SCENARIOS__',json.dumps(rows)).replace('__DEFAULTS__',json.dumps(asdict(a))),encoding='utf8')
    print(json.dumps(estimate(a),indent=2))

if __name__=='__main__':main()
