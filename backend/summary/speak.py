"""Read-aloud: summary text in, presigned mp3 URL out (tested on sample data).

speak(statement_id, text, lang="en") -> presigned URL (valid 1 hour)

Polly neural voice at a slower rate (SSML), mp3 stored at
s3://$AUDIO_BUCKET/audio/<statement_id>-<lang>.mp3 with a hash of the text in
object metadata; if the stored hash matches, Polly is skipped.

Voice map (neural):
  en -> Joanna (US English)
  es -> Lupe   (US Spanish)

Env: AWS_REGION, AUDIO_BUCKET.

Usage: python -m backend.summary.speak problem "Some text to read" [--lang=es]
"""
import hashlib
import os
import sys
from xml.sax.saxutils import escape

VOICE_MAP = {
    "en": "Joanna",
    "es": "Lupe",
}
RATE = "slow"
URL_SECONDS = 3600


def _ssml(text):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    body = "<break time=\"500ms\"/>".join(escape(p) for p in paragraphs)
    return f'<speak><prosody rate="{RATE}">{body}</prosody></speak>'


def speak(statement_id, text, lang="en", s3=None, polly=None):
    import boto3
    from botocore.exceptions import ClientError

    voice = VOICE_MAP.get(lang)
    if voice is None:
        raise ValueError(f"unsupported lang '{lang}'; supported: {sorted(VOICE_MAP)}")

    region = os.environ.get("AWS_REGION")
    s3 = s3 or boto3.client("s3", region_name=region)
    bucket = os.environ["AUDIO_BUCKET"]
    key = f"audio/{statement_id}-{lang}.mp3"
    digest = hashlib.sha256(f"{voice}|{RATE}|{text}".encode()).hexdigest()

    try:
        cached = s3.head_object(Bucket=bucket, Key=key)["Metadata"].get("text-sha256") == digest
    except ClientError:
        cached = False

    if not cached:
        polly = polly or boto3.client("polly", region_name=region)
        audio = polly.synthesize_speech(
            Text=_ssml(text),
            TextType="ssml",
            Engine="neural",
            VoiceId=voice,
            OutputFormat="mp3",
        )["AudioStream"].read()
        s3.put_object(
            Bucket=bucket, Key=key, Body=audio, ContentType="audio/mpeg",
            Metadata={"text-sha256": digest},
        )

    return s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=URL_SECONDS
    )


if __name__ == "__main__":
    lang_arg = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--lang=")), "en")
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    print(speak(positional[0], positional[1], lang=lang_arg))
