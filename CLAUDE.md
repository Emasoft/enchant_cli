# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Development Guidelines and Rules
- *CRITICAL*: when reading the lines of the source files, do not read just few lines like you usually do. Instead always read all the lines of the file (until you reach the limit of available context memory). No matter what is the situation, searching or editing a file, ALWAYS OBEY TO THIS RULE!!!.
- *CRITICAL*: do not ever do unplanned things or take decisions without asking the user first. All non trivial changes to the code must be planned first, approved by the user, and added to the tasks_checklist.md first. Unless something was specifically instructed by the user, you must not do it. Do not make changes to the codebase without duscussing those with the user first and get those approved. Be conservative and act on a strict need-to-be-changed basis.
- *CRITICAL*: COMMIT AFTER EACH CHANGE TO THE CODE, NO MATTER HOW SMALL!!!
- *CRITICAL*: after receiving instructions from the user, before you proceed, confirm if you understand and tell the user your plan. If instead you do not understand something, or if there are choices to make, ask the user to clarify, then tell the user your plan. Do not proceed with the plan if the user does not approve it.
- *CRITICAL*: **Auto-Lint after changes**: Always run the linters (like ruff, shellcheck, mypy, yamllint, eslint, etc.) after any changes to the code files! ALWAYS DO IT BEFORE COMMITTING!!
- *CRITICAL*: **Ultrathink before acting**: always ultrathink! Your thinking capabilities are not just for show. USE THEM!!!
- *CRITICAL*: Never use GREP! Use RIPGREP instead!
- *CRITICAL*: Never use pip. Use `uv pip <commands>` instead. Consider pip deprecated in favor of uv pip.
- be extremely meticulous and accurate. always check twice any line of code for errors when you edit it.
- never output code that is abridged or with parts replaced by placeholder comments like `# ... rest of the code ...`, `# ... rest of the function as before ...`, `# ... rest of the code remains the same ...`, or similar. You are not chatting. The code you output is going to be saved and linted, so omitting parts of it will cause errors and broken files.
- Be conservative. only change the code that it is strictly necessary to change to implement a feature or fix an issue. Do not change anything else. You must report the user if there is a way to improve certain parts of the code, but do not attempt to do it unless the user explicitly asks you to.
- when fixing the code, if you find that there are multiple possible solutions, do not start immediately but first present the user all the options and ask him to choose the one to try. For trivial bugs you don't need to do this, of course.
- never remove unused code or variables unless they are wrong, since the program is a WIP and those unused parts are likely going to be developed and used in the future. The only exception is if the user explicitly tells you to do it.
- don't worry about functions imported from external modules, since those dependencies cannot be always included in the chat for your context limit. Do not remove them or implement them just because you can''t find the module or source file they are imported from. You just assume that the imported modules and imported functions work as expected. If you need to change them, ask the user to include them in the chat.
- Always update the project version after changes. Use semantic version format for updating the project version: `{major - breaking changes or features}.{minor - non breaking changes or features}.{patch - small changes/fixes}`.
- think ultrahard when analyzing the project! spend a long time thinking deeply to understand completely the code flow and inner working of the program before writing any code or making any change.
- if the user asks you to implement a feature or to make a change, always check the source code to ensure that the feature was not already implemented before or it is implemented in another form. Never start a task without checking if that task was already implemented or done somewhere in the codebase.
- if you must write a function, always check if there are already similar functions that can be extended or parametrized to do what new function need to do. Avoid writing duplicated or similar code by reusing the same flexible helper functions where is possible.
- keep the source files as small as possible. If you need to create new functions or classes, prefer creating them in new modules in new files and import them instead of putting them in the same source file that will use them. Small reusable modules are always preferable to big functions and spaghetti code.
- Always check for leaks of secrets in the git repo with `gitleaks git --verbose` and `gitleaks dir --verbose`.
- commit should be atomic, specific, and focus on WHAT changed in subject line with WHY explained in body when needed.
- use semantic commit messages following the format in the Git Commit Message Format memory
- Write only shippable, production ready code. If you wouldn’t ship it, don’t write it.
- Don't drastically change existing patterns without explicit instruction
- before you execute a terminal command, trigger the command line syntax help or use `cheat <command>` to learn the correct syntax and avoid failed commands.
- if you attempt to run a command and the command is not found, first check the path, and then install it using `brew install`.
- never take shortcuts to skirt around errors. fix them.
- If the solution to a problem is not obvious, take a step back and look at the bigger picture.
- If you are unsure, stop and ask the user for help or additional information.
- if something you are trying to implement or fix does not work, do not fallback to a simpler solution and do not use workarounds to avoid implement it. Do not give up or compromise with a lesser solution. You must always attempt to implement the original planned solution, and if after many attempts it still fails, ask the user for instructions.
- always use type annotations
- always keep the size of source code files below 10Kb. If writing new code in a source file will make the file size bigger than 10Kb, create a new source file , write the code there, and import it as a module. Refactor big files in multiple smaller modules.
- always preserve comments and add them when writing new code.
- always write the docstrings of all functions and improve the existing ones. Use Google-style docstrings with Args/Returns sections, but do not use markdown.
- never use markdown in comments.
- when using the Bash tool, always set the timeout parameter to 1800000 (30 minutes).
- always tabulate the tests result in a nice table.
- do not use mockup tests or mocked behaviours unless it is absolutely impossible to do otherwise. If you need to use a service, local or remote, do not mock it, just ask the user to activate it for the duration of the tests. Results of mocked tests are completely useless. Only real tests can discover issues with the codebase.
- always use a **Test-Driven Development (TDD)** methodology (write tests first, the implementation later) when implementing new features or change the existing ones. But first check that the existing tests are written correctly.
- always plan in advance your actions, and break down your plan into very small tasks. Save a file named `DEVELOPMENT_PLAN.md` and write all tasks inside it. Update it with the status of each tasks after any changes.
- Plan all the changes in detail first. Identify potential issues before starting, and revise the plan until it will not create issues before starting.
- When making changes, identify all files that would need import updates first
- After each change, check all type annotations for consistency
- Make all changes in a single, well-planned operation with surgical edits
- Always lint the file after making all the changes to it, but not before
- Always run the tests relevant to the changed files after making all the changes planned, but not before
- Do one comprehensive commit at the end of each operation if the code passes the tests
- If you make errors while implementing the changes, examine you errors, ultrathink about them and write the lessons learned from them into CLAUDE.md for future references, so you won't repeat the same errors in the future.
- Use Prefect for all scripted processing ( https://github.com/PrefectHQ/prefect/ ), with max_concurrency=1 for max safety.
- Install `https://github.com/fpgmaas/deptry/` and run it at every commit.
- Add deptry to the project pre-commit configuration following these instructions: `https://github.com/astral-sh/uv-pre-commit`.
- Add deptry to both the local and the remote github workflows actions, so it can be used in the CI/CD pipeline automatically at every push/release as instructed here: `https://docs.astral.sh/uv/guides/integration/github/`.
- Install and run yamllint and actionlint at each commit (add them to pre-commit both local and remote, run them with `uv run`).
- You can run the github yaml files locally with `act`. Install act and read the docs to configure it to work with uv: `https://github.com/nektos/act`.
- Since `act` requires Docker, follow these instructions to setup docker containers with uv: `https://docs.astral.sh/uv/guides/integration/docker/`
- do not create prototypes or sketched/abridged versions of the features you need to develop. That is only a waste of time. Instead break down the new features in its elemental components and functions, subdivide it in small autonomous modules with a specific function, and develop one module at time. When each module will be completed (passing the test for the module), then you will be able to implement the original feature easily just combining the modules. The modules can be helper functions, data structures, external librries, anything that is focused and reusable. Prefer functions at classes, but you can create small classes as specialized handlers for certain data and tasks, then also classes can be used as pieces for building the final feature.
- When commit, never mention Claude as the author of the commits or as a Co-author.
- when refactoring, enter thinking mode first, examine the program flow, be attentive to what you're changing, and how it subsequently affects the rest of the codebase as a matter of its blast radius, the codebase landscape, and possible regressions. Also bear in mind the existing type structures and interfaces that compose the makeup of the specific code you're changing.
- Generate complete, tested code on first attempt.
- Always anchor with date/time and available tools.
- Clearly label the 4 TDD phases (analysis --> tests implementation --> code implementation -> debugging).
- Implement concrete solutions, no placeholders or abridged versions.
- Batch related tool calls and parallelize where safe.
- Proactively handle all edge cases on first attempt.
- Before marking a todo as complete, always spawn a subagent that especially checks the edited test files for tampering, then lint both the edited tests files and the edited code files, and finally run the tests relative to that todo again. If the tests pass, mark the todo task as complete.
- always use `Emasoft` as the user name, author and committer name for the git repo.
- always use `713559+Emasoft@users.noreply.github.com` as the user email and git committer email for the git repo.
- always add the following shebang at the beginning of each python file:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```
- always add a short changelog before the imports in of the source code to document all the changes you made to it.

```python
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# <your changelog here…>
#
```


### Formatting Rules
- Use only ruff format for formatting python files. Read how here: https://docs.astral.sh/ruff/formatter/
- Set ruff format to allows line lenght up to 320 chars, using the `--line-length=320` (max supported by ruff)
- Do not use pyproject.toml or ruff.toml to configure ruff, since there are too many variations of the command used in the workflows. Aleays run it in isolated mode with `--isolated` and set all options via cli.
- Use autofix to format pull-requests automatically. Read how here: https://autofix.ci/setup
- Use Prettier to format all other code files (except python and yaml).
- Use `pnpm run format` to run Prettier on node.js source files.
- Configure Prettier for github formatting actions following the instructions here: `https://prettier.io/docs/ci` and `https://autofix.ci/setup`.
- To format yaml files only use yamlfmt. Install yamlfmt with:
```
go install github.com/google/yamlfmt/cmd/yamlfmt@latest
```

Then create this configuration file (`.yamlfmt`):
```yaml
# .yamlfmt
formatter:
  indent: 2                      # Use 2-space indentation (standard in GitHub workflows)
  retain_line_breaks: true       # Preserve existing blank lines between blocks
  indentless_arrays: true        # Don’t add extra indent before each “-” list item
  scan_folded_as_literal: true   # Keep multi-line “>”-style blocks as-is, avoid collapsing
  trim_trailing_whitespace: true # Remove trailing spaces at end of lines
  eof_newline: true              # Ensure the file ends with exactly one newline
gitignore_excludes: true

```

To use yamlfmt:

```
# Format a single workflow file
yamlfmt -path .github/workflows/ci.yml

# Or format all workflow files
yamlfmt -path .github/workflows
```
- You should place the .yamlfmt file in the root directory of the project.
- You must check the .yamlfmt configuration file to see if you are using different settings (i.e. indent 2 or 4 spaces, etc.)
- Add yamlfmt to the git hooks/uv-pre-commit, so it is automatically executed at each commit.
- IMPORTANT: yamlfmt must not format all yaml files, but only those inside the .github subfolder, since it is configured for the github workflows formatting style. Other yaml files may exist outside the .github folder using different formatting styles. Do not format those files.


### Linting Rules
- Use `ruff check` and mypy for python
- Use autofix to lint pull-requests automatically. Read how here: https://autofix.ci/setup
- Do not use pyproject.toml or ruff.toml to configure `ruff check`, since there are too many variations of the command used in the workflows. Aleays run it in isolated mode with `--isolated` and set all options via cli.
- Use eslint for javascript
- Use shellcheck for bash
- Use actionlint snd yamllint for yaml
- Use jsonlint for json
- Run ruff using this command: `uv run ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --isolated --fix --output-format full`
- Run mypy using this command: `COLUMNS=400 uv run mypy --strict --show-error-context --pretty --install-types --no-color-output --show-error-codes --show-error-code-links --no-error-summary --follow-imports=normal <files> >mypy_lint_log.txt`
- use shellcheck-py if you need to use shellcheck from a python script
- Use `pnpm run lint` to run eslint on node.js source files.
- Add git hooks that uses uv-pre-commit to run the linting at each commit, read the guide here: `https://docs.astral.sh/uv/guides/integration/pre-commit/`
- Use deptry to check the dependencies. To install deptry follow hese instructions: `https://github.com/fpgmaas/deptry/`
- Add deptry to the project pre-commit configuration following these instructions: https://github.com/astral-sh/uv-pre-commit .
- Add deptry to both the local and the remote github workflows/ actions, so it can be used in the CI/CD pipeline automatically at every push/release as instructed here: https://docs.astral.sh/uv/guides/integration/github/ .
- Install and run yamllint and actionlint at each commit (add them to pre-commit both local and remote, run them with `uv run`).
- If you need to, you can run the github yaml files locally with `act`. Install act and read the docs to configure it to work with uv: https://github.com/nektos/act


### Testing Rules
- Always use pytest and pytest-cov for testing
- Run tests with uv (`uv run pytest`) or `pnpm run tests`
- For coverage reports: `uv run pytest --cov=. --cov-report=html`
- Add git hooks that uses uv-pre-commit to run the tests at each commit, read the guide here: `https://docs.astral.sh/uv/guides/integration/pre-commit/`
- Always convert the xtests in normal tests. Negative tests are confusing. Just make the test explicitly check for the negative outcome instead, and if the outcome is negative, the test is passed.
- Always show a nicely color formatted table with the list of all tests (the functions, not the file) and the outcome (fail, success, skip, error).
- The table must use unicode border blocks to delimit the cells, thicker for the header row.
- The table should report not only the name of the function, but the description of the test function in the docstrings.
- All tests functions should include a meaningful one-line string that synthetically describes the test and its aim.
- If a test function lacks this description, add it to the source files of the tests.
- All test functions must have docstrings with a short description that will be used by the table to describe the test.
- Mark the slow tests (those usually skipped when running tests on GitHub, or that need some extra big dependencies installed) with the emoji of a snail 🐌. Be sure to account for the extra character in the table formatting.

## GITHUB WORKFLOWS AFTER PUSHING
- Use GH cli tool to interact with github
- Keep synching, linting, formatting, testing and building, releasing and publishing separated in different workflows.
    - synch.yml = update the dependency libraries and the dev tools to the version indicated in the configuration files (i.e. `pyproject.toml`, `package.json`, `requirements-dev.txt`, etc.). Use uv synch for python.
    - lint.yml = lint the code files (ruff, eslint, shellcheck, actionlint, yamllint, jsonlint, pnpm, deptry, etc.)
    - format.yml = format the code files (ruff, prettier, yamlfmt, pnpm, etc.)
    - test.yml = run the tests for all code files (pytest, pytest-cov, playwright, etc.)
    - build.yml = build the project packages with uv build
    - release.yml = add a new release to github from the latest build, bump the semantic version and update the changelog
    - publish.yml = publish the ladt release to PyPi and other online indexes
    - metrics.yml = compute varous code metrics and statistics to be used to define the health of the project, the coverage, the issues/bugs open, the repo tars, repo size, etc. to be used in the docs and in the README.md
    - docs.yml = update the README.md file and all the docs with the latest changes. Also update the PyPi package info page if available and up to date.
    - ci.yml = orchestrator for the whole CI pipeline (it calls: synch, lint, format, test, build, release, publish, docs)
    - prfix.yml = review and autofix fix pull requests
    - check.yml = only check the project (it calls: synch, lint, format, test, security).
    - generate.yml = only build the package (it calls: synch, lint, format, test, build)
    - security.yml = some custom security checks, but this is optional since github already checks security. Use it only for project specific checks not included in github controls.
- Do not setup cron jobs. Setup the workflows to be triggered when the code change or there are PR
- Setup the CI/CD pipeline and all workflows to use an uv environment. Read how here: `https://docs.astral.sh/uv/guides/integration/github/`
- Always use uv-pre-commit ( `https://github.com/astral-sh/uv-pre-commit` ). Read how here: `https://docs.astral.sh/uv/guides/integration/pre-commit/`
- Do not use Super-Linter, use a simpler lint workflow that runs tools directly
- Use shellcheck-py if you need to control shellcheck linter from python code.
- Ensure formatting consistency between local and github by using pre-commit hooks with identical commands for the lint workflow and the formatting workflow
- Let the tests autodetect the environment (local or remote/github)
- Make sure the tests have a configuration for remote run on github that is different from the local one. Make API tests flexible so they can use different parameters when run locally and remotely.
- Let the test retry counts and all retry logic in the code be configurable with different max values for local and remote for faster CI execution
- After committing and pushing the project to github, always check if the push passed the github actions and checks. Wait few seconds, according to the average time needed for the lint and tests to run, then use the following commands to retrieve the last logs of the last actions:
```
gh run list --limit <..max number of recent actions logs to list...>
gh run view <... run number ...> --log-failed
```
Example:
```
> gh run list --limit 10
> mkdir -p ./logs && gh run view 15801201757 --log-failed > ./logs/15801201757.log
etc..

```
Then examine the log files saved in the ./logs/ subdir. Think ultrahard to find the causes of the failures. Use actionlint, yamllint and act to test and verify the workflows issues. Then report the issues causing the failings.

## API Configuration
- The system uses OpenRouter API for both renaming and translation phases
- Set `OPENROUTER_API_KEY` environment variable with your OpenRouter API key
- OpenRouter provides unified cost tracking across all models
- Model names are automatically mapped (e.g., "gpt-4o-mini" → "openai/gpt-4o-mini")


### Key Principles for CI/CD Success:

1. **Avoid Super-Linter** - Use a simpler lint workflow that runs tools directly
   - Super-Linter has configuration path issues and is overly complex. Do not use it.
   - Direct tool execution is more transparent and easier to debug

2. **Ensure Local/CI Formatting Consistency** - Use pre-commit hooks in CI workflows
   - Run `uv run pre-commit run <hook> --all-files` in CI instead of direct tool commands
   - This ensures identical behavior between local development and CI

3. **Separate Concerns in Workflows**
   - Keep linting, testing, and building in different workflows
   - This makes failures easier to diagnose and workflows faster to run

4. **Environment-Aware Test Configuration**
   - Tests should detect if running locally vs on GitHub Actions
   - Use environment detection: `is_running_in_test()` function
   - Different retry counts: local (10 retries) vs CI (2 retries)
   - Different timeouts: local (60s max) vs CI (5s max)

5. **Flexible API Tests**
   - Make API tests accept various valid responses, parsing the right tags or the right code blocks and ignoring the remaining text as it is variable
   - If the AI model and the API service support structured json responses, make use of them to get deterministic responses. If you use Openrouter, read the following: `https://openrouter.ai/docs/features/structured-outputs`. You can find the list of models supporting structured output here: `https://openrouter.ai/models?fmt=table&order=context-high-to-low&supported_parameters=structured_outputs`.
   - Put in place boundaries and measures to prevent the risks of consuming too many tokens (and spending too much money) when running API requests during the tests.
   - If the model allows API configuration variations, set up 2 or 3 example configurations max, choosing the most significant ones. Do not attempt to tests all possible combinations of API options.
   - If the project supports both remote API services and local API services or models, do not run the tests for the local ones when on github, since local models are not available there.
   - Set two profiles for the tests, LOCAL and REMOTE-CI (github).

6. **Configurable Retry Logic**
   - Use constants like `DEFAULT_MAX_RETRIES` and `DEFAULT_MAX_RETRIES_TEST`
   - Check environment in retry decorators to use appropriate values
   - Reduces CI execution time from 10+ minutes to ~2 minutes

### Implementation Example:
```python
def is_running_in_test() -> bool:
    """Detect if code is running in a test environment."""
    return ("pytest" in sys.modules or
            os.environ.get("PYTEST_CURRENT_TEST") or
            os.environ.get("CI") or
            os.environ.get("GITHUB_ACTIONS"))
```

## pre-commit: install it with uv

It is recommended to install pre-commit using uv’s tool mechanism, using this command:

```
$ uv tool install pre-commit --with pre-commit-uv
```

Running it, you’ll see output describing the installation process:

```
$ uv tool install pre-commit --with pre-commit-uv
Resolved 11 packages in 1ms
Installed 11 packages in 8ms
...
Installed 1 executable: pre-commit
```

This will put the `pre-commit` executable in `~/.local/bin` or similar (per the documentation). You should then be able to run it from anywhere:

```
$ pre-commit --version
pre-commit 4.2.0 (pre-commit-uv=4.1.4, uv=0.7.2)
```

The install command also adds [pre-commit-uv](https://pypi.org/project/pre-commit-uv/), a plugin that patches pre-commit to use uv to install Python-based tools. This drastically speeds up using Python-based hooks, a common use case. (Unfortunately, it seems pre-commit itself won’t be adding uv support.)

With pre-commit installed globally, you can now install its Git hook in relevant repositories per usual:

```
$ cd myrepo

$ pre-commit install
pre-commit installed at .git/hooks/pre-commit

$ pre-commit run --all-files
[INFO] Installing environment for https://github.com/pre-commit/pre-commit-hooks.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Using pre-commit with uv 0.7.2 via pre-commit-uv 4.1.4
check for added large files..............................................Passed
check for merge conflicts................................................Passed
trim trailing whitespace.................................................Passed
```

## Upgrade pre-commit

To upgrade pre-commit installed this way, run:

```
$ uv tool upgrade pre-commit
```

For example:

```
$ uv tool upgrade pre-commit
Updated pre-commit v4.1.0 -> v4.2.0
 - pre-commit==4.1.0
 + pre-commit==4.2.0
Installed 1 executable: pre-commit
```

This command upgrades pre-commit and all of its dependencies, in its managed environment.
For more information, read the uv tool upgrade documentation: `https://docs.astral.sh/uv/concepts/tools/`



### Module Splitting and Refactoring Best Practices

When splitting a large file into smaller modules, ALWAYS follow these steps:

#### 1. Pre-Refactoring Analysis
- **CRITICAL: Read the ENTIRE file first** - Do not read only few lines! Examine the whole file to understand all dependencies
- **Think ultrahard** about the codebase structure and the best way to refactor it
- **Plan the new directory tree structure** in advance and document it
- **Create a full backup** of each file being refactored: `cp original.py original_backup.py`
- **Only delete backups** after verifying no function, class or element was lost

#### 2. Create Comprehensive Inventory
Create `refactoring_log.md` to track all changes and create an inventory checklist of ALL:
- Classes and their methods
- Functions (standalone and nested)
- Constants and global variables
- Type definitions and NamedTuples
- Decorators
- Import statements
- Module-level code
- Meta classes
- Helper functions
- Wrappers

Each element can have multiple states:
- `[ ] to_be_moved`
- `[x] moved_to_<filename>`
- `[x] duplicated_to_<filename>`
- `[x] merged_with_similar_and_moved_to_<filename>`
- `[x] made_public`
- `[x] changed_to_be_more_flexible`
- `[x] updated_internal_references`
- `[x] changed_to_class_member`
- `[x] changed_to_non_class_member`
- `[x] updated_parameters_and_docstrings`
- `[x] updated_comments`
- `[x] commented_out`
- `[x] added_to_wrapper`
- `[x] moved_inside_a_function`
- `[x] moved_outside_a_function`
- `[x] passed_as_argument_to_external_function`
- `[x] passed_as_argument_to_external_class`
- `[x] converted_to_dynamic_function`

#### 3. Planning Phase
Create `REFACTORING_PLAN.md` with:
```markdown
# Refactoring Plan for [filename]

## Current Directory Structure
```
src/
  module.py (54KB)
```

## Target Directory Structure
```
src/
  module.py (8KB)
  module_constants.py (5KB)
  module_utils.py (10KB)
  module_core.py (20KB)
```

## Current Structure
- [ ] Class A (150 lines) -> to_be_moved
  - [ ] method1
  - [ ] method2
- [ ] Function B (50 lines) -> to_be_moved
- [ ] Constant C -> to_be_moved
- [ ] Global variable D -> to_be_moved

## Target Modules
1. module_core.py - Core functionality
   - [ ] Class A → module_core.py
2. module_constants.py - Constants and configuration
   - [ ] Constant C → module_constants.py
   - [ ] Global variable D → module_constants.py
3. module_utils.py - Utility functions
   - [ ] Function B → module_utils.py
```

#### 4. Execution Phase - One Element at a Time
For EACH element:
1. **Move the element** to target module
2. **Update all imports** in both original and all referencing files
3. **Update the tests** for this element immediately
4. **Lint and format** both source and target files: `uv run ruff format && uv run ruff check --fix`
5. **Run tests** specific to this element: `uv run pytest tests/test_<element>.py -xvs`
6. **Verify references**: `grep -r "element_name" . --include="*.py"`
7. **Update checklist** with new state: `[x] Function B → moved_to_module_utils.py`
8. **Remove from original** only after tests pass
9. **Track with TodoWrite** to monitor progress
10. **Commit immediately** after tests pass: `git add -A && git commit -m "refactor: move Function B to module_utils.py"`

#### 5. Verification After Each Move
- **Verify element was removed** from original (not duplicated)
- **Check all references** are updated
- **Run mypy** to catch type errors: `uv run mypy <files>`
- **Update refactoring_log.md** with the change details

#### 6. Final Verification Phase
- **Diff all backups** against originals: `diff -u module_backup.py module.py`
- **Verify no lost elements** by checking inventory checklist
- **Check for duplicates**: `grep -r "def function_name" . --include="*.py"`
- **Verify all imports** throughout codebase
- **Check directory structure** matches plan
- **Run full test suite**: `uv run pytest`
- **Run e2e tests** to ensure everything works exactly as before
- **Check file sizes** - sum of new modules should ≈ original size

#### 7. Post-Refactoring
- **Only remove backup files** after ALL tests pass and e2e verification
- **Update documentation** to reflect new module structure
- **Final commit** with summary of all moves

#### Critical Rules
- **NEVER make changes before examining the WHOLE file**
- **NEVER skip updating and running tests after each change**
- **NEVER move multiple elements simultaneously**
- **NEVER assume references are found** - actively search and verify
- **NEVER delete original code** before tests confirm the move worked
- **ALWAYS commit after each successful element refactoring**
- **ALWAYS maintain refactoring_log.md** to trace all movements

#### Refactoring Log Template
```markdown
# Refactoring Log for [module.py]

## 2024-XX-XX HH:MM - Function calculate_total
- Status: moved_to_module_utils.py
- Updated imports in: main.py, tests/test_calculate.py
- Tests updated: test_calculate_total()
- Verified references: 3 files updated
- Committed: abc123def

## 2024-XX-XX HH:MM - Class DataProcessor
- Status: moved_to_module_core.py, made_public, updated_parameters_and_docstrings
- Updated imports in: 5 files
- Tests updated: test_data_processor.py
- Added backward compatibility wrapper
- Committed: def456ghi
```


### Code Quality

- Run all linters (uv-pre-commit, ruff, mypy, shellcheck, yamllint) with `uv run <command..>`

# Python formatting and linting commands syntax:
uv run ruff format       # format with ruff
uv run ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --isolated --fix --output-format full
COLUMNS=400 uv run mypy --strict --show-error-context --pretty --install-types --no-color-output --show-error-codes --show-error-code-links --no-error-summary --follow-imports=normal <files> >mypy_lint_log.txt

# TypeScript/JavaScript formatting and linting commands syntax to use internally in dhtl:
uv run pnpm run lint            # ESLint
uv run pnpm run format          # Prettier
uv run pnpm run check           # Check formatting without fixing

# Bash scripts linting commands syntax to use internally in dhtl:
uv run shellcheck --severity=error --extended-analysis=true  # Shellcheck (always use severity=error!)

# YAML scripts linting
uv run yamllint
uv run actionlint

# Gitleaks and secrets preservation
gitleaks git --verbose
gitleaks dir --verbose


### Building and Packaging

# Build Python package
uv init                   # Init package with uv, creating pyproject.toml file, git and others
uv init --python 3.10     # Init package with a specific python version
uv init --app             # Init package with app configuration
uv init --lib             # Init package with library module configuration
uv python install 3.10    # Download and install a specific version of Python runtime
uv python pin 3.10        # Change python version for current venv
uv add <..module..>       # Add module to pyproject.toml dependencies
uv add -r requirements.txt # Add requirements from requirements.txt to pyproject.toml
uv pip install -r requirements.txt # Install dependencies from requirements.txt
uv pip compile <..arguments..> # compile requirement file
uv build                  # Build with uv
uv run python -m build    # Build wheel only
uv run pnpm run build     # Build frontend with pnpm

## UV Build Process - Complete Guide

### Prerequisites for Building with UV
1. **Project Structure Requirements**:
   - Valid `pyproject.toml` with build-system configuration
   - Package source files properly organized
   - `__init__.py` files in all package directories
   - README.md or README.rst for long description
   - Clean working directory (no test artifacts)

2. **Build System Configuration**:
   ```toml
   [build-system]
   requires = ["hatchling"]  # or other build backend
   build-backend = "hatchling.build"
   ```

### Step-by-Step UV Build Process

#### 1. Prepare the Project Environment
```bash
# Ensure you have a virtual environment
uv venv

# Sync all dependencies including dev dependencies
uv sync --all-extras

# Verify Python version matches project requirements
uv python find
```

#### 2. Clean Previous Build Artifacts
```bash
# Remove any existing build directories
rm -rf dist/ build/ *.egg-info/

# Clean pytest cache and coverage files
rm -rf .pytest_cache/ .coverage htmlcov/

# Remove __pycache__ directories
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

#### 3. Validate Project Configuration
```bash
# Check pyproject.toml is valid
cat pyproject.toml | python -m tomllib

# Ensure all required fields are present
# Required: name, version, description, authors, requires-python
```

#### 4. Build the Package
```bash
# Build both source distribution (sdist) and wheel
uv build

# Build only source distribution
uv build --sdist

# Build only wheel
uv build --wheel

# Build with specific output directory
uv build -o dist/

# Build with verbose output to debug issues
uv build -v
```

#### 5. Post-Build Verification
```bash
# List built artifacts
ls -la dist/

# Check wheel contents
unzip -l dist/*.whl | head -20

# Verify sdist contents
tar tzf dist/*.tar.gz | head -20

# Test installation in a fresh environment
uv venv test_env
source test_env/bin/activate  # or test_env\Scripts\activate on Windows
uv pip install dist/*.whl
python -c "import enchant_book_manager; print(enchant_book_manager.__version__)"
deactivate
rm -rf test_env
```

### Common Build Issues and Solutions

1. **Missing pyproject.toml fields**:
   - Ensure all required metadata fields are present
   - Use `uv init --lib` to generate a template if needed

2. **Import errors during build**:
   - Verify all `__init__.py` files are present
   - Check relative imports are correct
   - Ensure no circular dependencies

3. **Build backend not found**:
   - Install the build backend: `uv add --dev hatchling`
   - Or use setuptools: `requires = ["setuptools>=61.0"]`

4. **Version conflicts**:
   - Use `uv sync --refresh` to update locked dependencies
   - Check `requires-python` matches your environment

### Build Configuration Options

```toml
# pyproject.toml build configuration examples

[tool.hatch.build]
include = [
    "*.py",
    "*.txt",
    "*.md",
]
exclude = [
    "tests/",
    "docs/",
    ".git/",
]

[tool.hatch.build.targets.wheel]
packages = ["enchant_book_manager"]

[tool.hatch.version]
path = "__init__.py"
```

### Publishing Packages (Optional)

```bash
# Install twine for uploading
uv add --dev twine

# Upload to PyPI (requires PyPI account)
uv run twine upload dist/*

# Upload to test PyPI first
uv run twine upload --repository testpypi dist/*
```

### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.10'

- name: Install uv
  run: pip install uv

- name: Build package
  run: |
    uv venv
    uv sync
    uv build

- name: Upload artifacts
  uses: actions/upload-artifact@v3
  with:
    name: dist
    path: dist/
```

# What uv init generates:
```
.
├── .venv
│   ├── bin
│   ├── lib
│   └── pyvenv.cfg
├── .python-version
├── README.md
├── main.py
├── pyproject.toml
└── uv.lock

```

# What pyproject.toml contains:

```
[project]
name = "hello-world"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
dependencies = []

```

# What the file .python-version contains
The .python-version file contains the project's default Python version. This file tells uv which Python version to use when creating the project's virtual environment.

# What the .venv folder contains
The .venv folder contains your project's virtual environment, a Python environment that is isolated from the rest of your system. This is where uv will install your project's dependencies and binaries.

# What the file uv.lock contains:
uv.lock is a cross-platform lockfile that contains exact information about your project's dependencies. Unlike the pyproject.toml which is used to specify the broad requirements of your project, the lockfile contains the exact resolved versions that are installed in the project environment. This file should be checked into version control, allowing for consistent and reproducible installations across machines.
uv.lock is a human-readable TOML file but is managed by uv and should not be edited manually.

# Install package
uv pip install dist/*.whl    # Install built wheel
uv pip install -e .         # Development install

# Install global uv tools
uv tools install ruff
uv tools install mypy
uv tools install yamllint
uv tools install bump_my_version
...etc.

# Execute globally installed uv tools
uv tools run ruff <..arguments..>
uv tools run mypy <..arguments..>
uv tools run yamllint <..arguments..>
uv tools run bump_my_version <..arguments..>
...etc.


## More detailed list of options for the uv venv command:
Create a virtual environment

Usage: uv venv [OPTIONS] [PATH]

Arguments:
  [PATH]  The path to the virtual environment to create

Options:
      --no-project                           Avoid discovering a project or workspace
      --seed                                 Install seed packages (one or more of: `pip`, `setuptools`, and `wheel`) into the virtual environment [env:
                                             UV_VENV_SEED=]
      --allow-existing                       Preserve any existing files or directories at the target path
      --prompt <PROMPT>                      Provide an alternative prompt prefix for the virtual environment.
      --system-site-packages                 Give the virtual environment access to the system site packages directory
      --relocatable                          Make the virtual environment relocatable
      --index-strategy <INDEX_STRATEGY>      The strategy to use when resolving against multiple index URLs [env: UV_INDEX_STRATEGY=] [possible values:
                                             first-index, unsafe-first-match, unsafe-best-match]
      --keyring-provider <KEYRING_PROVIDER>  Attempt to use `keyring` for authentication for index URLs [env: UV_KEYRING_PROVIDER=] [possible values: disabled,
                                             subprocess]
      --exclude-newer <EXCLUDE_NEWER>        Limit candidate packages to those that were uploaded prior to the given date [env: UV_EXCLUDE_NEWER=]
      --link-mode <LINK_MODE>                The method to use when installing packages from the global cache [env: UV_LINK_MODE=] [possible values: clone, copy,
                                             hardlink, symlink]

Python options:
  -p, --python <PYTHON>      The Python interpreter to use for the virtual environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Index options:
      --index <INDEX>                      The URLs to use when resolving dependencies, in addition to the default index [env: UV_INDEX=]
      --default-index <DEFAULT_INDEX>      The URL of the default package index (by default: <https://pypi.org/simple>) [env: UV_DEFAULT_INDEX=]
  -i, --index-url <INDEX_URL>              (Deprecated: use `--default-index` instead) The URL of the Python package index (by default: <https://pypi.org/simple>)
                                           [env: UV_INDEX_URL=]
      --extra-index-url <EXTRA_INDEX_URL>  (Deprecated: use `--index` instead) Extra URLs of package indexes to use, in addition to `--index-url` [env:
                                           UV_EXTRA_INDEX_URL=]
  -f, --find-links <FIND_LINKS>            Locations to search for candidate distributions, in addition to those found in the registry indexes [env:
                                           UV_FIND_LINKS=]
      --no-index                           Ignore the registry index (e.g., PyPI), instead relying on direct URL dependencies and those provided via `--find-links`

Cache options:
      --refresh                            Refresh all cached data
  -n, --no-cache                           Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                                           UV_NO_CACHE=]
      --refresh-package <REFRESH_PACKAGE>  Refresh cached data for a specific package
      --cache-dir <CACHE_DIR>              Path to the cache directory [env: UV_CACHE_DIR=]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help venv` for more details.


## More detailed list of options for the uv init command:
Create a new project

Usage: uv init [OPTIONS] [PATH]

Arguments:
  [PATH]  The path to use for the project/script

Options:
      --name <NAME>                    The name of the project
      --bare                           Only create a `pyproject.toml`
      --package                        Set up the project to be built as a Python package
      --no-package                     Do not set up the project to be built as a Python package
      --app                            Create a project for an application
      --lib                            Create a project for a library
      --script                         Create a script
      --description <DESCRIPTION>      Set the project description
      --no-description                 Disable the description for the project
      --vcs <VCS>                      Initialize a version control system for the project [possible values: git, none]
      --build-backend <BUILD_BACKEND>  Initialize a build-backend of choice for the project [possible values: hatch, flit, pdm, poetry, setuptools, maturin,
                                       scikit]
      --no-readme                      Do not create a `README.md` file
      --author-from <AUTHOR_FROM>      Fill in the `authors` field in the `pyproject.toml` [possible values: auto, git, none]
      --no-pin-python                  Do not create a `.python-version` file for the project
      --no-workspace                   Avoid discovering a workspace and create a standalone project

Python options:
  -p, --python <PYTHON>      The Python interpreter to use to determine the minimum supported Python version. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Cache options:
  -n, --no-cache               Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                               UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>  Path to the cache directory [env: UV_CACHE_DIR=]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command



## More detailed list of options for uv sync command:
Update the project's environment

Usage: uv sync [OPTIONS]

Options:
      --extra <EXTRA>                            Include optional dependencies from the specified extra name
      --all-extras                               Include all optional dependencies
      --no-extra <NO_EXTRA>                      Exclude the specified optional dependencies, if `--all-extras` is supplied
      --no-dev                                   Disable the development dependency group
      --only-dev                                 Only include the development dependency group
      --group <GROUP>                            Include dependencies from the specified dependency group
      --no-group <NO_GROUP>                      Disable the specified dependency group
      --no-default-groups                        Ignore the default dependency groups
      --only-group <ONLY_GROUP>                  Only include dependencies from the specified dependency group
      --all-groups                               Include dependencies from all dependency groups
      --no-editable                              Install any editable dependencies, including the project and any workspace members, as non-editable [env:
                                                 UV_NO_EDITABLE=]
      --inexact                                  Do not remove extraneous packages present in the environment
      --active                                   Sync dependencies to the active virtual environment
      --no-install-project                       Do not install the current project
      --no-install-workspace                     Do not install any workspace members, including the root project
      --no-install-package <NO_INSTALL_PACKAGE>  Do not install the given package(s)
      --locked                                   Assert that the `uv.lock` will remain unchanged [env: UV_LOCKED=]
      --frozen                                   Sync without updating the `uv.lock` file [env: UV_FROZEN=]
      --dry-run                                  Perform a dry run, without writing the lockfile or modifying the project environment
      --all-packages                             Sync all packages in the workspace
      --package <PACKAGE>                        Sync for a specific package in the workspace
      --script <SCRIPT>                          Sync the environment for a Python script, rather than the current project
      --check                                    Check if the Python environment is synchronized with the project

Index options:
      --index <INDEX>                        The URLs to use when resolving dependencies, in addition to the default index [env: UV_INDEX=]
      --default-index <DEFAULT_INDEX>        The URL of the default package index (by default: <https://pypi.org/simple>) [env: UV_DEFAULT_INDEX=]
  -i, --index-url <INDEX_URL>                (Deprecated: use `--default-index` instead) The URL of the Python package index (by default:
                                             <https://pypi.org/simple>) [env: UV_INDEX_URL=]
      --extra-index-url <EXTRA_INDEX_URL>    (Deprecated: use `--index` instead) Extra URLs of package indexes to use, in addition to `--index-url` [env:
                                             UV_EXTRA_INDEX_URL=]
  -f, --find-links <FIND_LINKS>              Locations to search for candidate distributions, in addition to those found in the registry indexes [env:
                                             UV_FIND_LINKS=]
      --no-index                             Ignore the registry index (e.g., PyPI), instead relying on direct URL dependencies and those provided via
                                             `--find-links`
      --index-strategy <INDEX_STRATEGY>      The strategy to use when resolving against multiple index URLs [env: UV_INDEX_STRATEGY=] [possible values:
                                             first-index, unsafe-first-match, unsafe-best-match]
      --keyring-provider <KEYRING_PROVIDER>  Attempt to use `keyring` for authentication for index URLs [env: UV_KEYRING_PROVIDER=] [possible values: disabled,
                                             subprocess]

Resolver options:
  -U, --upgrade                            Allow package upgrades, ignoring pinned versions in any existing output file. Implies `--refresh`
  -P, --upgrade-package <UPGRADE_PACKAGE>  Allow upgrades for a specific package, ignoring pinned versions in any existing output file. Implies `--refresh-package`
      --resolution <RESOLUTION>            The strategy to use when selecting between the different compatible versions for a given package requirement [env:
                                           UV_RESOLUTION=] [possible values: highest, lowest, lowest-direct]
      --prerelease <PRERELEASE>            The strategy to use when considering pre-release versions [env: UV_PRERELEASE=] [possible values: disallow, allow,
                                           if-necessary, explicit, if-necessary-or-explicit]
      --fork-strategy <FORK_STRATEGY>      The strategy to use when selecting multiple versions of a given package across Python versions and platforms [env:
                                           UV_FORK_STRATEGY=] [possible values: fewest, requires-python]
      --exclude-newer <EXCLUDE_NEWER>      Limit candidate packages to those that were uploaded prior to the given date [env: UV_EXCLUDE_NEWER=]
      --no-sources                         Ignore the `tool.uv.sources` table when resolving dependencies. Used to lock against the standards-compliant,
                                           publishable package metadata, as opposed to using any workspace, Git, URL, or local path sources

Installer options:
      --reinstall                              Reinstall all packages, regardless of whether they're already installed. Implies `--refresh`
      --reinstall-package <REINSTALL_PACKAGE>  Reinstall a specific package, regardless of whether it's already installed. Implies `--refresh-package`
      --link-mode <LINK_MODE>                  The method to use when installing packages from the global cache [env: UV_LINK_MODE=] [possible values: clone, copy,
                                               hardlink, symlink]
      --compile-bytecode                       Compile Python files to bytecode after installation [env: UV_COMPILE_BYTECODE=]

Build options:
  -C, --config-setting <CONFIG_SETTING>                          Settings to pass to the PEP 517 build backend, specified as `KEY=VALUE` pairs
      --no-build-isolation                                       Disable isolation when building source distributions [env: UV_NO_BUILD_ISOLATION=]
      --no-build-isolation-package <NO_BUILD_ISOLATION_PACKAGE>  Disable isolation when building source distributions for a specific package
      --no-build                                                 Don't build source distributions [env: UV_NO_BUILD=]
      --no-build-package <NO_BUILD_PACKAGE>                      Don't build source distributions for a specific package [env: UV_NO_BUILD_PACKAGE=]
      --no-binary                                                Don't install pre-built wheels [env: UV_NO_BINARY=]
      --no-binary-package <NO_BINARY_PACKAGE>                    Don't install pre-built wheels for a specific package [env: UV_NO_BINARY_PACKAGE=]

Cache options:
  -n, --no-cache                           Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                                           UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>              Path to the cache directory [env: UV_CACHE_DIR=]
      --refresh                            Refresh all cached data
      --refresh-package <REFRESH_PACKAGE>  Refresh cached data for a specific package

Python options:
  -p, --python <PYTHON>      The Python interpreter to use for the project environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help sync` for more details.


## More detailed list of options for the uv python command:
Manage Python versions and installations

Usage: uv python [OPTIONS] <COMMAND>

Commands:
  list       List the available Python installations
  install    Download and install Python versions
  find       Search for a Python installation
  pin        Pin to a specific Python version
  dir        Show the uv Python installation directory
  uninstall  Uninstall Python versions

Cache options:
  -n, --no-cache               Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                               UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>  Path to the cache directory [env: UV_CACHE_DIR=]

Python options:
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help python` for more details.


## More detailed list of options for the uv pip command:
Manage Python packages with a pip-compatible interface

Usage: uv pip [OPTIONS] <COMMAND>

Commands:
  compile    Compile a `requirements.in` file to a `requirements.txt` or `pylock.toml` file
  sync       Sync an environment with a `requirements.txt` or `pylock.toml` file
  install    Install packages into an environment
  uninstall  Uninstall packages from an environment
  freeze     List, in requirements format, packages installed in an environment
  list       List, in tabular format, packages installed in an environment
  show       Show information about one or more installed packages
  tree       Display the dependency tree for an environment
  check      Verify installed packages have compatible dependencies

Cache options:
  -n, --no-cache               Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                               UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>  Path to the cache directory [env: UV_CACHE_DIR=]

Python options:
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help pip` for more details.



## More detailed list of options for uv build command:
Build Python packages into source distributions and wheels

Usage: uv build [OPTIONS] [SRC]

Arguments:
  [SRC]  The directory from which distributions should be built, or a source distribution archive to build into a wheel

Options:
      --package <PACKAGE>                      Build a specific package in the workspace
      --all-packages                           Builds all packages in the workspace
  -o, --out-dir <OUT_DIR>                      The output directory to which distributions should be written
      --sdist                                  Build a source distribution ("sdist") from the given directory
      --wheel                                  Build a binary distribution ("wheel") from the given directory
      --no-build-logs                          Hide logs from the build backend
      --force-pep517                           Always build through PEP 517, don't use the fast path for the uv build backend
  -b, --build-constraints <BUILD_CONSTRAINTS>  Constrain build dependencies using the given requirements files when building distributions [env:
                                               UV_BUILD_CONSTRAINT=]
      --require-hashes                         Require a matching hash for each requirement [env: UV_REQUIRE_HASHES=]
      --no-verify-hashes                       Disable validation of hashes in the requirements file [env: UV_NO_VERIFY_HASHES=]

Python options:
  -p, --python <PYTHON>      The Python interpreter to use for the build environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Index options:
      --index <INDEX>                        The URLs to use when resolving dependencies, in addition to the default index [env: UV_INDEX=]
      --default-index <DEFAULT_INDEX>        The URL of the default package index (by default: <https://pypi.org/simple>) [env: UV_DEFAULT_INDEX=]
  -i, --index-url <INDEX_URL>                (Deprecated: use `--default-index` instead) The URL of the Python package index (by default:
                                             <https://pypi.org/simple>) [env: UV_INDEX_URL=]
      --extra-index-url <EXTRA_INDEX_URL>    (Deprecated: use `--index` instead) Extra URLs of package indexes to use, in addition to `--index-url` [env:
                                             UV_EXTRA_INDEX_URL=]
  -f, --find-links <FIND_LINKS>              Locations to search for candidate distributions, in addition to those found in the registry indexes [env:
                                             UV_FIND_LINKS=]
      --no-index                             Ignore the registry index (e.g., PyPI), instead relying on direct URL dependencies and those provided via
                                             `--find-links`
      --index-strategy <INDEX_STRATEGY>      The strategy to use when resolving against multiple index URLs [env: UV_INDEX_STRATEGY=] [possible values:
                                             first-index, unsafe-first-match, unsafe-best-match]
      --keyring-provider <KEYRING_PROVIDER>  Attempt to use `keyring` for authentication for index URLs [env: UV_KEYRING_PROVIDER=] [possible values: disabled,
                                             subprocess]

Resolver options:
  -U, --upgrade                            Allow package upgrades, ignoring pinned versions in any existing output file. Implies `--refresh`
  -P, --upgrade-package <UPGRADE_PACKAGE>  Allow upgrades for a specific package, ignoring pinned versions in any existing output file. Implies `--refresh-package`
      --resolution <RESOLUTION>            The strategy to use when selecting between the different compatible versions for a given package requirement [env:
                                           UV_RESOLUTION=] [possible values: highest, lowest, lowest-direct]
      --prerelease <PRERELEASE>            The strategy to use when considering pre-release versions [env: UV_PRERELEASE=] [possible values: disallow, allow,
                                           if-necessary, explicit, if-necessary-or-explicit]
      --fork-strategy <FORK_STRATEGY>      The strategy to use when selecting multiple versions of a given package across Python versions and platforms [env:
                                           UV_FORK_STRATEGY=] [possible values: fewest, requires-python]
      --exclude-newer <EXCLUDE_NEWER>      Limit candidate packages to those that were uploaded prior to the given date [env: UV_EXCLUDE_NEWER=]
      --no-sources                         Ignore the `tool.uv.sources` table when resolving dependencies. Used to lock against the standards-compliant,
                                           publishable package metadata, as opposed to using any workspace, Git, URL, or local path sources

Build options:
  -C, --config-setting <CONFIG_SETTING>                          Settings to pass to the PEP 517 build backend, specified as `KEY=VALUE` pairs
      --no-build-isolation                                       Disable isolation when building source distributions [env: UV_NO_BUILD_ISOLATION=]
      --no-build-isolation-package <NO_BUILD_ISOLATION_PACKAGE>  Disable isolation when building source distributions for a specific package
      --no-build                                                 Don't build source distributions [env: UV_NO_BUILD=]
      --no-build-package <NO_BUILD_PACKAGE>                      Don't build source distributions for a specific package [env: UV_NO_BUILD_PACKAGE=]
      --no-binary                                                Don't install pre-built wheels [env: UV_NO_BINARY=]
      --no-binary-package <NO_BINARY_PACKAGE>                    Don't install pre-built wheels for a specific package [env: UV_NO_BINARY_PACKAGE=]

Installer options:
      --link-mode <LINK_MODE>  The method to use when installing packages from the global cache [env: UV_LINK_MODE=] [possible values: clone, copy, hardlink,
                               symlink]

Cache options:
  -n, --no-cache                           Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                                           UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>              Path to the cache directory [env: UV_CACHE_DIR=]
      --refresh                            Refresh all cached data
      --refresh-package <REFRESH_PACKAGE>  Refresh cached data for a specific package

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help build` for more details.


## More detailed list of options for the uv run command:
Run a command or script

Usage: uv run [OPTIONS] [COMMAND]

Options:
      --extra <EXTRA>                          Include optional dependencies from the specified extra name
      --all-extras                             Include all optional dependencies
      --no-extra <NO_EXTRA>                    Exclude the specified optional dependencies, if `--all-extras` is supplied
      --no-dev                                 Disable the development dependency group
      --group <GROUP>                          Include dependencies from the specified dependency group
      --no-group <NO_GROUP>                    Disable the specified dependency group
      --no-default-groups                      Ignore the default dependency groups
      --only-group <ONLY_GROUP>                Only include dependencies from the specified dependency group
      --all-groups                             Include dependencies from all dependency groups
  -m, --module                                 Run a Python module
      --only-dev                               Only include the development dependency group
      --no-editable                            Install any editable dependencies, including the project and any workspace members, as non-editable [env:
                                               UV_NO_EDITABLE=]
      --exact                                  Perform an exact sync, removing extraneous packages
      --env-file <ENV_FILE>                    Load environment variables from a `.env` file [env: UV_ENV_FILE=]
      --no-env-file                            Avoid reading environment variables from a `.env` file [env: UV_NO_ENV_FILE=]
      --with <WITH>                            Run with the given packages installed
      --with-editable <WITH_EDITABLE>          Run with the given packages installed in editable mode
      --with-requirements <WITH_REQUIREMENTS>  Run with all packages listed in the given `requirements.txt` files
      --isolated                               Run the command in an isolated virtual environment
      --active                                 Prefer the active virtual environment over the project's virtual environment
      --no-sync                                Avoid syncing the virtual environment [env: UV_NO_SYNC=]
      --locked                                 Assert that the `uv.lock` will remain unchanged [env: UV_LOCKED=]
      --frozen                                 Run without updating the `uv.lock` file [env: UV_FROZEN=]
  -s, --script                                 Run the given path as a Python script
      --gui-script                             Run the given path as a Python GUI script
      --all-packages                           Run the command with all workspace members installed
      --package <PACKAGE>                      Run the command in a specific package in the workspace
      --no-project                             Avoid discovering the project or workspace

Index options:
      --index <INDEX>                        The URLs to use when resolving dependencies, in addition to the default index [env: UV_INDEX=]
      --default-index <DEFAULT_INDEX>        The URL of the default package index (by default: <https://pypi.org/simple>) [env: UV_DEFAULT_INDEX=]
  -i, --index-url <INDEX_URL>                (Deprecated: use `--default-index` instead) The URL of the Python package index (by default:
                                             <https://pypi.org/simple>) [env: UV_INDEX_URL=]
      --extra-index-url <EXTRA_INDEX_URL>    (Deprecated: use `--index` instead) Extra URLs of package indexes to use, in addition to `--index-url` [env:
                                             UV_EXTRA_INDEX_URL=]
  -f, --find-links <FIND_LINKS>              Locations to search for candidate distributions, in addition to those found in the registry indexes [env:
                                             UV_FIND_LINKS=]
      --no-index                             Ignore the registry index (e.g., PyPI), instead relying on direct URL dependencies and those provided via
                                             `--find-links`
      --index-strategy <INDEX_STRATEGY>      The strategy to use when resolving against multiple index URLs [env: UV_INDEX_STRATEGY=] [possible values:
                                             first-index, unsafe-first-match, unsafe-best-match]
      --keyring-provider <KEYRING_PROVIDER>  Attempt to use `keyring` for authentication for index URLs [env: UV_KEYRING_PROVIDER=] [possible values: disabled,
                                             subprocess]

Resolver options:
  -U, --upgrade                            Allow package upgrades, ignoring pinned versions in any existing output file. Implies `--refresh`
  -P, --upgrade-package <UPGRADE_PACKAGE>  Allow upgrades for a specific package, ignoring pinned versions in any existing output file. Implies `--refresh-package`
      --resolution <RESOLUTION>            The strategy to use when selecting between the different compatible versions for a given package requirement [env:
                                           UV_RESOLUTION=] [possible values: highest, lowest, lowest-direct]
      --prerelease <PRERELEASE>            The strategy to use when considering pre-release versions [env: UV_PRERELEASE=] [possible values: disallow, allow,
                                           if-necessary, explicit, if-necessary-or-explicit]
      --fork-strategy <FORK_STRATEGY>      The strategy to use when selecting multiple versions of a given package across Python versions and platforms [env:
                                           UV_FORK_STRATEGY=] [possible values: fewest, requires-python]
      --exclude-newer <EXCLUDE_NEWER>      Limit candidate packages to those that were uploaded prior to the given date [env: UV_EXCLUDE_NEWER=]
      --no-sources                         Ignore the `tool.uv.sources` table when resolving dependencies. Used to lock against the standards-compliant,
                                           publishable package metadata, as opposed to using any workspace, Git, URL, or local path sources

Installer options:
      --reinstall                              Reinstall all packages, regardless of whether they're already installed. Implies `--refresh`
      --reinstall-package <REINSTALL_PACKAGE>  Reinstall a specific package, regardless of whether it's already installed. Implies `--refresh-package`
      --link-mode <LINK_MODE>                  The method to use when installing packages from the global cache [env: UV_LINK_MODE=] [possible values: clone, copy,
                                               hardlink, symlink]
      --compile-bytecode                       Compile Python files to bytecode after installation [env: UV_COMPILE_BYTECODE=]

Build options:
  -C, --config-setting <CONFIG_SETTING>                          Settings to pass to the PEP 517 build backend, specified as `KEY=VALUE` pairs
      --no-build-isolation                                       Disable isolation when building source distributions [env: UV_NO_BUILD_ISOLATION=]
      --no-build-isolation-package <NO_BUILD_ISOLATION_PACKAGE>  Disable isolation when building source distributions for a specific package
      --no-build                                                 Don't build source distributions [env: UV_NO_BUILD=]
      --no-build-package <NO_BUILD_PACKAGE>                      Don't build source distributions for a specific package [env: UV_NO_BUILD_PACKAGE=]
      --no-binary                                                Don't install pre-built wheels [env: UV_NO_BINARY=]
      --no-binary-package <NO_BINARY_PACKAGE>                    Don't install pre-built wheels for a specific package [env: UV_NO_BINARY_PACKAGE=]

Cache options:
  -n, --no-cache                           Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                                           UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>              Path to the cache directory [env: UV_CACHE_DIR=]
      --refresh                            Refresh all cached data
      --refresh-package <REFRESH_PACKAGE>  Refresh cached data for a specific package

Python options:
  -p, --python <PYTHON>      The Python interpreter to use for the run environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help run` for more details.


## Examples Of Development Commands

### Environment Setup
# Python environment (using uv)
uv venv
source .venv/bin/activate  # Linux/macOS
.venv_windows\Scripts\activate     # Windows
uv sync --all-extras       # Install all dependencies

# Node.js dependencies
uv run pnpm install

### Running the Application

# Full stack (frontend + backend) example
uv run pnpm run start-project            # macOS/Linux
uv run pnpm run start-project:win        # Windows
uv run pnpm run start-project:debug      # Debug mode

# Backend only example
uv run python3 main.py                    # or: python main.py on Windows
uv run python3 main.py --log-level debug  # Debug mode

----------------------------------------

TITLE: Creating Virtual Environment with Specific Python Version using uv (Console)
DESCRIPTION: Creates a virtual environment using a specific Python version (e.g., 3.11) with the `uv` tool. Requires the requested Python version to be available or downloadable by uv.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/environments.md#_snippet_2

LANGUAGE: console
CODE:

$ uv venv --python 3.11


----------------------------------------

TITLE: Creating a Virtual Environment with uv
DESCRIPTION: This command creates a new virtual environment in the current directory using `uv venv`. It automatically detects the appropriate Python version and provides instructions for activating the environment.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_14

LANGUAGE: console
CODE:

$ uv venv
Using Python 3.12.3
Creating virtual environment at: .venv
Activate with: source .venv/bin/activate

------------------------------------------

## Managed and system Python installations with uv
Since it is common for a system to have an existing Python installation, uv supports discovering Python versions. However, uv also supports installing Python versions itself. To distinguish between these two types of Python installations, uv refers to Python versions it installs as managed Python installations and all other Python installations as system Python installations.

Note
uv does not distinguish between Python versions installed by the operating system vs those installed and managed by other tools. For example, if a Python installation is managed with pyenv, it would still be considered a system Python version in uv.


## Requesting a version
A specific Python version can be requested with the --python flag in most uv commands. For example, when creating a virtual environment:


$ uv venv --python 3.11.6

uv will ensure that Python 3.11.6 is available — downloading and installing it if necessary — then create the virtual environment with it.
The following Python version request formats are supported:

	•	<version> (e.g., 3, 3.12, 3.12.3)
	•	<version-specifier> (e.g., >=3.12,<3.13)
	•	<implementation> (e.g., cpython or cp)
	•	<implementation>@<version> (e.g., cpython@3.12)
	•	<implementation><version> (e.g., cpython3.12 or cp312)
	•	<implementation><version-specifier> (e.g., cpython>=3.12,<3.13)
	•	<implementation>-<version>-<os>-<arch>-<libc> (e.g., cpython-3.12.3-macos-aarch64-none)

Additionally, a specific system Python interpreter can be requested with:

	•	<executable-path> (e.g., /opt/homebrew/bin/python3)
	•	<executable-name> (e.g., mypython3)
	•	<install-dir> (e.g., /some/environment/)

By default, uv will automatically download Python versions if they cannot be found on the system. This behavior can be disabled with the python-downloads option.


## Python version files
The .python-version file can be used to create a default Python version request. uv searches for a .python-version file in the working directory and each of its parents. If none is found, uv will check the user-level configuration directory. Any of the request formats described above can be used, though use of a version number is recommended for interoperability with other tools.
A .python-version file can be created in the current directory with the uv python pin command:

## Change to use a specific Python version in the current directory

$ uv python pin 3.11

Pinned `.python-version` to `3.11`


A global .python-version file can be created in the user configuration directory with the uv python pin --global command. (not reccomended)

## Discovery of .python-version files can be disabled with --no-config.
uv will not search for .python-version files beyond project or workspace boundaries (with the exception of the user configuration directory).

## Installing a Python version
uv bundles a list of downloadable CPython and PyPy distributions for macOS, Linux, and Windows.

Tip
By default, Python versions are automatically downloaded as needed without using uv python install.

To install a Python version at a specific version:


$ uv python install 3.12.3

To install the latest patch version:


$ uv python install 3.12

To install a version that satisfies constraints:


$ uv python install '>=3.8,<3.10'

To install multiple versions:


$ uv python install 3.9 3.10 3.11

To install a specific implementation:


$ uv python install pypy

All of the Python version request formats are supported except those that are used for requesting local interpreters such as a file path.
By default uv python install will verify that a managed Python version is installed or install the latest version. If a .python-version file is present, uv will install the Python version listed in the file. A project that requires multiple Python versions may define a .python-versions file. If present, uv will install all of the Python versions listed in the file.

Important:
The available Python versions are frozen for each uv release. To install new Python versions, you may need upgrade uv.

## Installing Python executables

To install Python executables into your PATH, provide the --preview option:


$ uv python install 3.12 --preview
This will install a Python executable for the requested version into ~/.local/bin, e.g., as python3.12.

Tip
If ~/.local/bin is not in your PATH, you can add it with uv tool update-shell.

To install python and python3 executables, include the --default option:


$ uv python install 3.12 --default --preview

When installing Python executables, uv will only overwrite an existing executable if it is managed by uv — e.g., if ~/.local/bin/python3.12 exists already uv will not overwrite it without the --force flag.
uv will update executables that it manages. However, it will prefer the latest patch version of each Python minor version by default. For example:


$ uv python install 3.12.7 --preview  # Adds `python3.12` to `~/.local/bin`

$ uv python install 3.12.6 --preview  # Does not update `python3.12`

$ uv python install 3.12.8 --preview  # Updates `python3.12` to point to 3.12.8

## Project Python versions
uv will respect Python requirements defined in requires-python in the pyproject.toml file during project command invocations. The first Python version that is compatible with the requirement will be used, unless a version is otherwise requested, e.g., via a .python-version file or the --python flag.

## Viewing available Python versions
To list installed and available Python versions:


$ uv python list

To filter the Python versions, provide a request, e.g., to show all Python 3.13 interpreters:


$ uv python list 3.13

Or, to show all PyPy interpreters:


$ uv python list pypy

By default, downloads for other platforms and old patch versions are hidden.
To view all versions:


$ uv python list --all-versions

To view Python versions for other platforms:


$ uv python list --all-platforms

To exclude downloads and only show installed Python versions:


$ uv python list --only-installed

See the uv python list reference for more details.

## Finding a Python executable
To find a Python executable, use the uv python find command:

$ uv python find

By default, this will display the path to the first available Python executable. See the discovery rules for details about how executables are discovered.

This interface also supports many request formats, e.g., to find a Python executable that has a version of 3.11 or newer:

$ uv python find '>=3.11'

By default, uv python find will include Python versions from virtual environments. If a .venv directory is found in the working directory or any of the parent directories or the VIRTUAL_ENV environment variable is set, it will take precedence over any Python executables on the PATH.
To ignore virtual environments, use the --system flag:

$ uv python find --system

But it is not reccomended.

## Discovery of Python versions
When searching for a Python version, the following locations are checked:
	•	Managed Python installations in the UV_PYTHON_INSTALL_DIR.
	•	A Python interpreter on the PATH as python, python3, or python3.x on macOS and Linux, or python.exe on Windows.
	•	On Windows, the Python interpreters in the Windows registry and Microsoft Store Python interpreters (see py --list-paths) that match the requested version.

In some cases, uv allows using a Python version from a virtual environment. In this case, the virtual environment's interpreter will be checked for compatibility with the request before searching for an installation as described above. See the pip-compatible virtual environment discovery documentation for details.
When performing discovery, non-executable files will be ignored. Each discovered executable is queried for metadata to ensure it meets the requested Python version. If the query fails, the executable will be skipped. If the executable satisfies the request, it is used without inspecting additional executables.
When searching for a managed Python version, uv will prefer newer versions first. When searching for a system Python version, uv will use the first compatible version — not the newest version.
If a Python version cannot be found on the system, uv will check for a compatible managed Python version download.

## EXAMPLE OF INSTALLING A VERSION OF PYTHON AND CHANGING IT LATER WITH PIN:

## Install multiple Python versions:


$ uv python install 3.10 3.11 3.12

Searching for Python versions matching: Python 3.10

Searching for Python versions matching: Python 3.11

Searching for Python versions matching: Python 3.12

Installed 3 versions in 3.42s

 + cpython-3.10.14-macos-aarch64-none

 + cpython-3.11.9-macos-aarch64-none

 + cpython-3.12.4-macos-aarch64-none


## Download Python versions as needed:


$ uv venv --python 3.12.0

Using CPython 3.12.0

Creating virtual environment at: .venv

Activate with: source .venv/bin/activate


$ uv run --python pypy@3.8 -- python

Python 3.8.16 (a9dbdca6fc3286b0addd2240f11d97d8e8de187a, Dec 29 2022, 11:45:30)

[PyPy 7.3.11 with GCC Apple LLVM 13.1.6 (clang-1316.0.21.2.5)] on darwin

Type "help", "copyright", "credits" or "license" for more information.


## Change to use a specific Python version in the current directory:


$ uv python pin 3.11

Pinned `.python-version` to `3.11`


------------------------------------------



## Project Architecture

### EnChANT Book Manager
A comprehensive Chinese novel translation and EPUB generation system with three main phases:

1. **Phase 1 - Renaming**: Extract metadata from Chinese filenames and rename to English
   - Module: `renamenovels.py`
   - Uses AI to extract title/author from Chinese filenames

2. **Phase 2 - Translation**: Translate Chinese text to English with chunking
   - Module: `cli_translator.py`
   - Chunk-based translation with retry mechanism
   - Cost tracking for API usage
   - Supports multiple translation services

3. **Phase 3 - EPUB Generation**: Create English EPUB with proper TOC
   - Module: `make_epub.py`
   - Detects English chapter patterns
   - Validates chapter sequences
   - Supports customization (CSS, language, metadata)

### Key Design Principles
- **Orchestration**: `enchant_cli.py` is the sole orchestrator coordinating all phases
- **Separation of Concerns**: Each module handles specific functionality
- **Library Behavior**: No user prompts in library code (only in CLI main)
- **Error Handling**: Comprehensive retry mechanism with exponential backoff
- **Configuration**: YAML-based configuration (`enchant_config.yml`)
- **Extensibility**: Easy to add new translation services or output formats

### Recent Improvements
- **EPUB Generation**:
  - Added support for custom CSS, language settings, and metadata
  - Improved chapter detection for various English patterns
  - XML generation using ElementTree for proper escaping
  - Created `epub_utils.py` for common EPUB utilities

- **Testing**:
  - Converted pytest tests to unittest for consistency
  - Added comprehensive test coverage (92.6% pass rate)
  - Formatted test output with descriptions and status indicators

- **Code Quality**:
  - Proper type annotations throughout
  - Docstrings for all functions
  - Small, focused modules under 10KB each

### Dependencies
- Core tools: pytest, pytest-cov, pytest-mock, mypy, ruff, flake8, pre-commit, yamllint, actionlint, prefect, shellcheck, gh
- Package management: UV (modern Python package manager)
- Version management: bump-my-version, gitpython, gitleaks
- UI/CLI: click, rich
- Frontend/Nodejs: pnpm, eslint
- AI/ML libraries: openai, litellm, google-generativeai (for certain features)



### Pytest Timeout Configuration

pytest-timeout prevents tests from hanging indefinitely.

# Installation (already included in dev dependencies)
uv add pytest-timeout --dev

# Usage
Run the test suite with a global timeout in seconds:
pytest --timeout=300

# Per-test timeout using decorator
@pytest.mark.timeout(60)
def test_foo():
    pass

# Configuration priority (from low to high):
1. Global timeout in pytest.ini:
   [pytest]
   timeout = 300
2. PYTEST_TIMEOUT environment variable
3. --timeout command line option
4. @pytest.mark.timeout() decorator on individual tests

# Disable timeout for specific test
@pytest.mark.timeout(0)
def test_long_running():
    pass
EOF < /dev/null
