# Publish and demonstrate the workbench

1. Extract the ZIP and open the folder containing `README.md` in local Codex. Keep the hidden `.github` directory.
2. Follow the README to run both demo profiles and confirm the results. Try the [Codex MCP workflow](codex.md).
3. Install GitHub CLI if needed. In the workbench folder, sign in with `gh auth login --hostname github.com --git-protocol https --web` and verify the owner with `gh auth status`. [GitHub CLI authentication](https://cli.github.com/manual/gh_auth_login)
4. Create and publish the repo. Choose the visibility you want before running the final command.

```sh
git init -b main
git add .
git diff --cached --stat
git commit -m "Add QA Workbench portfolio project"
gh repo create qa-workbench --public --source=. --remote=origin --push
```

Use `--private` for a private repo. Check **Actions → Workbench integration** after pushing. [GitHub CLI repository creation](https://cli.github.com/manual/gh_repo_create)

## Interview walkthrough

Run the reference, switch to the candidate, and open the discount failure. Explain why using the same check on both builds helps identify a regression. Show the screenshot, then ask Codex to draft a report from the stored result. Explain how you verified the AI draft, what the evidence supports, and what you would retest.
