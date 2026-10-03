"""Upload integration tests; tested on sample data, no AWS calls."""
import base64
import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from backend.api import uploads, handler
from backend.common import store


def textract_response(statement):
    blocks = []
    def add(block):
        block['Id'] = str(len(blocks))
        blocks.append(block)
        return block['Id']
    add({'BlockType': 'LINE', 'Text': f"Client: {statement['client']['name']} (age {statement['client']['age']}) Statement period: {statement['period']} SYNTHETIC SAMPLE"})
    def table(rows):
        cells = []
        for r, row in enumerate(rows, 1):
            for c, value in enumerate(row, 1):
                word = add({'BlockType': 'WORD', 'Text': str(value), 'Confidence': 99})
                cells.append(add({'BlockType': 'CELL', 'RowIndex': r, 'ColumnIndex': c,
                                  'Relationships': [{'Type': 'CHILD', 'Ids': [word]}]}))
        add({'BlockType': 'TABLE', 'Relationships': [{'Type': 'CHILD', 'Ids': cells}]})
    table([['Acct', 'Type', 'Start value', 'Deposits', 'Dividends', 'Withdrawals & wires', 'Fees', 'Market change', 'End value']] +
          [[a['id'], a['type'], a['start_value'], 0, 0, 0, 0, 0, a['end_value']] for a in statement['accounts']])
    table([['Description', 'Account', 'Amount']] + [[f['label'], f.get('account', ''), f['amount']] for f in statement['fees']] +
          [['Total fees, prior period', '', statement['prior_fee_total']]])
    table([['Date', 'ID', 'Account', 'Type', 'Description / payee', 'Amount']] +
          [[t['date'], t['id'], t['account'], t['type'], t.get('payee', ''), t['amount']] for t in statement['transactions']])
    return {'Blocks': blocks}


class UploadTests(unittest.TestCase):
    def setUp(self):
        with open('data/ground_truth/problem.json') as source:
            self.statement = json.load(source)

    def test_changed_contents_are_extracted(self):
        self.statement['client']['name'] = 'Jonathan Kim'
        self.statement['accounts'][0]['end_value'] = 420123.45
        parsed = uploads.parse_statement(textract_response(self.statement))
        self.assertEqual(parsed['client']['name'], 'Jonathan Kim')
        self.assertEqual(parsed['accounts'][0]['end_value'], 420123.45)
        self.assertEqual(len(parsed['transactions']), len(self.statement['transactions']))

    def test_low_confidence_and_missing_tables_fail(self):
        response = textract_response(self.statement)
        next(b for b in response['Blocks'] if b['BlockType'] == 'WORD')['Confidence'] = 50
        with self.assertRaises(uploads.UploadError):
            uploads.parse_statement(response)
        with self.assertRaises(uploads.UploadError):
            uploads.parse_statement({'Blocks': response['Blocks'][:1]})

    def test_binary_multipart(self):
        pdf = b'%PDF-1.4\n\x00\xff\x80\nEOF'
        raw = b'--demo\r\nContent-Disposition: form-data; name="file"; filename="different.pdf"\r\nContent-Type: application/pdf\r\n\r\n' + pdf + b'\r\n--demo--\r\n'
        event = {'headers': {'Content-Type': 'multipart/form-data; boundary=demo'},
                 'isBase64Encoded': True, 'body': base64.b64encode(raw).decode()}
        self.assertEqual(uploads.uploaded_pdf(event), pdf)

    def test_uncertain_header_punctuation_does_not_block_numbers(self):
        response = textract_response(self.statement)
        # Use an unrelated punctuation word in a known table, preserving its headers.
        response['Blocks'].append({'Id': 'slash', 'BlockType': 'WORD', 'Text': '/', 'Confidence': 82})
        cell = next(b for b in response['Blocks'] if b['BlockType'] == 'CELL')
        cell['Relationships'][0]['Ids'].append('slash')
        self.assertEqual(uploads.parse_statement(response)['client']['name'], 'Margaret Hale')

    def test_unique_statement_flags_and_summary(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'STORE': 'local', 'LOCAL_STORE_DIR': directory, 'SUMMARY_MOCK': '1'}):
            sid = 'upload-' + 'a' * 32
            self.statement['client']['name'] = 'Jonathan Kim'
            with open(os.path.join(directory, sid + '.json'), 'w') as target:
                json.dump(self.statement, target)
            with patch.object(uploads, 'extract', return_value=(sid, self.statement)):
                status, result = handler.process({'headers': {'Content-Type': 'application/pdf'}, 'body': '%PDF-test'})
            self.assertEqual(status, 200)
            self.assertEqual(result['statement_id'], sid)
            self.assertEqual(len(store.list_flags(sid)), 3)
            self.assertTrue(all(f['id'].startswith(sid) for f in store.list_flags(sid)))
            self.assertEqual(handler._statement(sid)['client']['name'], 'Jonathan Kim')
            _, summary = handler.summary(sid)
            self.assertIn('Jonathan', summary['text'])
            self.assertEqual(summary['validation']['mismatches'], [])
            handler._summary_cache.pop(sid, None)


if __name__ == '__main__':
    unittest.main()
