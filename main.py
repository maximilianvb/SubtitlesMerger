import moviepy.editor as mp
import subprocess
import wave
import json
from vosk import Model, KaldiRecognizer
import re

movie_filename = 'movie.mp4'
subtitle_filename = 'subtitles.srt'

def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

def separate_audio(movie):
    time_area = get_sec(subs[int(len(subs)/4)][1][0])
    sync_clip = movie.subclip(time_area - 30, time_area + 30)
    movie_path = "sync_clip.mp4"
    sync_clip.write_videofile(movie_path)
    command = f"ffmpeg -i {movie_path} -ab 160k -ac 1 -ar 44100 -vn audio.wav"
    subprocess.call(command, shell=True)

def detect_sub_delay(subs):
    delta = 0
    model = Model('models')
    wf = wave.open('audio.wav', 'rb')
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)
    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            part_result = json.loads(rec.Result())
            print(part_result['text'])
            for matcher in subs[int(len(subs)/4-10):int(len(subs)/4+10)]:
                match = re.sub('[^A-Za-z0-9]+', ' ', matcher[2].lower())
                if not part_result['text'] == '':
                    seeking = part_result['text']
                    if match in seeking:
                        first_matching_word = match.split(' ')[0]
                        for word in part_result['result']:
                            if word['word'] == first_matching_word:
                                word_start = word['start']
                                ref = get_sec(subs[int(len(subs)/4)][1][0])
                                delta = (30 - word_start + get_sec(matcher[1][0]) - ref) * -1
                        part_result['result'][0]
            results.append(part_result)
    part_result = json.loads(rec.FinalResult())
    results.append(part_result)
    print('calculated delta: ' + str(delta))
    return delta

with open(subtitle_filename, 'r') as f:
    subs = f.read().split('\n\n')
    subs.pop(-1) # removes the last empty line from the srt file.
    for i, line_data in enumerate(subs):
        subs[i] = line_data.split('\n')
        subs[i][1] = subs[i][1].split(' --> ')
        for j, time in enumerate(subs[i][1]):
            subs[i][1][j] = time.split(',')[0]

movie = mp.VideoFileClip(movie_filename)
separate_audio(movie)
delay = detect_sub_delay(subs)

movie = movie.subclip(0, 200)
clips = [movie]
for sub in subs[:10]:
    start, end = sub[1][0], sub[1][1]
    if len(sub) == 4:
        text = mp.TextClip(sub[2] + '\n' + sub[3], font='Arial', fontsize=24, color='white')
    else:
        text = mp.TextClip(sub[2] + '\n', font='Arial', fontsize=24, color='white')
    text = text.set_position('bottom', 'center')
    text = text.set_duration(get_sec(end)-get_sec(start))
    text = text.set_start(get_sec(start) + int(delay))
    clips.append(text)

final = mp.CompositeVideoClip(clips)
final.write_videofile('final.mp4')