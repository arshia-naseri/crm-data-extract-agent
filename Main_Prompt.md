Step 1: Determine batch numbers.

Run this shell command to get the last git commit message:

```
git log -1 --pretty=%s
```

If the message matches the pattern `Batch X,Y,Z,W Done` (where X,Y,Z,W are numbers), extract the highest number and compute the next 4 batch numbers starting from (highest + 1). Cap at 68 — do not exceed 68. If fewer than 4 remain, only use those that remain.

If the message does NOT match that pattern, start from batch numbers 1, 2, 3, 4.

Store the list of batch numbers. Example: if last commit says "Batch 1,2,3,4 Done", the list is [5, 6, 7, 8].

If the highest number from the last commit is already 68 or higher, there are no batches left. Print "All 68 batches complete." and stop.

SELF-CHECK before proceeding:
- Print the extracted commit message.
- Print the computed batch list.
- Confirm every number in the list is between 1 and 68 inclusive.
- Confirm the list has no duplicates.
- Confirm none of these batches appear in any previous "Batch ... Done" commit (run `git log --oneline --grep="Batch" | head -20` to verify).
- If any check fails, stop and print the error. Do not proceed.

Step 2: Process each batch.

For each batch number in the list, one at a time in order:

- Spawn `@forge_local` with BATCH_NUM set to that batch number.
- Wait for it to fully complete before starting the next one.
- After each forge completes, verify `tmp/batch_{NUM}_table.csv` exists.
- If a forge fails or the CSV is missing, log the error and continue to the next batch. Do not retry.

RULES:
- Only use `@forge_local`. Never spawn `@miner_local` directly — forge_local handles that.
- Do not modify any files in `client_info/`, `batch/`, or `.codex/`.
- Do not run more than one forge at a time.
- Process batches in ascending order only.

Step 3: Commit results.

After all batches in the list are processed:

```
git add tmp/
git commit -m "Batch X,Y,Z,W Done"
```

Replace X,Y,Z,W with the actual batch numbers that were successfully processed (CSV exists in tmp/), comma-separated with no spaces. If fewer than 4 were processed, only list the ones that succeeded.

Do not stage or commit any files outside of `tmp/`.
If zero batches succeeded, do not commit. Print "No batches completed successfully." and stop.
