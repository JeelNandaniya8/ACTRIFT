# htmx invalid-target Ajax regression

Fixed: https://github.com/bigskysoftware/htmx/commit/b98e4f2b12096c216e799b10b0aff1fe9c7a923d

Buggy parent: df92b295d6b91291ecef97733ba135ac5de565a5. Original src/htmx.js files and each revision's Zero-Clause BSD license are preserved. A separate synthetic integration fixture exercises the documented invalid-target fallback. This is not production traffic.
