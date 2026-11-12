"""Read-only GitHub hosted MCP test for Netskope AI Guardrails."""
import asyncio
import os
import ssl
import sys
import time
import traceback
from pathlib import Path

import certifi
import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
MCP_URL = os.getenv("MCP_URL", "https://api.githubcopilot.com/mcp/")
REPO_OWNER = os.getenv("REPO_OWNER", "WhiteHatHero")
REPO_NAME = os.getenv("REPO_NAME", "Agentic-Broker-Test")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
NETSKOPE_CA_PEM = os.getenv("NETSKOPE_CA_PEM", "")


def build_ssl_context():
    """Trust public CAs and optionally an approved Netskope TLS inspection CA."""
    print("\n[TLS] Configuring certificate trust...")
    context = ssl.create_default_context(cafile=certifi.where())
    if NETSKOPE_CA_PEM:
        ca_path = Path(NETSKOPE_CA_PEM).expanduser()
        if not ca_path.is_file():
            raise FileNotFoundError(f"Netskope CA certificate not found: {ca_path}")
        context.load_verify_locations(cafile=str(ca_path))
        print(f"[TLS] Netskope CA loaded: {ca_path}")
        # The original controlled POC permits noncritical CA basic constraints
        # with Python 3.13; chain and hostname verification remain enabled.
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
        print("[TLS] X509 strict mode disabled for Netskope CA compatibility")
    else:
        print("[TLS] Using standard public CA trust")
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    print("[TLS] Certificate and hostname verification ENABLED")
    return context


async def run_mcp_test():
    started = time.monotonic()
    print("=" * 65)
    print("NETSKOPE MCP GUARDRAILS - GITHUB HOSTED MCP TEST")
    print("=" * 65)
    try:
        print("\n[1] Checking environment...")
        print(f"[PYTHON] {sys.executable}")
        print(f"[SERVER] {MCP_URL}")
        if not GITHUB_TOKEN or GITHUB_TOKEN == "YOUR_PERSONAL_GITHUB_TOKEN":
            raise RuntimeError("Set your own GITHUB_TOKEN in .env")
        print("[AUTH] GitHub personal token detected")

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-MCP-Toolsets": "repos",
            "X-MCP-Readonly": "true",
        }
        timeout = httpx.Timeout(30.0, read=120.0)
        async with httpx.AsyncClient(
            headers=headers, timeout=timeout, verify=build_ssl_context()
        ) as http_client:
            print("\n[2] Connecting to GitHub hosted MCP...")
            async with streamable_http_client(MCP_URL, http_client=http_client) as (
                read_stream, write_stream, get_session_id
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    initialization = await session.initialize()
                    print("[SUCCESS] MCP session initialized")
                    print("[SERVER]", initialization.serverInfo.name)
                    print("[PROTOCOL]", initialization.protocolVersion)
                    print("[SESSION]", get_session_id() or "No session ID issued")

                    print("\n[3] Discovering MCP tools...")
                    tools_response = await session.list_tools()
                    tool_names = {tool.name for tool in tools_response.tools}
                    print(f"[SUCCESS] {len(tool_names)} tools found")
                    for tool in tools_response.tools:
                        print("  -", tool.name)

                    print("\n[4] Executing read-only GitHub MCP tool...")
                    target_tool = "search_repositories"
                    if target_tool not in tool_names:
                        raise RuntimeError(
                            f"{target_tool} not available; check toolsets and permissions"
                        )
                    arguments = {
                        "query": f"{REPO_NAME} in:name user:{REPO_OWNER}",
                        "perPage": 1,
                        "minimal_output": True,
                    }
                    print(f"[TOOL] {target_tool}")
                    print(f"[ARGUMENTS] {arguments}")
                    tool_started = time.monotonic()
                    result = await session.call_tool(target_tool, arguments=arguments)
                    print(f"[TOOL DURATION] {time.monotonic() - tool_started:.2f}s")
                    if result.isError:
                        for item in result.content:
                            if hasattr(item, "text"):
                                print(item.text[:3000])
                        raise RuntimeError("MCP tool execution failed or was denied")
                    print("[SUCCESS] MCP tool call completed")

                    print("\n[5] GitHub MCP response:")
                    for item in result.content:
                        if hasattr(item, "text"):
                            print(item.text[:3000])
                    print("\n[RESULT] REAL MCP TOOL CALL SUCCESSFUL")
                    print("\n[NETSKOPE VERIFICATION]")
                    print("1. Verify traffic steering in Netskope.")
                    print("2. Verify TLS inspection is active.")
                    print("3. Check MCP activity in Netskope logs.")
                    print("4. Check whether the intended policy matched.")
                    print("5. Confirm whether CallToolRequest was allowed.")
        return True
    except Exception as error:
        print("\n[RESULT] TEST FAILED")
        print(f"[ERROR TYPE] {type(error).__name__}")
        print(f"[ERROR MESSAGE] {error}")
        traceback.print_exc()
        if isinstance(error, BaseExceptionGroup):
            def show_errors(group):
                for sub_error in group.exceptions:
                    if isinstance(sub_error, BaseExceptionGroup):
                        show_errors(sub_error)
                    else:
                        print(f"[CAUSE] {type(sub_error).__name__}: {sub_error}")
            print("\n[UNDERLYING ERRORS]")
            show_errors(error)
        print("\n[DIAGNOSTIC] Review TLS trust, MCP connectivity, GitHub auth and Netskope logs.")
        return False
    finally:
        print(f"\n[DURATION] {time.monotonic() - started:.2f} seconds")
        print("=" * 65)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run_mcp_test()) else 1)
