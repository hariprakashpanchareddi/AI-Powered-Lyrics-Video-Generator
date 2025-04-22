# app.py
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import tempfile
import datetime
from difflib import SequenceMatcher
import whisperx
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import TextClip, ColorClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import pysrt

# Create Flask app serving static files from project root
app = Flask(__name__, static_folder='.', static_url_path='')

# Helpers for alignment and SRT generation
def match_lyrics_to_words(lyrics, words):
    aligned, used_idxs = [], set()
    for line in lyrics:
        best = {"score": 0, "start": None, "end": None, "indexes": []}
        for i in range(len(words)):
            if i in used_idxs:
                continue
            text_accum = ""
            for j in range(i, len(words)):
                if j in used_idxs:
                    break
                text_accum += words[j]["word"] + " "
                score = SequenceMatcher(None,
                                        line.lower(),
                                        text_accum.strip().lower())
                score = score.ratio()
                if score > best["score"]:
                    best = {
                        "score": score,
                        "start": words[i]["start"],
                        "end": words[j]["end"],
                        "indexes": list(range(i, j+1))
                    }
        if best["start"] is not None:
            aligned.append({"lyric": line, "start": best["start"], "end": best["end"]})
            used_idxs.update(best["indexes"])
        else:
            aligned.append({"lyric": line, "start": None, "end": None})
    return aligned


def enforce_sequence(aligned, min_gap=0.01):
    last_end = 0.0
    for e in aligned:
        s = e["start"] if e["start"] is not None else last_end
        t = e["end"] if e["end"] is not None else s + min_gap
        if s < last_end:
            s = last_end
        if t <= s:
            t = s + min_gap
        e["start"], e["end"] = s, t
        last_end = t
    return aligned


def fmt(ts):
    td = datetime.timedelta(seconds=ts)
    tot = int(td.total_seconds())
    hh = tot // 3600
    mm = (tot % 3600) // 60
    ss = tot % 60
    ms = int((td.total_seconds() - tot) * 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def create_srt(aligned, srt_path):
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, e in enumerate(aligned, 1):
            f.write(f"{i}\n{fmt(e['start'])} --> {fmt(e['end'])}\n{e['lyric']}\n\n")


def align_lyrics(audio_path, lyrics_path, device="cpu"):
    # Load WhisperX model and audio
    model = whisperx.load_model("small", device=device, compute_type="float32")
    audio = whisperx.load_audio(audio_path)

    # Transcribe and align
    result = model.transcribe(audio_path)
    segments = result["segments"]
    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    aligned_res = whisperx.align(segments, align_model, metadata, audio, device)
    words = aligned_res["word_segments"]

    # Read lyrics lines
    with open(lyrics_path, encoding="utf-8") as f:
        lyrics = [L.strip() for L in f if L.strip()]

    # Match and enforce sequence
    aligned = match_lyrics_to_words(lyrics, words)
    return enforce_sequence(aligned)


def generate_video(audio_path, srt_path, output_path):
    from PIL import Image
    import numpy as np
    from moviepy.video.VideoClip import ImageClip

    # Load audio
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    # Load and resize background image
    img = Image.open("background.jpeg")  # <-- set your image path here
    img_resized = img.resize((1280, 720), Image.Resampling.LANCZOS)
    img_array = np.array(img_resized)
    bg = ImageClip(img_array).with_duration(duration)

    # Load SRT and build text clips
    subs = pysrt.open(srt_path)
    clips = []
    last_end = 0.0
    for sub in subs:
        start = sub.start.ordinal / 1000.0
        end = sub.end.ordinal / 1000.0
        if start < last_end:
            start = last_end
        dur = end - start
        if dur <= 0:
            continue
        txt = TextClip(
            text=sub.text,
            font_size=48,
            font=r'C:\WINDOWS\FONTS\COPRGTL.TTF',
            color="white",
            bg_color="black",
            method='label',
            transparent=False
        ).with_start(start).with_duration(dur).with_position("center")
        clips.append(txt)
        last_end = start + dur

    # Composite clips and attach audio
    video = CompositeVideoClip([bg] + clips).with_audio(audio)
    video.write_videofile(output_path, fps=24)


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/generate', methods=['POST'])
def generate():
    # Get inputs
    audio_file = request.files.get('audio')
    lyrics_file = request.files.get('lyrics')
    video_name = request.form.get('videoName') or 'output'

    # Secure filenames
    audio_fname = secure_filename(audio_file.filename)
    lyrics_fname = secure_filename(lyrics_file.filename)
    base_name = os.path.splitext(video_name)[0]
    mp4_name = f"{base_name}.mp4"
    srt_name = f"{base_name}.srt"

    # Save uploads to temp
    tmp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(tmp_dir, audio_fname)
    lyrics_path = os.path.join(tmp_dir, lyrics_fname)
    audio_file.save(audio_path)
    lyrics_file.save(lyrics_path)

    # Align and create SRT
    aligned = align_lyrics(audio_path, lyrics_path)
    gen_dir = os.path.join(os.getcwd(), 'generated')
    os.makedirs(gen_dir, exist_ok=True)
    srt_path = os.path.join(gen_dir, srt_name)
    create_srt(aligned, srt_path)

    # Generate video
    video_path = os.path.join(gen_dir, mp4_name)
    generate_video(audio_path, srt_path, video_path)

    # Clean up temp files
    try:
        os.remove(audio_path)
        os.remove(lyrics_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass

    # Return URLs for frontend
    return jsonify({
        'video_url': f"/generated/{mp4_name}",
        'caption_url': f"/generated/{srt_name}"
    })

if __name__ == '__main__':
    app.run(debug=True)
