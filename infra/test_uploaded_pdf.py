"""Check real uploaded contents through AWS; writes a synthetic decision."""
import json
from pathlib import Path
import sys
import urllib.request
import urllib.error

base = 'https://kdr26wla75.execute-api.us-east-1.amazonaws.com/prod'
root = Path(__file__).resolve().parents[1]
pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'data/pdfs/jonathan.pdf'
boundary = 'clear-statement-upload-check'
body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="different-name.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
        + pdf.read_bytes() + f'\r\n--{boundary}--\r\n'.encode())

def call(path, data=None, content_type='application/json'):
    request = urllib.request.Request(base + path, data=data, headers={'Content-Type': content_type})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode()) from error

result = call('/process', body, f'multipart/form-data; boundary={boundary}')
sid = result['statement_id']
assert sid.startswith('upload-'), result
print('PASS unique uploaded statement ID', sid, flush=True)
statement = call('/statement/' + sid)
assert statement['client']['name'] == 'Jonathan Kim', statement['client']
assert statement['accounts'][0]['end_value'] == 420123.45, statement['accounts']
print('PASS extracted Jonathan Kim and changed IRA figure', flush=True)
summary = call('/summary/' + sid)
assert not summary['validation']['mismatches'], summary['validation']
assert '420123.45' in summary['text'].replace(',', ''), summary['text']
assert summary['audio_url'], summary
with urllib.request.urlopen(summary['audio_url'], timeout=60) as audio:
    assert audio.status == 200 and len(audio.read()) > 1000
print('PASS validated summary and Polly audio', flush=True)
flags = call('/flags?statement_id=' + sid)
assert len(flags) == 3, flags
wire = next(flag for flag in flags if flag['rule'] == 'large_wire_new_payee')
record = call('/flags/' + wire['id'] + '/decision', json.dumps({'action': 'escalate', 'note': 'Tested on sample data: confirm Jonathan wire.'}).encode())
audit = call('/audit/' + sid)
assert any(item['id'] == record['id'] for item in audit), audit
print('PASS 3 flags, escalation, and persistent audit (tested on sample data)', flush=True)
