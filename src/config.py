"""Central settings, read from the environment with a gitignored .env file at
the repo root as fallback — keys live only on disk, never typed into a shell
command. See providers/ for how LLM_PROVIDER selects the active provider."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"


def _dotenv_values():
    if not ENV_PATH.exists():
        return {}
    values = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_DOTENV = _dotenv_values()


def get_env(key, default=None):
    import os
    return os.environ.get(key) or _DOTENV.get(key) or default


class Settings:
    def __init__(self):
        self.llm_provider = get_env("LLM_PROVIDER", "anthropic")

        self.anthropic_api_key = get_env("ANTHROPIC_API_KEY")
        self.anthropic_model = get_env("ANTHROPIC_MODEL", "claude-sonnet-5")

        # Covers OpenAI, Azure OpenAI, and any OpenAI-compatible endpoint.
        # For Azure, set OPENAI_BASE_URL to the resource endpoint and
        # OPENAI_API_VERSION; OPENAI_MODEL is then the deployment name.
        self.openai_api_key = get_env("OPENAI_API_KEY")
        self.openai_base_url = get_env("OPENAI_BASE_URL")
        self.openai_api_version = get_env("OPENAI_API_VERSION")
        self.openai_model = get_env("OPENAI_MODEL", "gpt-4o")

        self.database_url = get_env("DATABASE_URL")

        self.max_tool_calls = int(get_env("MAX_TOOL_CALLS", "8"))
        self.max_retries = int(get_env("MAX_RETRIES", "3"))


SETTINGS = Settings()
