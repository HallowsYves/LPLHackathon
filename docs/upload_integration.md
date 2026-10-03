# Synthetic PDF upload integration

The frontend still calls the six existing endpoints. Multipart PDF uploads now
go to a private S3 bucket, then Textract TABLES + FORMS, then a deterministic
parser. Each upload has a unique statement ID. Parsed JSON is stored in S3 so
later Lambda invocations can read it. Flags use IDs scoped to the uploaded
statement; summaries, Polly audio, advisor decisions, and audit records follow
that ID. Original PDFs are accessible through an expiring S3 URL.

Supported input: single-page PDFs under 4 MB using the layout produced by
`data/make_pdfs.py`, labeled SYNTHETIC SAMPLE. Other layouts and uncertain table
text produce a visible error. This is not a general brokerage-statement parser.
New wire payees mean not present in earlier rows of the uploaded statement;
no prior-account-history source exists. The UI states that limitation.
Uploads never silently substitute ground-truth data based on their filename.
The Load sample button deliberately retains the predefined demo path.

Run local checks:

```powershell
python -m unittest backend.api.test_uploads backend.api.test_decisions backend.flags.test_rules backend.summary.test_validator
```

Deploy from Windows after configuring workshop credentials:

```powershell
./infra/deploy_uploads.ps1
```

This updates the existing clear-statement stack, adds private statement storage,
grants its Lambda access, and enables binary PDF/multipart handling at API Gateway.
It packages only backend Python and ground-truth JSON. No SAM installation is needed.
It does not publish the local frontend; refresh the locally served frontend to test.

Upload `data/pdfs/jonathan.pdf` using any filename. Expect Jonathan Kim, IRA ending
value $420,123.45, total ending value $493,477.48, and three flags. Play the summary,
then escalate the wire with a note. Verify the audit entry immediately and after
reload. Repeat with another filename: IDs should differ while figures stay the same.
All results are tested on sample data.

Deployment verification: AWS stack update succeeded. Real Textract extraction
read Jonathan Kim and the changed IRA ending value from a PDF uploaded as
different-name.pdf. Bedrock validation reported zero mismatches, Polly audio
returned successfully and played in the browser, and three flags plus a saved
escalation and audit were verified. Browser reload retained the statement and audit.
The hosted S3 frontend was updated and its Jonathan advisor view was verified.
26 local unit tests passed. AWS validate-template accepted the deployment template;
separate cfn-lint and cfn-guard checks were unavailable and were not run.
