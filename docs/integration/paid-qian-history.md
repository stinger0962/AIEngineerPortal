# Qian saved-reading history

The previous workspace listed recent signs but could not reopen their saved
answers, even though its failure message recommended checking history before
retrying. This change connects the existing owner-protected detail endpoint to
an inline, read-only history view.

- History initially shows five records and can expand the server's newest 50.
- Select a record to read its full saved question and answer; the current question
  draft and live reading are not replaced. Close the detail to return.
- No generation, speech, credit mutation or provider request is triggered by
  viewing history. Content renders as text, not executable markup.
- Loading, unavailable records and failures are explicit. Refresh the list or
  retry a detail deliberately; failed loads are not presented as empty history.
- New selections, closing and unmount cancel prior reads and reject stale results.
- Existing paid session and owner checks apply. A missing, other-account or
  unowned legacy record is not exposed; session expiry returns to the account gate.

A saved answer may be partial after provider interruption. The data model does
not record a completion status, so the history view does not claim successful
completion or payment/refund state. Inspect saved content before deciding to
retry a failed reading. No migration, pricing or entitlement policy is added.

Tests use synthetic records and mocked browser traffic. Real provider services,
production data and deployment remain untouched.
