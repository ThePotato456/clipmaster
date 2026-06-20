# Clipmaster

Clipmaster transcribes `.mp3` and `.mp4` files with OpenAI's Whisper API, sends
the transcript to OpenAI's Moderation API, prints a compact report, and saves the
full moderation response as JSON.

## Features

- Supports `.mp3` input directly.
- Converts `.mp4` input to `.mp3` with `ffmpeg` before transcription.
- Writes moderation JSON next to the analyzed audio by default.
- Loads secrets from either the shell environment or a local `.env` file.
- Keeps compatibility with the original `OPENAI_KEY` environment variable while
  preferring `OPENAI_API_KEY`.

## Requirements

- Python 3.10 or newer
- `ffmpeg` for `.mp4` input
- An OpenAI API key

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your key:

```bash
OPENAI_API_KEY=your_api_key_here
```

## Usage

Analyze an MP3:

```bash
python3 analyze_audio.py path/to/audio.mp3
```

Analyze an MP4:

```bash
python3 analyze_audio.py path/to/video.mp4
```

Write the JSON output to a specific path:

```bash
python3 analyze_audio.py path/to/audio.mp3 --output reports/audio.json
```

Delete the MP3 generated from MP4 input after analysis:

```bash
python3 analyze_audio.py path/to/video.mp4 --delete-converted-audio
```

Show all options:

```bash
python3 analyze_audio.py --help
```

## Output

The command prints the transcript, moderation categories above the display
threshold, whether the transcript was flagged, and the JSON path that was saved.

By default, JSON output is written as:

- `audio.mp3.json` for `audio.mp3`
- `video.mp3.json` for `video.mp4` after conversion

## Notes

- `.mp4` input requires `ffmpeg` to be installed and available on `PATH`.
- Generated transcripts may contain sensitive content. Keep `.env`, local audio,
  and moderation JSON out of version control unless they are intentionally public.

## License

MIT. See [LICENSE](LICENSE).
