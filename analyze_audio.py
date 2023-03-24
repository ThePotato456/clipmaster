import os, subprocess, openai, sys, json, math

from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")

def convert_mp4_to_mp3(file):
    input_file = f"{file}"
    output_file = "{0}.mp3".format(file.replace(".mp4", ""))
    ffmpeg_cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', input_file, '-vn', '-ar', '44100', '-ac', '2', '-b:a', '192k', output_file]
    try:
        subprocess.check_call(ffmpeg_cmd)
        return output_file
    except subprocess.CalledProcessError as e:
        return None

def convert_to_decimal(float):
    return format(float, '.16f')

def analyze_audio(file):
    audio_file = open(file, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript.text

def moderate_text(text):
    moderation = openai.Moderation.create(input=text, model='text-moderation-latest')
    return moderation.results[0]

def moderate_file(file):
    if '.mp4' in file:
        audio = convert_mp4_to_mp3(sys.argv[1])
    else:
        audio = file
    transcript = analyze_audio(audio)
    moderation = moderate_text(transcript)
    moderation['message'] = transcript
    with open(f'{audio}.json', 'w') as file: json.dump(moderation, file, indent=2)
    return moderation


if __name__ == "__main__":
    if len(sys.argv) > 1:
        moderation = moderate_file(sys.argv[1])
        print('Message: {0}'.format(moderation['message']))
        for category in moderation.categories:
            category_score = float(moderation.category_scores[category])
            if float(category_score) >= math.pow(10, -3):
                print(f'Category: {category} Score: {category_score}')
        print(f'Flagged: {moderation.flagged}')
    else:
        print("Usage: python3 analyze_audio.py <file>")