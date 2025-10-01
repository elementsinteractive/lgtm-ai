import datetime
import logging
import os
import pathlib
import subprocess
from unittest import mock

import click
import gitlab
import httpx
from lgtm_ai.ai.agent import get_ai_model, get_reviewer_agent_with_settings, get_summarizing_agent_with_settings
from lgtm_ai.ai.schemas import Review, SupportedAIModels, SupportedAIModelsList
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.formatters.markdown import MarkDownFormatter
from lgtm_ai.git_client.gitlab import GitlabClient
from lgtm_ai.review import CodeReviewer
from lgtm_ai.review.context import ContextRetriever
from lgtm_ai.validators import TargetParser
from rich.logging import RichHandler

PRS_FOR_EVALUATION = {
    # This PR represents a trivial change.
    "PR-1-trivial": "https://gitlab.com/X/Y/-/merge_requests/1",
    # This PR represents a more complex change, with a focus on quality. There aren't many issues in it.
    "PR-2-quality": "https://gitlab.com/X/Y/-/merge_requests/2",
    # This PR is a correct change (more or less), but has some issues introduced on purpose. Some of these issues are:
    #    - tasks.py intentionally contains not only tasks, but public functions as well. This could benefit from a refactor.
    #    - In settings.py, two env variables are introduced, but with inconsistent naming (CELERY_TRIGGER_REBUILD_AT_HOUR, TRIGGER_REBUILD_AT_MINUTE).
    #    - In `tasks.py:get-content`, there is a useless assignment and the url could be `None`.
    #    - In `tasks.py:load_images`, the src file env variable is added directly instead of it being located elsewhere.
    #    - In `tasks.py:csv_contains_at_least_one_valid_record`, the csv reader has no `delimiter` set.
    #    - In `tasks.py:csv_contains_at_least_one_valid_record`, the `image` field is accessed in the dict reader without a default value.
    #    - Status code 200 is hardcoded in `tasks.py:get_content`.
    #    - Many test cases are missing.
    "PR-3-issues": "https://gitlab.com/X/Y/-/merge_requests/3",
}


# Set lgtm logging level to debug since this is done
# for evaluation purposes.
logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
logging.getLogger("lgtm").setLevel(logging.DEBUG)


@click.command()
@click.option(
    "--model",
    default="gpt-4o-mini",
    type=click.Choice(SupportedAIModelsList),
    help="The name of the model to use for the review",
)
@click.option("--git-api-key", required=True, help="The API key to the git service (GitLab, GitHub, etc.)")
@click.option("--ai-api-key", required=True, help="The API key to the AI model service (OpenAI, etc.)")
@click.option("--sample-size", default=3, help="The number of times a PR will be evaluated")
@click.option("--output-directory", default="ai_assessments", help="The directory to save the assessment results")
def main(model: SupportedAIModels, git_api_key: str, ai_api_key: str, sample_size: int, output_directory: str) -> None:
    branch = get_git_branch()
    click.echo(f"Current branch: {branch}")

    if branch == "main":
        click.echo("You are on the main branch. Please checkout a feature branch to run this script.")
        click.Abort()

    # Create dir with branch name
    output_directory = (pathlib.Path(output_directory) / f"{datetime.date.today().isoformat()}-{branch}").as_posix()
    click.echo(f"Creating output directory: {output_directory}")
    os.mkdir(output_directory)

    click.echo(f"Evaluating the quality of the review on PRs: {', '.join(PRS_FOR_EVALUATION)}")
    for pr_name, pr_url in PRS_FOR_EVALUATION.items():
        for i in range(sample_size):
            click.echo(f"Evaluating PR: {pr_name} - Sample {i + 1}")
            perform_review(
                output_dir=output_directory,
                pr_url=pr_url,
                pr_name=pr_name,
                sample=i + 1,
                model=model,
                git_api_key=git_api_key,
                ai_api_key=ai_api_key,
            )
            click.echo(f"PR: {pr_name} Sample {i + 1} completed.")
    click.echo(f"Evaluation completed. Results saved to the {output_directory}.")


def get_git_branch() -> str:
    return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()  # noqa: S603, S607


def perform_review(
    output_dir: str, pr_url: str, pr_name: str, sample: int, model: SupportedAIModels, git_api_key: str, ai_api_key: str
) -> None:
    url = TargetParser(allow_git_repo=True)(mock.Mock(), "pr_url", pr_url)
    git_client = GitlabClient(client=gitlab.Gitlab(private_token=git_api_key), formatter=MarkDownFormatter())
    code_reviewer = CodeReviewer(
        reviewer_agent=get_reviewer_agent_with_settings(),
        summarizing_agent=get_summarizing_agent_with_settings(),
        model=get_ai_model(model_name=model, api_key=ai_api_key),
        git_client=git_client,
        context_retriever=ContextRetriever(
            git_client=git_client, issues_client=git_client, httpx_client=httpx.Client(timeout=3)
        ),
        config=ResolvedConfig(
            ai_api_key=ai_api_key,
            git_api_key=git_api_key,
            model=model,
            technologies=("Python", "Django", "FastAPI"),
        ),
    )
    review = code_reviewer.review(target=url)
    write_review_to_dir(model, output_dir, pr_name, sample, review)


def write_review_to_dir(
    model: SupportedAIModels, output_directory: str, pr_name: str, sample: int, review: Review
) -> None:
    with open(f"{output_directory}/review-pr-{pr_name}-{sample}.md", "w") as f:
        f.write(review_to_md(model, review, pr_name, sample))


def review_to_md(model: SupportedAIModels, review: Review, pr_name: str, sample: int) -> str:
    formatter = MarkDownFormatter()
    lines = [
        f"# Review for PR: {pr_name}",
        f"> Sample {sample}",
        f"> Using model: {model}",
        formatter.format_review_summary_section(review, review.review_response.comments),
    ]
    return "\n\n".join(lines)


if __name__ == "__main__":
    main()
