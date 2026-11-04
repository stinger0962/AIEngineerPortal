# Public HTTPS diagnostics

Use Actions → Public HTTPS diagnostics → Run workflow → main to check the live
site without building, SSH, configuration changes, or deployment. This workflow
only reads fixed https://portal.leipan.cc/health and https://portal.leipan.cc/.
It retains normal certificate/hostname verification and refuses redirects.

Failures report the fixed endpoint label, safe category, and numeric HTTP status
when available. Bodies, exception strings, redirect targets, and credentials are
never logged. Both endpoints are checked independently each attempt. A failed
probe does not establish whether the cause is application, proxy, DNS, TLS, or
runner connectivity until its category and supporting evidence are reviewed.
Successful checks confirm public reachability and expected content at that time,
not all product features or payment functionality.

This can diagnose the already-deployed release without rerunning production.
It never rolls back automatically. Existing deployment smoke checks use the same
script and still fail closed. No backup requirement is introduced.
