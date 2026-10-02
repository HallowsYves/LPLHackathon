# Clear Statement: Architecture and Build Plan

> LPL Financial University Hackathon 2026, theme: *Startup from the Future*
> Source of truth for the idea: `Clear_Statement_Project_Explainer.pdf`
> Submission deadline: **Saturday Oct 3, 9:00 AM PT / 12:00 PM ET**

## 1. One-line pitch

Clear Statement turns a dense account statement into a plain-language, read-aloud summary for older clients, and flags possible financial exploitation so a human advisor can act. The tool never acts on its own.

## 2. Scope for the weekend

One narrow, working slice: a **synthetic** statement goes in, and the demo shows:

- Side-by-side view of the original statement and the plain-language version
- A read-aloud button
- Three flags: large wire to a new payee, rapid repeated withdrawals, sudden fee change
- An advisor review screen with approve / escalate / dismiss and a saved audit record

**Out of scope:** real client data, live LPL systems, any automatic hold on an account. All demo data is synthetic, and any reported result must be labeled "tested on sample data".

## 3. Architecture

```
 Synthetic statement PDF
        |
        v
 [S3: originals] --> Lambda: extract --> Textract --> parser --> statement.json
                                                                   |
                         +-----------------------------------------+
                         v                                         v
              Lambda: summarize                         Lambda: flag engine
              Bedrock (+ Guardrails)                    3 plain-Python rules
              + number validator                                   |
                         |                                         v
                         v                              DynamoDB: flags
              Polly -> mp3 in S3                                   |
                         |                                         v
                         +----------> API Gateway <---- Lambda: decisions
                                            |            (approve / escalate / dismiss
                                            v             -> DynamoDB audit log)
                                  Web app (static, S3 + CloudFront or Amplify)
                                  |- Client view: original | plain version | read-aloud
                                  '- Advisor view: flags -> decide -> audit trail
```

### AWS services

| Step | Service | Why this one |
|---|---|---|
| Read the statement | Amazon Textract | Statements are tables; Textract extracts tables and forms |
| Write the explanation | Amazon Bedrock + Guardrails | Wording only; Guardrails block risky phrasing ("fraud", advice) |
| Read aloud | Amazon Polly | Accessibility for older clients |
| Orchestrate | AWS Lambda, API Gateway | Serverless, cost-aware |
| Store | Amazon S3, DynamoDB | Originals, flags, decisions, audit trail |
| Alerts (stretch) | Amazon SES | Email the advisor; sandbox needs verified addresses |

**Deliberately cut for the weekend:** Step Functions (one orchestrator Lambda is enough; mention Step Functions as the production path in the pitch) and SES (stretch only; the UI shows "alert sent" regardless).

## 4. Design principles (these are the pitch)

1. **Numbers come from fixed extraction; AI only writes wording.** A validator checks every dollar figure in the summary against `statement.json` and regenerates on a mismatch.
2. **Flags are simple and explainable.** Rules are plain Python; every flag carries a plain-English reason.
3. **Flag, not verdict.** Language is "worth a call", never "fraud".
4. **A human decides everything.** Temporary holds are a firm's choice under FINRA Rule 2165, not something the tool does.
5. **Every flag, decision, and note is recorded** so the firm can show how it handled the situation.

## 5. Shared contract (agree on this in the first 20 minutes)

### `statement.json`

```json
{
  "client": {"name": "Margaret Hale", "age": 78},
  "period": "2026-Q3",
  "accounts": [
    {"id": "A1", "type": "IRA", "start_value": 412300.12, "end_value": 405880.40}
  ],
  "fees": [{"label": "Advisory fee", "amount": 1031.50}],
  "transactions": [
    {"id": "t1", "date": "2026-09-12", "type": "wire",
     "payee": "Greenfield Holdings LLC", "amount": 48000, "payee_is_new": true}
  ],
  "prior_fee_total": 640.00
}
```

### Flag

```json
{
  "id": "f1",
  "rule": "large_wire_new_payee",
  "txn_ids": ["t1"],
  "reason": "A $48,000 wire went to a payee not seen before. Worth a call.",
  "status": "open"
}
```

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/process` | Upload and process a statement |
| GET | `/statement/{id}` | Return `statement.json` |
| GET | `/summary/{id}` | Plain-language summary + audio URL |
| GET | `/flags` | List flags |
| POST | `/flags/{id}/decision` | `{action: approve\|escalate\|dismiss, note}` |
| GET | `/audit/{id}` | Audit trail |

## 6. Work split (4 people)

### Person 1: Data and extraction

- Script to generate 2 to 3 synthetic statement PDFs (reportlab or a Word template exported to PDF): one normal, one with all three planted problems.
- S3 upload, then a Lambda that calls Textract (`AnalyzeDocument`, TABLES + FORMS) and parses the result into `statement.json`.
- **Safety net:** keep the ground-truth JSON that generated each PDF; fall back to it if Textract parsing is messy.
- Deliver the first working `statement.json` to the team within 1 to 2 hours. Until then, others use a hand-written mock.

### Person 2: Flag engine and advisor backend

- Three rules as plain Python functions with thresholds as constants:
  - Large wire to a new payee
  - 3+ withdrawals within 7 days
  - Fee increase of more than X% versus prior period
- Every flag gets a plain-English `reason`.
- DynamoDB tables `flags` and `audit` (flag, who decided, action, note, timestamp).
- Lambda + API Gateway routes for flags, decisions, audit.
- Stretch: SES email to the advisor on a new flag.

### Person 3: AI summary and read-aloud

- Bedrock prompt that receives only `statement.json` and returns a short, large-print-friendly summary: account value, what changed, fees paid, and 2 to 3 questions to ask the advisor.
- **Number validator:** extract every dollar figure from the output and confirm it exists in `statement.json`; regenerate on mismatch. Make this visible in the demo.
- Bedrock Guardrail blocking "fraud" language and anything resembling investment advice.
- Polly Lambda: summary text in, mp3 to S3, presigned URL out.
- **Request Bedrock model access in the AWS console immediately.** It is the most common blocker.

### Person 4: Frontend, integration, demo, and deck

- Static web app (React or plain HTML + JS) hosted on S3 + CloudFront or Amplify.
  - **Client view:** original statement left, plain version right in large type, read-aloud button, high-contrast toggle.
  - **Advisor view:** flag list with reasons and highlighted transactions, approve / escalate / dismiss with a note, audit trail panel.
- Owns AWS account setup, IAM, CORS, and deploying Lambdas as they come online.
- Owns the deck (LPL template), the recorded backup demo video, and the code ZIP.

## 7. Timeline

| Checkpoint | Goal |
|---|---|
| First hour | AWS access working, contract agreed, Bedrock access requested, mock JSON shared |
| Hours 2 to 5 | Each person's piece works alone against mock data |
| Hours 5 to 8 | End to end: PDF upload, summary + flags, advisor decision, audit |
| Evening | Feature freeze. Polish UI, run the demo script 3 times, record backup video |
| Morning | Final deck, code ZIP, Project Submission Form, upload to Box before 9:00 AM PT (leave a 1-hour buffer) |

## 8. Demo script (5 minutes)

1. **30s:** the problem (hard-to-read statements plus senior exploitation; the 2023 $3M FINRA fine against LPL).
2. Upload the statement; show the side-by-side; press read-aloud.
3. Switch to the advisor view; show the three flags; open the wire flag and **Escalate** with a note.
4. Show the audit trail.
5. Architecture slide, then the "why LPL should acquire this" close.

## 9. Judging alignment

All projects are judged on **Best Use of AWS** automatically; the team picks **2 of 4** main categories (form arrives 12:00 PM PT Friday).

| Category | Our angle |
|---|---|
| Startup We'd Buy Tomorrow | Built-in distribution (every client gets statements), hard-to-copy audit-trail moat |
| Biggest Business Impact | Lower exploitation losses and penalties; client trust and retention |
| Best Customer Experience | Large print, read-aloud, side-by-side original |
| Best Technical Execution | Grounded numbers + validator, explainable rules |
| Best Use of AWS (auto) | Name why each service was chosen; secure, cost-aware, live demo |

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| AI states a wrong number | Fixed extraction; AI writes wording only; validator; original always shown beside summary |
| Too much to build in one weekend | Three rules, one synthetic statement |
| Tool seems to accuse someone of fraud | Flags say "worth a call"; human always decides |
| Judges ask how this differs from LPL's existing tools | Ours is client-facing and tied to exploitation review and record keeping |
| Fee transparency is sensitive | Frame as client trust; do not single out fees or cash sweep unprompted |
| Claims we cannot back up | Say it "helps people spot and act faster", not "prevents fraud" |
| Textract parsing quirks | Ground-truth JSON fallback |
| Bedrock access delays | Request model access in hour one |
| CORS / deployment surprises | Test the deployed path early, not at the end |

## 11. Open questions (for refinement)

- Is the client-facing view really how LPL would want to deliver this, or is the advisor the real buyer?
- Who is the paying customer: LPL, the advisors, or the 1,100 institution partners?
- How does this differ from tools LPL already has, and is that difference defensible?
- Are three rules enough to look credible, and how do we avoid false-positive overload for advisors?
- Which two judging categories do we actually want to win?
- What is the single most impressive moment in the live demo?

## 12. Key terms

| Term | Plain meaning |
|---|---|
| FINRA Rule 4512 | Firms must make reasonable efforts to get a trusted contact person for an account |
| FINRA Rule 2165 | Lets firms place a temporary hold on suspected exploitation; permitted, not required |
| Trusted contact | Person the client names whom the firm can call if something seems wrong |
| Temporary hold | Short pause on a withdrawal or trade while a firm checks a suspicious request |
| Audit trail | Saved record of what happened and who decided |
| Human in the loop | A person reviews and approves before anything happens |

## 13. Sources

- LPL Financial, "A Guide to Your Statements"
- FINRA, *The Essential Senior Investor Protection Tools: Rules 2165 and 4512*
- InvestmentNews, "Finra fines LPL $3M for failing to detect wire transfers that harmed clients"
- MDF Law, "LPL Financial Fined $3 Million: E-Signature Allegations"
- Fredrikson, "FINRA enacts new rules addressing financial exploitation of seniors"
- Goodwin, "FINRA to permit temporary transaction holds"