"""Browser-driven differential experiments. No model or API required."""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Error, sync_playwright


@dataclass(frozen=True, order=True)
class Action:
    role: str
    name: str


@dataclass(frozen=True)
class Settings:
    depth: int = 2
    budget: int = 30
    settle_ms: int = 180
    timeout_ms: int = 2500
    repeats: int = 2
    allow_writes: bool = False
    executable: str | None = None

    def validate(self):
        for name, low, high in (("depth", 1, 5), ("budget", 1, 200),
                                ("settle_ms", 0, 5000), ("timeout_ms", 100, 15000),
                                ("repeats", 2, 5)):
            if type(getattr(self, name)) is not int or not low <= getattr(self, name) <= high:
                raise ValueError(f"{name} must be between {low} and {high}")


def origin(url: str) -> tuple:
    if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise ValueError("URL contains invalid whitespace or control characters")
    u = urlsplit(url)
    if u.scheme not in ("http", "https") or u.username is not None or u.password is not None or not u.hostname:
        raise ValueError("Only HTTP(S) URLs without credentials are supported")
    return (u.scheme, u.hostname, u.port if u.port is not None else (443 if u.scheme == "https" else 80))


def validate_url(url: str):
    if origin(url)[1] not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Only explicit loopback URLs are allowed. Use disposable local test apps.")


def normal(s: str) -> str:
    return " ".join(s.split())


def stable_json(data) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# Playwright's actual accessible-role matcher is the final authority for replay.
DISCOVER = r'''() => {
  const visible = e => { const r=e.getBoundingClientRect(); const s=getComputedStyle(e); return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'; };
  const label = e => { const ids=e.getAttribute('aria-labelledby'); if(ids){const n=ids.split(/\s+/).map(x=>document.getElementById(x)?.innerText||'').join(' ').trim(); if(n)return n;} return e.getAttribute('aria-label') || e.innerText || e.value || e.getAttribute('title') || ''; };
  return [...document.querySelectorAll('button,[role=button],input[type=button],input[type=submit],a[href],[role=link]')].filter(e=>visible(e)&&!e.disabled&&e.getAttribute('aria-disabled')!=='true').map(e=>({role:e.matches('a[href],[role=link]')?'link':'button', name:label(e).replace(/\s+/g,' ').trim()})).filter(a=>a.name&&a.name.length<=120);
}'''


def available(page) -> list[Action]:
    actions = sorted(set(Action(**a) for a in page.evaluate(DISCOVER)))
    return [a for a in actions if page.get_by_role(a.role, name=a.name, exact=True).count() == 1]


def snapshot(page) -> dict:
    raw = page.locator('body').inner_text()
    if len(raw) > 65536:
        raise ValueError("Page text exceeds observation limit (64 Ki characters)")
    lines = sorted(normal(x) for x in raw.splitlines() if normal(x))
    u = urlsplit(page.url)
    return {"route": u.path + ("?" + u.query if u.query else "") + ("#" + u.fragment if u.fragment else ""),
            "text": lines, "actions": [asdict(a) for a in available(page)]}


def delta(before, after, downloads):
    result = {"text_added": sorted((Counter(after['text']) - Counter(before['text'])).elements()),
              "text_removed": sorted((Counter(before['text']) - Counter(after['text'])).elements()),
              "route_change": after['route'] if before['route'] != after['route'] else None,
              "downloads": downloads}
    if "actions" in before and "actions" in after:
        a = {Action(**x) for x in before["actions"]}
        b = {Action(**x) for x in after["actions"]}
        result["actions_added"] = [asdict(x) for x in sorted(b-a)]
        result["actions_removed"] = [asdict(x) for x in sorted(a-b)]
    return result


def has_signal(outcome):
    return any(outcome.get(key) for key in ("text_added", "text_removed", "route_change", "downloads", "actions_added", "actions_removed"))


def validate_path(path, cfg):
    if len(path) > cfg.depth:
        raise ValueError("Journey exceeds configured depth")
    for a in path:
        if a.role not in ("button", "link", "reload") or not isinstance(a.name, str) or not 1 <= len(a.name) <= 120:
            raise ValueError("Unsupported action in journey")


def experiment(browser: Browser, url: str, path: tuple[Action, ...], cfg: Settings) -> dict:
    """Every path starts in a fresh browser context; no real user session is used."""
    validate_path(path, cfg)
    context = browser.new_context(accept_downloads=True, service_workers="block")
    allowed = origin(url)
    blocked = []
    downloads = []
    pages = []
    steps = []

    def gate(route):
        request = route.request
        try:
            ok = origin(request.url) == allowed and (cfg.allow_writes or request.method in ('GET','HEAD','OPTIONS'))
        except ValueError:
            ok = False
        if ok:
            route.continue_()
        else:
            blocked.append(request.method + ' ' + (urlsplit(request.url).hostname or '[non-http]'))
            route.abort()

    def on_download(item):
        downloads.append(item)

    def watch(page):
        pages.append(page)
        page.on('download', on_download)

    context.route('**/*', gate)
    if hasattr(context, 'route_web_socket'):
        context.route_web_socket('**/*', lambda ws: (blocked.append('WebSocket'), ws.close()))
    context.on('page', watch)
    page = context.new_page()
    page.set_default_timeout(cfg.timeout_ms)
    try:
        response = page.goto(url, wait_until='domcontentloaded', timeout=cfg.timeout_ms)
        if response is None or not response.ok:
            return {"status":"inconclusive", "reason":"Initial HTTP response failed", "steps":[]}
        page.wait_for_timeout(cfg.settle_ms)
        if blocked:
            return {"status":"inconclusive", "reason":"Network policy blocked initial request", "steps":steps, "blocked":blocked}
        if len(pages) != 1 or origin(page.url) != allowed:
            return {"status":"inconclusive", "reason":"Unexpected initial navigation or popup", "steps":steps}
        initial = snapshot(page)
        previous = initial
        for i, action in enumerate(path):
            downloads.clear()
            if action.role == 'reload':
                response = page.reload(wait_until='domcontentloaded', timeout=cfg.timeout_ms)
                if response is None or not response.ok:
                    return {"status":"inconclusive", "reason":"Reload HTTP response failed", "steps":steps}
            else:
                locator = page.get_by_role(action.role, name=action.name, exact=True)
                count = locator.count()
                if count == 0:
                    return {"status":"unmatched", "at":i, "reason":"Accessible action not found", "steps":steps, "blocked":blocked}
                if count != 1 or not locator.is_visible() or not locator.is_enabled():
                    return {"status":"inconclusive", "at":i, "reason":"Ambiguous, hidden or disabled action", "steps":steps, "blocked":blocked}
                locator.click(timeout=cfg.timeout_ms)
            page.wait_for_timeout(cfg.settle_ms)
            if len(pages) != 1:
                return {"status":"inconclusive", "reason":"Popup navigation unsupported", "steps":steps, "blocked":blocked}
            if blocked:
                return {"status":"inconclusive", "reason":"Network policy blocked a request", "steps":steps, "blocked":blocked}
            if origin(page.url) != allowed:
                return {"status":"inconclusive", "reason":"Navigation left the authorized origin", "steps":steps}
            current = snapshot(page)
            files = []
            for item in downloads:
                if item.failure():
                    return {"status":"inconclusive", "reason":"Download did not complete", "steps":steps}
                p = Path(item.path())
                size = p.stat().st_size
                if size > 10 * 1024 * 1024:
                    return {"status":"inconclusive", "reason":"Download exceeds 10 MiB observation limit", "steps":steps}
                data = p.read_bytes()
                files.append({"name":item.suggested_filename,"bytes":size,"sha256":hashlib.sha256(data).hexdigest(),
                              "format_hint":"pdf" if data.startswith(b'%PDF-') else "other"})
            steps.append({"action":asdict(action), "outcome":delta(previous,current,files)})
            previous = current
        if blocked:
            return {"status":"inconclusive", "reason":"Network policy blocked a request", "steps":steps, "blocked":blocked}
        return {"status":"ok", "initial":initial, "final":previous, "steps":steps}
    except (Error, OSError, ValueError) as exc:
        return {"status":"inconclusive", "reason":str(exc).splitlines()[0][:350], "steps":steps, "blocked":blocked}
    finally:
        try:
            context.close()
        except Error:
            pass


def signature(result: dict) -> str:
    if result['status'] != 'ok':
        return stable_json({k: result.get(k) for k in ('status','at','reason','steps')})
    return stable_json({k:result[k] for k in ('initial','final','steps')})


def compare_path(before, after):
    if len(before) < 2 or len(after) < 2:
        return 'inconclusive', 'At least two observations per version are required'
    if len({signature(r) for r in before}) != 1 or len({signature(r) for r in after}) != 1:
        return 'inconclusive', 'Observed behavior varied across repeated runs'
    a,b = before[0],after[0]
    if a['status'] != 'ok':
        return 'inconclusive','Baseline path did not execute reliably'
    if b['status'] == 'unmatched' and not b.get('blocked'):
        return 'unmatched','Baseline action unavailable by its original accessible name; may be renamed or removed'
    if b['status'] != 'ok':
        return 'inconclusive',b.get('reason','Candidate could not be executed')
    aout,bout = [x['outcome'] for x in a['steps']], [x['outcome'] for x in b['steps']]
    if not aout and not bout:
        return 'inventory', 'Initial accessible-action inventory; no action executed'
    if aout == bout:
        if not any(has_signal(o) for o in aout):
            return 'unobserved','Both paths executed, but neither produced a supported observable change'
        return 'equivalent_observed','Repeated observable action outcomes matched'
    if any(x['downloads'] != y['downloads'] for x,y in zip(aout,bout)):
        return 'download_changed','Download occurrence, name, size or bytes differ; inspect intent'
    return 'behavior_changed','Observable action outcomes differ; inspect intent'


def compare(before_url: str, after_url: str, cfg: Settings) -> dict:
    cfg.validate()
    validate_url(before_url); validate_url(after_url)
    rows = []
    queue = deque([()])
    seen_paths = {()}
    candidate_only = []
    with sync_playwright() as p:
        kwargs = {"headless": True}
        if cfg.executable:
            kwargs['executable_path'] = cfg.executable
        browser = p.chromium.launch(**kwargs)
        try:
            while queue and len(rows) < cfg.budget:
                path = queue.popleft()
                before = [experiment(browser,before_url,path,cfg) for _ in range(cfg.repeats)]
                after = [experiment(browser,after_url,path,cfg) for _ in range(cfg.repeats)]
                status,reason = compare_path(before,after)
                a,b = before[0],after[0]
                rows.append({"path":[asdict(x) for x in path],"status":status,"reason":reason,"before":before,"after":after})
                if status != 'inconclusive' and a['status']==b['status']=='ok':
                    aa={Action(**x) for x in a['final']['actions']}; ba={Action(**x) for x in b['final']['actions']}
                    for action in sorted(ba-aa):
                        candidate_only.append({"path":[asdict(x) for x in path],"action":asdict(action)})
                if a['status'] != 'ok' or len(path)>=cfg.depth or len({signature(r) for r in before})!=1:
                    continue
                acts = [Action(**x) for x in a['final']['actions']]
                if path and path[-1].role != 'reload':
                    acts.insert(0, Action('reload','Reload page'))
                for action in acts:
                    new = path+(action,)
                    if new not in seen_paths and len(seen_paths)<cfg.budget:
                        seen_paths.add(new); queue.append(new)
        finally:
            browser.close()
    return {"schema":"ghostdiff.evidence/v1","before_url":before_url,"after_url":after_url,
            "observation_revision":2,"settings":asdict(cfg),"summary":dict(Counter(r['status'] for r in rows)),"candidate_only_actions":candidate_only,
            "paths":rows,"coverage":{"executed_paths":len(rows),"path_budget":cfg.budget,"depth_limit":cfg.depth,"budget_reached":len(rows)>=cfg.budget},"limits":"Bounded baseline exploration without state pruning; exact accessible names; observed deltas, not proof of functional equivalence."}


def replay(before_url, after_url, path, cfg):
    cfg.validate(); validate_url(before_url); validate_url(after_url)
    validate_path(path,cfg)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, **({'executable_path':cfg.executable} if cfg.executable else {}))
        try:
            a=[experiment(browser,before_url,path,cfg) for _ in range(cfg.repeats)]
            b=[experiment(browser,after_url,path,cfg) for _ in range(cfg.repeats)]
            status,reason=compare_path(a,b)
            return {"status":status,"reason":reason,"path":[asdict(x) for x in path],"before":a,"after":b}
        finally:
            browser.close()
