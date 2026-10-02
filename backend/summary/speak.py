"""Read-aloud: summary text in, presigned mp3 URL out (tested on sample data).

speak(statement_id, text) -> presigned URL (valid 1 hour)

Polly neural voice at a slower rate (SSML), mp3 stored at
s3://$AUDIO_BUCKET/audio/<statement_id>.mp3 with a hash of the text in object
metadata; if the stored hash matches, Polly is skipped. Env: AWS_REGION, AUDIO_BUCKET.

Usage: python -m backend.summary.speak problem "Some text to read"
"""
import hashlib
import os
import sys
from xml.sax.saxutils import escape

VOICE = "Joanna"
RATE = "slow"
URL_SECONDS = 3600


def _ssml(text):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    body = "<break time=\"500ms\"/>".join(escape(p) for p in paragraphs)
    return f'<speak><prosody rate="{RATE}">{body}</prosody></speak>'


def speak(statement_id, text, s3=None, polly=None):
    import boto3
    from botocore.exceptions import ClientError
    region = os.environ.get("AWS_REGION")
    s3 = s3 or boto3.client("s3", region_name=region)
    bucket = os.environ["AUDIO_BUCKET"]
    key = f"audio/{statement_id}.mp3"
    digest = hashlib.sha256(f"{VOICE}|{RATE}|{text}".encode()).hexdigest()
    try:
        cached = s3.head_object(Bucket=bucket, Key=key)["Metadata"].get("text-sha256") == digest
    except ClientError:
        cached = False
    if not cached:
        polly = polly or boto3.client("polly", region_name=region)
        audio = polly.synthesize_speech(Text=_ssml(text), TextType="ssml", Engine="neural",
                                        VoiceId=VOICE, OutputFormat="mp3")["AudioStream"].read()
        s3.put_object(Bucket=bucket, Key=key, Body=audio, ContentType="audio/mpeg",
                      Metadata={"text-sha256": digest})
    return s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key},
                                     ExpiresIn=URL_SECONDS)


if __name__ == "__main__":
    print(speak(sys.argv[1], sys.argv[2]))
