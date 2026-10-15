# Preserved first full clean-checkout failure

Revision `90d27b7a4ad2aee29059611e00ee8583bd811e76` began from a detached initially clean checkout, with uv/npm offline. Setup, data regeneration,102 Python tests/frontend checks and framework playback passed. The actual full playback executed all900 cases before strict aggregation rejected a failed-leg `effective_seed` mismatch. No successful reproduction is claimed.

[The command records](../clean-20261015T045621Z/failed.json) bind every exit code and log. [The semantic diagnostic](semantic-mismatch.json) compares all900 actual case records:210 cases differ only in272 failed-leg `effective_seed` fields, historical profile seeds versus null. It does not drop those fields or declare the comparison matched.

[The archive inventory](failed-reproduction-archive.json) binds every one of the59,141 generated files and a46,714,894-byte [complete archive](failed-reproduction-20261015T051521Z.tar.gz). Every archive member was read back and checked against its original bytes. Its paths are rooted under artifacts/reproductions/20261015T051521Z; extract into an empty inspection directory, never over another campaign. `archive.py` records the executed preservation operation. The original failed worktree remains retained too.

After the final comparison exception, the child retained30.9GB in Python module-finalization garbage collection. [The one-second stack sample](shutdown-sample.txt) and [precise owned-process termination record](cleanup-termination.json) document why only child86246 was stopped. This allowed make/driver to record actual failure and preserved the worktree. It did not interrupt active comparison work or fabricate a clean exit.

[The separately versioned correction](../../../REPLAY_METADATA.md) attributes historical seed metadata only after complete exact failed playback, keeps the uncorrected leg record and collects unreachable objects between replay legs. The new full clean checkout is a separate run with a different committed revision; nothing here converts this failed run into a success.
