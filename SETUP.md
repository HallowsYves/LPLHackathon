# SETUP: get working in 10 minutes

Works the same whether you use Claude Code or Codex. Do this once, then pick a task from `TASKS.md`.

## 1. Get AWS credentials

1. Open the hackathon event page and click **Get AWS CLI credentials**.
2. Copy the five `export` lines it shows.
3. Paste them into your terminal. They apply to that terminal only and expire, so repeat this when you see `ExpiredToken`.

Never put these in a file, in the repo, or in a chat. `.env` is already in `.gitignore`, but don't rely on that.

Check it works:

```bash
aws sts get-caller-identity
```

You should see account `732214162180` and the role `WSParticipantRole`.

## 2. Install tools

```bash
brew install aws-sam-cli          # needed for infra tasks P and Q only
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Set the two config values

```bash
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Use this model. The account has a model allowlist, and others (for example Sonnet 5.5) are denied. Haiku 4.5 is tested and works.

## 4. Confirm everything responds

```bash
python infra/smoke_test.py        # task A; checks Bedrock, Polly, Textract, S3
```

## 5. Start a task

1. `git pull`, then open `TASKS.md`.
2. Pick a task whose `Needs:` is `none` or already merged, and tell the team which one so nobody doubles up.
3. Paste the task's prompt into Claude Code or Codex and work only in its `Owns:` folder.
4. Run its `Done when:` command, tick the box in `TASKS.md`, commit, and push.

## Known facts about this account

- Region: `us-east-1`. The event ends about Oct 5, after the Oct 3 9:00 AM PT deadline.
- Working: Bedrock (Haiku 4.5 confirmed), Polly (neural voices), Textract, S3.
- No Guardrails exist yet; task K creates one.
- Do not claim real-world results. Everything is synthetic and must be labeled "tested on sample data".
