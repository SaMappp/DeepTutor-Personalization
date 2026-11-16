# Maintenance rules

This is the independent, unofficial public archive `SaMappp/DeepTutor-Personalization`.
Upstream baseline: DeepTutor v1.7.1, commit `f7aed0744c36c5afef16a4261c31ebee1208cac2`.

The maintainer's standing instruction, effective 2026-11-16: after completing and verifying a DeepTutor modification or optimization, synchronize its publishable code, patches, tests and development record to this repository. This includes explicit authorization to commit and push reviewed changes; no routine extra confirmation is needed. Apply this only to DeepTutor work.

Before a sync:
- Verify the actual deployed component; CLI, desktop backend, frontend and desktop shell are separate targets.
- Export only reviewed source files. Update full overrides, reproducible patches, manifest hashes, notices, provenance and the development/validation docs together.
- Preserve upstream attribution and per-file licenses. Never invent historical commits or claim unperformed validation.
- Exclude credentials, personal email addresses, chats, coursework, attachments, learning databases, local cache contents, raw verification snapshots, logs and backups.
- Check the staged diff and commit author/committer identity; use the maintainer's GitHub noreply email for new commits.
- Fetch the remote head, preserve unrelated changes, push without force, then verify the remote SHA and a representative source blob. Do not rewrite old history without explicit approval.
- If checks fail or publication is blocked, preserve a checkpoint and report what remains. Do not mark a sync complete before verifying the remote.

Validation from the repository root:
`python tools/verify_publication.py --upstream <clean-v1.7.1-source>`
`python -m unittest discover -s tests -v`
For context-reuse integration tests, set `DEEPTUTOR_CORE` to a v1.7.1 core with dependencies and run `python tools/check_context_reuse.py`.

State and maintenance entry points: PROJECT_STATE.md, WORK_LOG.md, DECISIONS.md and docs/MAINTAINING.md. Public records must contain no private runtime evidence.
