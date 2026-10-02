"""AWS smoke test: one call each to Bedrock, Polly, Textract and S3.

  python infra/smoke_test.py

Prints PASS/FAIL per service and the region used. Needs AWS credentials (SETUP.md) and
env vars AWS_REGION (default us-east-1) and BEDROCK_MODEL_ID. Exit code 1 if any FAIL.
The only thing sent anywhere is a one-word prompt and a generated blank image.
"""
import os
import struct
import sys
import zlib

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")


def tiny_png(w=64, h=64):
    """A valid all-white PNG built by hand, so no imaging library is needed."""
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    rows = b"".join(b"\x00" + b"\xff" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def bedrock():
    model = os.environ.get("BEDROCK_MODEL_ID")
    if not model:
        raise RuntimeError("BEDROCK_MODEL_ID is not set (see SETUP.md)")
    r = boto3.client("bedrock-runtime", region_name=REGION).converse(
        modelId=model, messages=[{"role": "user", "content": [{"text": "Reply with the word OK."}]}],
        inferenceConfig={"maxTokens": 10})
    return f"model replied {r['output']['message']['content'][0]['text'].strip()!r}"


def polly():
    r = boto3.client("polly", region_name=REGION).synthesize_speech(
        Text="Hello.", Engine="neural", VoiceId="Joanna", OutputFormat="mp3")
    return f"{len(r['AudioStream'].read())} bytes of audio"


def textract():
    r = boto3.client("textract", region_name=REGION).analyze_document(
        Document={"Bytes": tiny_png()}, FeatureTypes=["TABLES", "FORMS"])
    return f"{len(r['Blocks'])} blocks returned"


def s3():
    r = boto3.client("s3", region_name=REGION).list_buckets()
    return f"{len(r['Buckets'])} buckets visible"


def main():
    print(f"Region: {REGION}")
    failed = False
    for name, fn in (("Bedrock", bedrock), ("Polly", polly), ("Textract", textract), ("S3", s3)):
        try:
            print(f"PASS  {name}: {fn()}")
        except Exception as e:
            failed = True
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
