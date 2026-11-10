"""Build the manager demo video: Soniox voiceover slides + the recorded live-demo clips.

Put your screen recordings (with Beacon's voice and your mic) in docs/demo-video/clips/:
    1_register.mp4   2_question.mp4   3_followup.mp4   4_surya.mp4
A missing clip is skipped. Clip audio is kept as recorded; the voiceover plays only on slides.
    .venv\\Scripts\\python docs/demo-video/build_video.py
Output: docs/demo-video/Beacon_Demo.mp4
"""
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
WORK, CLIPS, VOICE = HERE / '.work', HERE / 'clips', HERE / 'narration'
# (slide id, narration scene, demo clip played after it)
ORDER = [('intro', 'scene_01', None),
         ('ch-register', 'scene_02', '1_register.mp4'),
         ('ch-question', 'scene_03', '2_question.mp4'),
         ('ch-followup', 'scene_04', '3_followup.mp4'),
         ('ch-surya', 'scene_05', '4_surya.mp4'),
         ('architecture', 'scene_06', None),
         ('stack', 'scene_07', None),
         ('vector', 'scene_08', None),
         ('cost', 'scene_09', None),
         ('closing', 'scene_10', None)]
VIDEO = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', '30']
AUDIO = ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *args], check=True)


def render_slides():
    (WORK / 'slides').mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        page = p.chromium.launch(channel='chrome').new_page(viewport={'width': 1920, 'height': 1080})
        page.goto((HERE / 'slides.html').as_uri())
        page.wait_for_timeout(500)
        for slide, _, _ in ORDER:
            page.locator(f'#{slide}').screenshot(path=str(WORK / 'slides' / f'{slide}.png'))


def has_audio(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries',
                          'stream=index', '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return bool(out.stdout.strip())


def main():
    missing = [s for _, s, _ in ORDER if not (VOICE / f'{s}.wav').exists()]
    if missing:
        sys.exit(f'Narration missing: {missing}. Run make_narration.py first.')
    render_slides()
    parts = []
    for i, (slide, scene, clip) in enumerate(ORDER):
        seg = WORK / f'{i:02d}a_{slide}.mp4'
        # Half a second of silence either side of the voiceover, slide fades in and out.
        ffmpeg('-loop', '1', '-i', str(WORK / 'slides' / f'{slide}.png'), '-i', str(VOICE / f'{scene}.wav'),
               '-filter_complex', '[1:a]loudnorm=I=-16:TP=-1.5,aresample=48000,adelay=500|500,apad=pad_dur=0.8[a];'
               '[0:v]fade=t=in:st=0:d=0.4,format=yuv420p[v]',
               '-map', '[v]', '-map', '[a]', '-shortest', *VIDEO, *AUDIO, str(seg))
        parts.append(seg)
        if clip and (CLIPS / clip).exists():
            src, seg = CLIPS / clip, WORK / f'{i:02d}b_{slide}.mp4'
            scale = 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0b1020,setsar=1'
            if has_audio(src):
                ffmpeg('-i', str(src), '-vf', scale, '-af', 'loudnorm=I=-16:TP=-1.5', *VIDEO, *AUDIO, str(seg))
            else:
                ffmpeg('-i', str(src), '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-vf', scale,
                       '-shortest', *VIDEO, *AUDIO, str(seg))
            parts.append(seg)
        elif clip:
            print(f'Skipping missing clip: clips/{clip}')
    listing = WORK / 'concat.txt'
    listing.write_text(''.join(f"file '{p.as_posix()}'\n" for p in parts), encoding='utf-8')
    final = HERE / 'Beacon_Demo.mp4'
    ffmpeg('-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', str(final))
    print('Video ready:', final)


if __name__ == '__main__':
    main()
