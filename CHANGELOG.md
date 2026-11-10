# Changelog

## 0.1.1 (Nov 9, 2026)
- Cell 1 now pins villa to commit 47a9c37 (47a9c37f6f8e99afdab47bb46ad425aa726f5dc0), tested Nov 9 in a fresh Kaggle copy after villa #2440
- Cell 1 checks the Reader V3 file against SHA-256 ea405417...e984d8a and warns if it differs
- Cell 1 prints a hint if Internet is off in the Kaggle session
- No change to scoring, pass lines or verdicts

## 0.1.0 (Oct 31, 2026)
- First public version, submitted to the October 2026 progress prize
- Verdict from the average of three papyrus numbers (score B), with two floors: any one number below 60% of its pass line fails, and less than half the page inside the readable window fails
- Reading direction fixed before reading (team-published volumes read forward); the forward/reverse ink ratio only adds a warning
- Pass lines: 9.36 um from PHerc0841 w00, ag144, ag174; 8.64 um contrast from PHerc0009B (one segment, first estimate)
- `check_only` mode, `add_segment`, `add_volume`, `add_mesh`, `table()`, `to_check()`
- Ratio values capped at 100
