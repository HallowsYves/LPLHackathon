"""Spanish translation of a validated English summary (tested on sample data).

translate_summary(text, lang, statement) -> {"text": str, "machine_translated": bool}

Only "es" is supported alongside "en". For "en" the input is returned unchanged.
For "es":
  1. Call Amazon Translate (en -> es).
  2. Re-run the number validator on the result.
  3. If any figure mismatches, fall back to the English text with machine_translated=False
     and log a warning — the caller should show a visible notice to the user.

Guardrails and "worth a call" tone are applied to the English source before translation,
not here.

Env: AWS_REGION (standard boto3 default if unset).
"""
import os

SUPPORTED = {"en", "es"}


def translate_summary(text: str, lang: str, statement: dict, translate_client=None) -> dict:
    """Return {"text": str, "machine_translated": bool}.

    machine_translated is True only when Amazon Translate was used AND the
    translated figures all validated correctly.  It is False for 'en' or when
    the translation had to fall back to English.
    """
    if lang not in SUPPORTED:
        raise ValueError(f"unsupported lang '{lang}'; supported: {sorted(SUPPORTED)}")

    if lang == "en":
        return {"text": text, "machine_translated": False}

    # Translate to Spanish.
    import boto3
    from backend.summary.validator import validate

    client = translate_client or boto3.client(
        "translate", region_name=os.environ.get("AWS_REGION")
    )
    response = client.translate_text(
        Text=text,
        SourceLanguageCode="en",
        TargetLanguageCode="es",
    )
    translated = response["TranslatedText"]

    # Re-validate figures in the translated text against the original statement.
    v = validate(translated, statement)
    if v["mismatches"]:
        print(
            f"[translate] {len(v['mismatches'])} figure mismatch(es) after translation; "
            f"falling back to English. Mismatches: {v['mismatches']}"
        )
        return {"text": text, "machine_translated": False}

    return {"text": translated, "machine_translated": True}
