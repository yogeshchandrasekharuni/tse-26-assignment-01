# Actual UI replay and downloads

The real browser clicked Replay captured run on Full synthetic feed. The queue completed job 089a1e6a781449788bd0d253f96894bf with nine recorded decisions and zero network attempts. Its canonical output matches the original saved live analysis. The UI visibly labels the result Offline replay.

Money display was changed to USD thousands and area to m². Both CSV and JSON were downloaded through their visible browser links and copied verbatim into this packet. All twelve CSV canonical rows agree with the strict typed JSON and original capture. The final displayed CSV values are 357.060500 USD thousands and 2.147715 USD thousands/m². The browser screenshot shows the corresponding rounded values 357.1k and 2.15k, with 1,440 observations.

The preserved terminal/request and exported output make this one-run verification reviewable without the ignored web runtime directory. [verification.json](verification.json) binds the actual files. This does not substitute for full 900 clean-checkout playback.
