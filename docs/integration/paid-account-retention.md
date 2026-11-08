# Paid account retention tooling (not scheduled or activated)

This is maintenance for the **new paid product's authentication material**, not
account erasure, billing cleanup or personal-portal migration. No production job
or schedule is installed. No real records were deleted to develop or test it.

## Existing expiry policy

| Material | Validity | Cleanup eligibility |
| --- | --- | --- |
| Session token hash | 30 days after issue; sign-in/revocation can end it earlier | At or after its stored expiration |
| Rate-limit bucket | Stored expiry is the UTC hourly bucket start plus 2 hours | At or after its stored expiration |
| Email challenge | 15 minutes, single use | At or after stored expiration plus 24 hours, whether consumed or unused |

The extra challenge day supports operational diagnosis. The tool reports counts,
not email addresses, codes, tokens or row contents. It does not shorten active
sessions, reset live rate limits, or remove a challenge before the grace period.
It does not delete accounts, verified-email bindings, profiles, readings,
conversations, ownership records, orders or credit ledger entries. This is not a
complete personal-data retention or customer deletion policy.

## Inspect first

From the repository root, show help without connecting to any database:

```sh
PYTHONPATH=backend python -m app.cli.paid_retention --help
```

For an already-running **disposable local preview** only:

```sh
docker compose -f compose.paid-local.yml exec -T backend python -m app.cli.paid_retention
```

No flag means dry-run. The command must use an explicit dedicated
`PAID_DATABASE_URL` and a distinct `DATABASE_URL` for the portal boundary. It
never falls back to portal storage and does not load an implicit `.env`, create a
database, seed data or migrate schema. Do not paste database URLs into chat,
command-line arguments or issue comments. Output contains only aggregate counts
and safe operational metadata; failures do not echo connection details.

The preview database is temporary and usually has nothing to clean. An empty
result is expected, not evidence that a production retention schedule exists.

## Controlled cleanup

Application requires both `--apply` and a positive `--max-delete N` total-row
budget. Neither flag is implied by a prior dry-run. Review a
fresh dry-run, verify the database identity and backup/recovery policy, and obtain
any required authorization **before** executing against real data. The CLI's
flags are mechanical safeguards, not user approval. Tests exercise apply only on
disposable fixtures. Do not schedule this command or run it on a production host
as part of this milestone.

A run uses one UTC cutoff. It should fail closed on unsupported or unrelated
schemas, portal aliases, missing storage or a deletion count above the explicit
budget. Pre-commit failures roll back the transaction. A connection failure during commit
can have an uncertain outcome: inspect current counts and database state before
retrying, rather than assuming nothing changed. Repeating cleanup after a
confirmed successful run should produce zero eligible rows unless new material
expired.
No raw exception or per-record data should be copied to logs while investigating
failures.

## Future operations decision

Before enabling a recurring job, choose the authorized target, cadence, deletion
budget, alert destination and backup/restore expectations. Monitor successful
runs and errors using aggregate counts. Separate application health from
retention health: this PR does not claim monitoring, future notifications or a
production schedule is in place. PostgreSQL and SQLite behavior must both be
validated for whichever engine will actually be deployed.
