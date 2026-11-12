# Netskope AI Guardrails — GitHub MCP CallToolRequest POC

Python proof of concept connecting to GitHub's hosted MCP endpoint. It initializes a real MCP session, discovers tools, and executes a **read-only** `search_repositories` tool call. Use the request to validate Netskope traffic steering, TLS inspection, and AI Guardrails policy handling of `CallToolRequest`.

## Prerequisites
- Python 3.13 (original POC environment)
- Your **own**, least-privilege GitHub personal token authorized for the hosted MCP endpoint
- Network access to `https://api.githubcopilot.com/mcp/`
- Netskope client/policies configured as needed
- An approved Netskope CA PEM only if Python does not already trust the TLS inspection CA

## Installation (per teammate)

```bash
git clone https://github.com/WhiteHatHero/Agentic-Broker-Test.git
```
```bash
cd Agentic-Broker-Test
python3.13 -m venv .venv
source .venv/bin/activate   # PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
```

Edit `.env`: supply your **personal** `GITHUB_TOKEN`; set `REPO_OWNER` and `REPO_NAME` to a repository your account can read; set `NETSKOPE_CA_PEM` (get this from Keychain on Mac or certlm.msc for Windows) to your locally approved CA certificate path. Never commit tokens, `.env`, or certificates.

## Run

```bash
python mcp_guardrails_test.py
```

The test prints protocol/session information, available tools, the tool request and response, and duration. Failures return a non-zero exit code.

## Netskope verification

1. Confirm traffic to the hosted GitHub MCP endpoint is steered.
2. Confirm TLS inspection when required by policy.
3. Correlate the test timestamp with MCP events and `CallToolRequest` in Netskope logs.
4. Confirm the expected policy match and enforcement action (allow, alert, block).
5. A successful HTTP or MCP response **alone does not prove** that Netskope inspected or enforced a policy.

## Safety and troubleshooting

- The test uses `X-MCP-Toolsets: repos` and `X-MCP-Readonly: true` and requests only a repository search.
- Use a separate least-privilege personal token for each tester.
- If you supply a Netskope CA PEM, the original test relaxes Python 3.13's X.509 strict conformance flag for compatibility. CA chain and hostname verification remain on. Only use this exception if organizationally approved.
- Authentication and hosted MCP tool availability may change; check GitHub's current documentation when debugging.
- Do not publish tokens, private certificates, virtual environments, or sensitive test logs.
