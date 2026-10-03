"""Extract the team's single-page synthetic statement layout with Textract.

Never substitute a fixture based on an uploaded filename. Unsupported layouts
fail visibly. Wire payee history is limited to earlier rows in this statement.
"""
import json
import os
import re
import uuid
from decimal import Decimal
from email.parser import BytesParser
from email.policy import default


class UploadError(ValueError):
    pass


def uploaded_pdf(event):
    import base64
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    content_type = headers.get('content-type', '')
    body = event.get('body') or ''
    raw = base64.b64decode(body) if event.get('isBase64Encoded') else body.encode('latin-1')
    if 'multipart/form-data' in content_type:
        message = BytesParser(policy=default).parsebytes(
            f'Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n'.encode() + raw)
        parts = [part for part in message.iter_parts() if part.get_param('name', header='content-disposition') == 'file']
        if len(parts) != 1:
            raise UploadError('Select one synthetic PDF to upload.')
        raw = parts[0].get_payload(decode=True)
    elif 'application/pdf' not in content_type:
        return None
    if not raw or not raw.startswith(b'%PDF-'):
        raise UploadError('The uploaded file is not a PDF.')
    if len(raw) > 4 * 1024 * 1024:
        raise UploadError('Use a single-page synthetic PDF smaller than 4 MB.')
    return raw


def amount(text):
    cleaned = re.sub(r'[\s$,]', '', text)
    if not re.fullmatch(r'-?\d+(?:\.\d{1,2})?', cleaned):
        raise UploadError(f'Could not read a statement amount: {text!r}.')
    return float(abs(Decimal(cleaned)))


def parse_statement(response):
    blocks = {block['Id']: block for block in response['Blocks']}
    lines = ' '.join(block.get('Text', '') for block in blocks.values() if block['BlockType'] == 'LINE')
    if 'SYNTHETIC SAMPLE' not in lines.upper():
        raise UploadError('Only labeled synthetic sample statements are supported.')
    client = re.search(r'Client:\s*(.*?)\s*\(age\s*(\d+)\)', lines, re.I)
    period = re.search(r'Statement period:\s*(\d{4}-Q[1-4])', lines, re.I)
    if not client or not period:
        raise UploadError('Use the sample brokerage layout with Client, age, and Statement period fields.')

    def children(block):
        return [blocks[key] for rel in block.get('Relationships', []) if rel['Type'] == 'CHILD' for key in rel['Ids']]

    tables = []
    for table in blocks.values():
        if table['BlockType'] != 'TABLE':
            continue
        rows = {}
        for cell in children(table):
            if cell['BlockType'] != 'CELL':
                continue
            words = children(cell)
            if any(word.get('Confidence', 100) < 85 for word in words
                   if word['BlockType'] == 'WORD' and re.search(r'[A-Za-z0-9]', word.get('Text', ''))):
                raise UploadError('Some table text was unclear. Please use a clearer synthetic PDF.')
            text = ' '.join(word.get('Text', '') for word in words if word['BlockType'] == 'WORD')
            rows.setdefault(cell['RowIndex'], {})[cell['ColumnIndex']] = text
        tables.append([[cells.get(column, '') for column in range(1, max(cells) + 1)]
                       for _, cells in sorted(rows.items())])
    accounts, fees, transactions = [], [], []
    prior = None
    seen_payees = set()
    for rows in tables:
        if not rows:
            continue
        header = ' '.join(rows[0]).lower()
        if 'acct' in header and 'start' in header and 'end' in header:
            for row in rows[1:]:
                if len(row) != 9:
                    raise UploadError('Could not read the account summary table.')
                if row[1].lower() == 'total':
                    continue
                accounts.append({'id': row[0], 'type': row[1], 'start_value': amount(row[2]), 'end_value': amount(row[8])})
        elif 'description' in header and 'account' in header and 'date' not in header:
            for row in rows[1:]:
                if len(row) != 3:
                    raise UploadError('Could not read the fees table.')
                if 'prior' in row[0].lower():
                    prior = amount(row[2])
                elif not row[0].lower().startswith('total'):
                    fees.append({'label': row[0], 'account': row[1], 'amount': amount(row[2])})
        elif 'date' in header and 'payee' in header:
            for row in rows[1:]:
                if len(row) != 6:
                    raise UploadError('Could not read the transactions table.')
                txn = {'date': row[0], 'id': row[1], 'account': row[2], 'type': row[3].lower(), 'amount': amount(row[5])}
                if row[4]:
                    txn['payee'] = row[4]
                    if txn['type'] == 'wire':
                        txn['payee_is_new'] = row[4] not in seen_payees
                    seen_payees.add(row[4])
                transactions.append(txn)
    if not accounts or not fees or prior is None or not transactions:
        raise UploadError('Required tables are missing. Use the single-page sample brokerage layout.')
    if len({a['id'] for a in accounts}) != len(accounts) or any(not a['id'] for a in accounts):
        raise UploadError('Account IDs did not pass validation.')
    from datetime import date
    year, quarter = period.group(1).split('-Q')
    ids = set()
    account_ids = {account['id'] for account in accounts}
    for txn in transactions:
        try:
            day = date.fromisoformat(txn['date'])
        except ValueError as error:
            raise UploadError('Could not read a transaction date.') from error
        if day.year != int(year) or (day.month - 1) // 3 + 1 != int(quarter) or txn['id'] in ids or txn['account'] not in account_ids:
            raise UploadError('Transaction dates, IDs, or accounts did not pass validation.')
        if txn['type'] not in {'wire', 'withdrawal', 'deposit', 'dividend'}:
            raise UploadError('Unsupported transaction type in the synthetic statement.')
        ids.add(txn['id'])
    return {'client': {'name': client.group(1), 'age': int(client.group(2))}, 'period': period.group(1),
            'accounts': accounts, 'fees': fees, 'transactions': transactions, 'prior_fee_total': prior}


def bucket():
    return os.environ.get('STATEMENT_BUCKET')


def load(statement_id):
    if not re.fullmatch(r'upload-[a-f0-9]{32}', statement_id):
        raise KeyError(statement_id)
    if bucket():
        import boto3
        from botocore.exceptions import ClientError
        try:
            obj = boto3.client('s3').get_object(Bucket=bucket(), Key=f'statements/{statement_id}.json')
        except ClientError as error:
            if error.response['Error']['Code'] in {'NoSuchKey', '404'}:
                raise KeyError(statement_id) from error
            raise
        statement = json.loads(obj['Body'].read())
        statement['original_url'] = boto3.client('s3').generate_presigned_url('get_object',
            Params={'Bucket': bucket(), 'Key': f'originals/{statement_id}.pdf'}, ExpiresIn=3600)
        statement['extraction_notice'] = 'Read from uploaded synthetic PDF with Textract. New payee history is limited to earlier rows in this statement.'
        return statement
    path = os.path.join(os.environ.get('LOCAL_STORE_DIR', '.local_store'), f'{statement_id}.json')
    try:
        with open(path, encoding='utf-8') as source:
            return json.load(source)
    except FileNotFoundError as error:
        raise KeyError(statement_id) from error


def extract(pdf):
    import boto3
    sid = 'upload-' + uuid.uuid4().hex
    s3 = boto3.client('s3') if bucket() else None
    key = f'originals/{sid}.pdf'
    if s3:
        s3.put_object(Bucket=bucket(), Key=key, Body=pdf, ContentType='application/pdf')
    document = {'S3Object': {'Bucket': bucket(), 'Name': key}} if s3 else {'Bytes': pdf}
    response = boto3.client('textract').analyze_document(Document=document, FeatureTypes=['TABLES', 'FORMS'])
    statement = parse_statement(response)
    payload = json.dumps(statement).encode()
    if s3:
        s3.put_object(Bucket=bucket(), Key=f'statements/{sid}.json', Body=payload, ContentType='application/json')
    else:
        folder = os.environ.get('LOCAL_STORE_DIR', '.local_store')
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f'{sid}.json'), 'wb') as target:
            target.write(payload)
    return sid, statement
