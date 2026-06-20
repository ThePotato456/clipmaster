#!/usr/bin/env python3
"""Transcribe audio/video files and run the transcript through moderation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_TRANSCRIPTION_MODEL = "whisper-1"
DEFAULT_MODERATION_MODEL = "text-moderation-latest"
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".mp4"}
SCORE_PRINT_THRESHOLD = 1e-3


class ClipmasterError(RuntimeError):
    """Raised for recoverable CLI errors."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe an MP3 or MP4 file and moderate the transcript."
    )
    parser.add_argument("file", type=Path, help="Path to an .mp3 or .mp4 file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path for the moderation JSON. Defaults to <audio-file>.json.",
    )
    parser.add_argument(
        "--transcription-model",
        default=DEFAULT_TRANSCRIPTION_MODEL,
        help=f"OpenAI transcription model. Default: {DEFAULT_TRANSCRIPTION_MODEL}.",
    )
    parser.add_argument(
        "--moderation-model",
        default=DEFAULT_MODERATION_MODEL,
        help=f"OpenAI moderation model. Default: {DEFAULT_MODERATION_MODEL}.",
    )
    parser.add_argument(
        "--keep-converted-audio",
        action="store_true",
        default=True,
        help="Keep MP3 files generated from MP4 input. This is the default.",
    )
    parser.add_argument(
        "--delete-converted-audio",
        action="store_false",
        dest="keep_converted_audio",
        help="Delete the generated MP3 after transcription.",
    )
    return parser


def create_client() -> Any:
    try:
        from dotenv import load_dotenv
        from openai import OpenAI
    except ImportError as exc:
        raise ClipmasterError(
            "Missing dependencies. Run: python3 -m pip install -r requirements.txt"
        ) from exc

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
    if not api_key:
        raise ClipmasterError(
            "Set OPENAI_API_KEY in your environment or .env file before running."
        )

    return OpenAI(api_key=api_key)


def validate_input(path: Path) -> Path:
    path = path.expanduser().resolve()

    if not path.exists():
        raise ClipmasterError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise ClipmasterError(f"Input path is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise ClipmasterError(f"Unsupported file type {path.suffix!r}. Use {supported}.")

    return path


def convert_mp4_to_mp3(path: Path) -> Path:
    output_path = path.with_suffix(".mp3")
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(path),
        "-vn",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "192k",
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise ClipmasterError("ffmpeg is required to convert MP4 files.") from exc
    except subprocess.CalledProcessError as exc:
        raise ClipmasterError(f"ffmpeg failed to convert {path}") from exc

    return output_path


def prepare_audio(path: Path) -> tuple[Path, bool]:
    if path.suffix.lower() != ".mp4":
        return path, False

    return convert_mp4_to_mp3(path), True


def transcribe_audio(client: Any, path: Path, model: str) -> str:
    with path.open("rb") as audio_file:
        transcript = client.audio.transcriptions.create(model=model, file=audio_file)

    text = getattr(transcript, "text", None)
    if not text:
        raise ClipmasterError("Transcription completed but returned no text.")

    return text


def moderate_text(client: Any, text: str, model: str) -> dict[str, Any]:
    moderation = client.moderations.create(input=text, model=model)
    result = moderation.results[0]
    if hasattr(result, "model_dump"):
        payload = result.model_dump(mode="json")
    else:
        payload = result.dict()
    payload["message"] = text
    return payload


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        json.dump(data, output_file, indent=2)
        output_file.write("\n")


def print_report(moderation: dict[str, Any]) -> None:
    print(f"Message: {moderation['message']}")

    categories = moderation.get("categories", {})
    scores = moderation.get("category_scores", {})

    for category in sorted(categories):
        score = float(scores.get(category, 0))
        if score >= SCORE_PRINT_THRESHOLD:
            print(f"Category: {category} Score: {score * 100}%")

    print(f"Flagged: {moderation.get('flagged', False)}")


def analyze_file(
    input_path: Path,
    output_path: Path | None,
    transcription_model: str,
    moderation_model: str,
    keep_converted_audio: bool,
) -> Path:
    source_path = validate_input(input_path)
    client = create_client()
    audio_path, was_converted = prepare_audio(source_path)
    output_path = output_path or audio_path.with_name(f"{audio_path.name}.json")

    try:
        transcript = transcribe_audio(client, audio_path, transcription_model)
        moderation = moderate_text(client, transcript, moderation_model)
        write_json(output_path, moderation)
        print_report(moderation)
        return output_path
    finally:
        if was_converted and not keep_converted_audio:
            audio_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        output_path = analyze_file(
            input_path=args.file,
            output_path=args.output,
            transcription_model=args.transcription_model,
            moderation_model=args.moderation_model,
            keep_converted_audio=args.keep_converted_audio,
        )
    except ClipmasterError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if exc.__class__.__module__.startswith("openai"):
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        raise

    print(f"Saved moderation JSON: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
