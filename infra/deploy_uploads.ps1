param(
    [string]$StackName = 'clear-statement',
    [string]$Region = 'us-east-1',
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    aws sts get-caller-identity --query Account --output text
    if ($LASTEXITCODE -ne 0) { throw 'Configure workshop AWS credentials first.' }
    $stackJson = aws cloudformation describe-stacks --stack-name $StackName --region $Region --output json
    if ($LASTEXITCODE -ne 0) { throw 'Could not read the existing stack.' }
    $stack = ($stackJson | ConvertFrom-Json).Stacks[0]
    $audioBucket = ($stack.Outputs | Where-Object OutputKey -eq 'AudioBucketName').OutputValue
    if (-not $audioBucket) { throw 'Existing stack has no audio bucket for packaging.' }
    & $Python infra/package_lambda.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
    # AWS CLI's bundled Python can reject non-ASCII paths on Windows.
    $deployFolder = Join-Path ([System.IO.Path]::GetTempPath()) ('clear-statement-deploy-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $deployFolder | Out-Null
    Copy-Item -LiteralPath tmp/upload-deployment/template.yaml,tmp/upload-deployment/lambda.zip -Destination $deployFolder
    Set-Location -LiteralPath $deployFolder
    aws cloudformation package --template-file template.yaml --s3-bucket $audioBucket --output-template-file packaged.yaml --region $Region
    if ($LASTEXITCODE -ne 0) { throw 'Artifact upload failed.' }
    aws cloudformation deploy --template-file packaged.yaml --stack-name $StackName --region $Region --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --no-fail-on-empty-changeset
    if ($LASTEXITCODE -ne 0) { throw 'Stack deployment failed. Inspect CloudFormation events.' }
    Write-Output 'Backend deployed. Test an uploaded synthetic PDF from the local frontend.'
} finally {
    Pop-Location
}
