#!/usr/bin/env bash
# Deploy Clear Statement: build + deploy the SAM stack, write the API URL into
# frontend/config.js, upload frontend/ to the site bucket, print the site URL.
# Needs AWS credentials (see SETUP.md) and the AWS SAM CLI. Sample data only.
#
# frontend/config.js is expected to hold lines like:
#   const API_BASE = "...";
#   const USE_MOCK = false;
# Only those two lines are changed; the file is created if it does not exist.
set -euo pipefail

cd "$(dirname "$0")/.."
export AWS_REGION="${AWS_REGION:-us-east-1}"
STACK="${STACK_NAME:-clear-statement}"

sam build --template-file infra/template.yaml --build-dir infra/.aws-sam/build
sam deploy --template-file infra/.aws-sam/build/template.yaml --stack-name "$STACK" \
  --region "$AWS_REGION" --capabilities CAPABILITY_IAM --resolve-s3 \
  --no-confirm-changeset --no-fail-on-empty-changeset

out() { aws cloudformation describe-stacks --stack-name "$STACK" --region "$AWS_REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API_URL="$(out ApiUrl)"; SITE_BUCKET="$(out SiteBucketName)"; SITE_URL="$(out SiteUrl)"

mkdir -p frontend
CFG=frontend/config.js
[ -f "$CFG" ] || printf 'const API_BASE = "";\nconst USE_MOCK = false;\n' > "$CFG"
sed -i.bak -E "s|^(const API_BASE = ).*|\1\"$API_URL\";|; s|^(const USE_MOCK = ).*|\1false;|" "$CFG"
rm -f "$CFG.bak"

[ -f frontend/index.html ] || echo "warning: frontend/index.html not found; the site will be empty" >&2
aws s3 sync frontend/ "s3://$SITE_BUCKET/" --delete --region "$AWS_REGION"

echo
echo "API:  $API_URL"
echo "Site: $SITE_URL"
