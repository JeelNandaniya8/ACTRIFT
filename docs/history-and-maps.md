# Local history and source maps

```sh
ghostdiff history-record report/evidence.json --db history.db --project demo --revision v1
ghostdiff history-show --db history.db --project demo
ghostdiff localize report/evidence.json --repo ./app --good GOOD_SHA --bad BAD_SHA --source-maps maps.json
```

SQLite stores revision labels, scoped hashes, counts and insertion timestamps, not original page content. Use a dedicated trusted local database. Revisions cannot be silently overwritten; distinct scopes remain incomparable.

Source-map manifest format: `{"schema":"ghostdiff.source-maps/v1","maps":{"/bundle.js":"bundle.js.map"}}`. Supply trusted maps from the exact candidate build. Ordinary version 3 VLQ segments are decoded offline, mapping generated one-based browser line/column coordinates to original segment coordinates. No remote fetch or sourcesContent export. Relative source paths only; indexed maps, external URLs, bundler-specific virtual paths and deployment verification are unsupported. Mapped source coordinates improve changed-hunk ranking but are not proof of causation.
