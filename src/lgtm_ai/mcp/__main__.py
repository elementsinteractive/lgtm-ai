try:
    from fastmcp import FastMCP
except ImportError:
    raise SystemExit(
        "You are trying to run the lgtm-mcp CLI, but you have not installed the required dependencies. Install them with `pip install 'lgtm-ai[mcp]'"
    ) from None

from pathlib import Path
from typing import Annotated, Any

import httpx
from lgtm_ai.ai.agent import get_ai_model, get_reviewer_agent_with_settings, get_summarizing_agent_with_settings
from lgtm_ai.ai.schemas import AgentSettings, Review
from lgtm_ai.base.schemas import LocalRepository
from lgtm_ai.config.handler import CliOptions, ConfigHandler
from lgtm_ai.formatters.json import JsonFormatter
from lgtm_ai.review import CodeReviewer
from lgtm_ai.review.context import ContextRetriever
from pydantic import Field

mcp = FastMCP("LGTM-AI Code Reviewer Tool")
formatter = JsonFormatter()
httpx_client = httpx.Client(timeout=3)


class ReviewOutput(Review):
    pr_diff: Any = Field(exclude=True)
    model_config = {"from_attributes": True}


@mcp.tool(
    name="lgtm-review",
    title="LGTM-AI Code Review",
    description="Perform a code review using lgtm-ai for a local git repository. Use this when the user requests a thorough code review.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
)
def get_lgtm_review(
    repo_path: Annotated[str, Field("Path to the local git repository")],
    compare: Annotated[
        str,
        Field(
            description="What to compare. Defaults to 'HEAD', which will review uncommitted changes. To compare against another branch, pass the branch name (e.g., `main`)."
        ),
    ] = "HEAD",
    config_file_path: Annotated[
        str | None,
        Field(
            description="Optional path to a config file (lgtm.toml or pyproject.toml). If not provided, the tool will auto-detect lgtm.toml or pyproject.toml in the current working directory where the MCP server is running from (lgtm.toml takes precedence). Falls back to environment variables and defaults if no config files exist."
        ),
    ] = None,
) -> ReviewOutput:
    """Perform a code review for a local git repository using lgtm-ai."""
    repo_path_p = Path(repo_path)
    if not repo_path_p.is_dir() or not (repo_path_p / ".git").is_dir():
        raise ValueError(f"'{repo_path}' is not a valid local git repository path.")

    target = LocalRepository(repo_path=repo_path_p)
    config_file = config_file_path if config_file_path else None

    resolved_config = ConfigHandler(
        cli_args=CliOptions(compare=compare),
        config_file=config_file,
    ).resolve_config(target)

    agent_extra_settings = AgentSettings(retries=resolved_config.ai_retries)
    code_reviewer = CodeReviewer(
        reviewer_agent=get_reviewer_agent_with_settings(agent_extra_settings),
        summarizing_agent=get_summarizing_agent_with_settings(agent_extra_settings),
        model=get_ai_model(
            model_name=resolved_config.model,
            api_key=resolved_config.ai_api_key,
            model_url=resolved_config.model_url,
        ),
        context_retriever=ContextRetriever(
            git_client=None,
            issues_client=None,
            httpx_client=httpx_client,
        ),
        git_client=None,
        config=resolved_config,
    )
    review = code_reviewer.review(target=target)

    return ReviewOutput.model_validate(review)


def cli() -> None:
    """Entry point for the MCP tool."""
    mcp.run()


if __name__ == "__main__":
    cli()
