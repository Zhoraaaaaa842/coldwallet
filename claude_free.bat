@echo off
setlocal
set "ANTHROPIC_AUTH_TOKEN=sk-b21a3fd846037ac7-06cedd-1c61c094"

set "ANTHROPIC_BASE_URL=http://localhost:20128/v1"

set "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1"

set "ANTHROPIC_MODEL=kr/claude-sonnet-4.5"

echo Start Claude via omniroute
npx claude %
endlocal