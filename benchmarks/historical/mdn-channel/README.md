# Historical channel messaging error

Original upstream fix: https://github.com/mdn/dom-examples/commit/98c8bb8b20e627161b0cf2cc17a1fccd2258f79b
Buggy parent: 36eba9f807f24dab86745e7b1634c97865ec2594. The original page2.html files are stored unchanged under the upstream license. The separate test harness loads the iframe and sends a message without transferring a MessagePort. The fixed version ignores this message; the original handler attempts to dereference e.ports[0]. This is a documented example defect, not a production application benchmark.
