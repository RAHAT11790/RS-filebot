# app.py
import gradio as gr
import os
import tempfile
import whisper
from transformers import MarianMTModel, MarianTokenizer
from TTS.api import TTS
import moviepy.editor as mp

# Models
whisper_model = whisper.load_model("small")
tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ja-hi")
trans_model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-ja-hi")
tts = TTS("tts_models/multilingual/multi-dataset/hi")

SEGMENT_LENGTH = 120  # seconds per segment

def dub_long_video(video_file):
    if video_file is None:
        return None
    workdir = tempfile.mkdtemp(prefix="dub_")
    input_path = video_file.name if hasattr(video_file, "name") else video_file
    video = mp.VideoFileClip(input_path)
    total_duration = int(video.duration)
    dubbed_segments = []
    start = 0
    idx = 1
    while start < total_duration:
        end = min(start + SEGMENT_LENGTH, total_duration)
        segment_path = os.path.join(workdir, f"segment_{idx}.mp4")
        video.subclip(start, end).write_videofile(segment_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        clip_seg = mp.VideoFileClip(segment_path)
        audio_path = os.path.join(workdir, f"audio_{idx}.wav")
        clip_seg.audio.write_audiofile(audio_path, verbose=False, logger=None)
        res = whisper_model.transcribe(audio_path, language="ja")
        jp_text = res.get("text", "")
        translated = trans_model.generate(**tokenizer([jp_text], return_tensors="pt", padding=True))
        hi_text = tokenizer.decode(translated[0], skip_special_tokens=True)
        tts_path = os.path.join(workdir, f"hindi_audio_{idx}.wav")
        tts.tts_to_file(text=hi_text, file_path=tts_path)
        final_seg = clip_seg.set_audio(mp.AudioFileClip(tts_path))
        final_seg_path = os.path.join(workdir, f"dubbed_segment_{idx}.mp4")
        final_seg.write_videofile(final_seg_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        dubbed_segments.append(final_seg_path)
        idx += 1
        start += SEGMENT_LENGTH
    concat_file = os.path.join(workdir, "segments_list.txt")
    with open(concat_file, "w") as f:
        for seg in dubbed_segments:
            f.write(f"file '{seg}'\n")
    output_path = os.path.join(workdir, "final_dubbed_video.mp4")
    os.system(f"ffmpeg -f concat -safe 0 -i {concat_file} -c copy {output_path}")
    return output_path

demo = gr.Interface(
    fn=dub_long_video,
    inputs=gr.Video(label="Upload Japanese Video"),
    outputs=gr.Video(label="Hindi Dubbed Video"),
    title="Anime Hindi Dubbing App",
    description="Upload Japanese anime video. Segment-wise dubbing, Hindi TTS generated. Mobile-friendly UI.",
    allow_flagging="never"
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
