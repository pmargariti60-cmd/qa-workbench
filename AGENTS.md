# AI contributor instructions

Read `README.md` and `MANIFESTO.md` before working on the project. Treat the bundled candidate's three seeded defects as part of the demo.

Use MCP run records when asked to triage. Cite a run ID, environment, failed check, and evidence link. Separate observations from theories. Keep report drafting read-only unless asked to change project files.

For app changes, run `python -m unittest discover -s tests -v` with port 8765 free. Local profiles and run data are ignored by Git.
