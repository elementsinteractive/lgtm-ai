## v0.7.2 (2025-06-27)

### Fix

- raise LGTMException in case of bad git diff parsing (#64)

## v0.7.1 (2025-06-23)

### Fix

- ensure that model name in summary is the **resolved** name without wildcards (#59)

### Technical

- show version of lgtm-ai in verbose mode (#60)
- update all dependencies (#58)

## v0.7.0 (2025-06-12)

### Feat

- **#54**: add support for gemini model wildcards (#55)

## v0.6.0 (2025-06-12)

### Feat

- **#52**: add support for new gemini-pro-06-05 (#53)

### Technical

- bump ruff from 0.11.12 to 0.11.13 in the patch-updates group (#50)
- bump pytest from 8.3.5 to 8.4.0 in the minor-updates group (#51)

## v0.5.2 (2025-06-06)

### Fix

- change correctness emoji (#49)

## v0.5.1 (2025-06-03)

### Fix

- Gemini broke pydantic-ai integration, this is a workaround (#47)

### Technical

- add diagrams for lgtm (#46)

## v0.5.0 (2025-06-02)

### Feat

- Add additional context for the LLM

### Refactor

- additional context class and reuse `get_file_contents` everywhere in git clients

### Docs

- add additional context docs

### Tests

- add tests for additional context functionality

## v0.4.1 (2025-06-02)

### Fix

- **#41**: handle empty PR titles and descriptions for GitHub
- **#28**: harmonize github and gitlab implementations for getting context

### Refactor

- small refactor of parse url validator

### CI

- simplify lgtm workflow

### Technical

- bump the minor-updates group with 2 updates
- bump the patch-updates group with 2 updates

## v0.4.0 (2025-05-30)

### Feat

- add support for new gemini 2.5 flash

## v0.3.0 (2025-05-29)

### Feat

- **#18**: add json formatter and new `--output-format` option and config
- **#19**: add initial support for local LLMs

### Fix

- **#32**: relative line number for GitHub was incorrect
- pass model_url to guidegenerator
- allow any name given a --model-url

### Docs

- add @Rooni as a contributor

### Technical

- add issue template

## v0.2.0 (2025-05-28)

### Feat

- **#16**: add token cost summary to ai reviews

### Fix

- update summary format and fix lint issue
- cli error prevented users from selecting deepseek models

### CI

- add security steps to pipeline
- remove unnecessary cli opts for lgtm workflow

### Technical

- add dependabot

## v0.1.4 (2025-05-26)

### Docs

- add explanation for categories and severities to README

## v0.1.3 (2025-05-23)

### Fix

- lgtm link after moving to github
- yml was incorrect

### Docs

- mention lgtm workflow in README

### Technical

- fix gh action name
- add more CODEOWNERS to allow more reviewers

## v0.1.2 (2025-05-23)

### Fix

- lgtm yml entrypoint

### CI

- restrict usage of lgtm reviews to maintainers
- add docker command for lgtm to action
- testing lgtm
- add lgtm to lgtm

## v0.1.1 (2025-05-23)

### Feat

- add new `guide` command to generate a reviewer guide
- add support for GitHub
- add support for optional agent settings
- add support for DeepSeek
- add support for Mistral
- add collapsible section to review comment with metadata
- support Anthropic (claude) models
- add pr title and summary to the user prompt
- add support for Google's Gemini models
- add Dockerfile
- more granular comment positioning
- add Security category and re-write category explanations
- add configurable categories/presets
- support and autodetect pyproject.toml files
- autodetect lgtm.toml and validate config fields
- add publish and silent to config file opts
- sort review comments by severity
- add model to config file and hide secrets from verbose output
- get secrets also from env variables
- add ability to exclude files from review
- add config file and cli args to set tech in PR
- take advantage of multiple agents-make the second agent add suggestions
- create a summarizing agent to reduce noise
- tweak prompt to add explanation about scores and severities
- Add code snippet to the comments
- add file context to the prompt
- tweak prompt and add better evaluation PRs
- add severity and category to comments
- allow to customize model
- improve prompt to avoid empty comments, add review score
- add basic logging
- add rich for better console prints
- quick & dirty script to evaluate reviews
- post comments as inline to the file and line number
- gitlab comment with summary
- prototype to get the ball rolling

### Fix

- copy readme in docker too
- venv out of cache
- tweak guide prompt
- copyedit readme
- make the summary comment of reviews more pleasent to the eye
- handle exceptions by pydantic-ai
- some typos and small doctring update
- only print comments in terminal if there are any
- reduce errors by added/removed confusions
- provide gemini models ourselves
- tweak prompt to avoid unusual errors
- small bug where __main__ was not using config for silent and publish opts
- lgtm executable not available in PATH
- download context from main branch if it fails on PR
- make logging work also for evaluation script
- parse git diff before passing it to the AI
- solve lint config issues

### Refactor

- common cli args abstracted
- move formatters out of client and main
- parse url as soon as possible

### CI

- restrict bump to only main
- add docker publish step
- make publish depend on bump
- publish step to pypi
- set up caches in ci, and small fixes to readme
- add basic github actions

### Docs

- fix inconsistent title
- fix gl step definition in readme
- fix some readme issues
- improve docs after GitHub support
- add docs for supported models

### Technical

- LICENSE date
- change publish to main for now
- add badges
- reset version
- add assessments
- add codeowners
- convert pyproject.toml into a PEP 621 compliant file
- add some pictures
- add contributors to readme
- prepare for github
- switch to gemini by default
- some findings after pilot config
- add lgtm to lgtm
- evaluate gpt-4.1 vs gpt-4o
- cruft update and new test
- bump python support to 3.13 and drop support for 3.11
- bump pydantic ai to get rid of some bugs
- update notion urls
- bump pydantic ai to new breaking version
- cruft update and pre-commit changes
- add logo to readme
- add current placeholder assets
- initial commit
- template init

### Tests

- add missing test for ReviewGuideGenerator
- more strict mypy settings
