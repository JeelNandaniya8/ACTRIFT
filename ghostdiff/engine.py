"""Browser-driven differential experiments. No model or API required."""
from __future__ import annotations

from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from time import perf_counter
from dataclasses import asdict, dataclass, replace
import base64
import re
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Error, sync_playwright
from .matching import suggestions
from .session import local_storage_state
from .reset import reset_target,reset_backend


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
    browser: str = 'chromium'
    ignore: tuple[str, ...] = ()
    mask_text: tuple[str, ...] = ()
    screenshots: bool = False
    allow_risky_actions: bool = False
    parallel: bool = False

    def validate(self):
        if self.browser not in ('chromium', 'firefox', 'webkit'):
            raise ValueError('Unsupported browser engine')
        if self.executable is not None and not isinstance(self.executable, str):
            raise ValueError('Browser executable must be a path string')
        if type(self.allow_writes) is not bool:
            raise ValueError('allow_writes must be boolean')
        for value in (self.ignore,self.mask_text):
            if not isinstance(value,(tuple,list)) or len(value)>30 or any(not isinstance(x,str) or not x.strip() or len(x)>200 for x in value):
                raise ValueError("Invalid ignore or text-mask rules")
        if type(self.screenshots) is not bool or type(self.allow_risky_actions) is not bool or type(self.parallel) is not bool:
            raise ValueError("Screenshot and risky-action flags must be boolean")
        for name, low, high in (("depth", 1, 5), ("budget", 1, 200),
                                ("settle_ms", 0, 5000), ("timeout_ms", 100, 15000),
                                ("repeats", 2, 5)):
            if type(getattr(self, name)) is not int or not low <= getattr(self, name) <= high:
                raise ValueError(f"{name} must be between {low} and {high}")


def launch_browser(playwright, cfg: Settings):
    cfg.validate()
    kwargs = {'headless': True}
    if cfg.executable:
        kwargs['executable_path'] = cfg.executable
    return getattr(playwright, cfg.browser).launch(**kwargs)


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
  const candidates=document.querySelectorAll('button,[role=button],input[type=button],input[type=submit],a[href],[role=link]');
  if(candidates.length>5000) throw Error('Action candidate observation limit (5000) exceeded');
  return [...candidates].filter(e=>visible(e)&&!e.disabled&&e.getAttribute('aria-disabled')!=='true').map(e=>({role:e.matches('a[href],[role=link]')?'link':'button', name:label(e).replace(/\s+/g,' ').trim()})).filter(a=>a.name&&a.name.length<=120);
}'''


def available(page) -> list[Action]:
    actions = sorted(set(Action(**a) for a in page.evaluate(DISCOVER)))
    if len(actions)>256:
        raise ValueError("Unique named action observation limit (256) exceeded")
    return [a for a in actions if page.get_by_role(a.role, name=a.name, exact=True).count() == 1]


RISKY = re.compile(r"\b(delete|remove|destroy|erase|logout|log out|sign out|unsubscribe|cancel subscription|purchase|buy|pay|transfer|send|publish|checkout)\b", re.I)


def ignored(action, cfg):
    if action.role == "reload":
        return False
    name=normal(action.name).casefold()
    return name in {normal(x).casefold() for x in cfg.ignore} or (not cfg.allow_risky_actions and bool(RISKY.search(name)))


def masked_text(page, selectors):
    if not selectors:
        return page.locator('body').inner_text()
    # Restore synchronous DOM changes before returning to the application.
    return page.evaluate("""selectors => {
      const nodes=new Set();
      for(const selector of selectors) for(const node of document.querySelectorAll(selector)){
        if(node===document.body || node===document.documentElement || !node.style) throw Error('Invalid text mask target');
        nodes.add(node); if(nodes.size>2000) throw Error('Too many text mask targets');
      }
      const old=[...nodes].map(node=>[node,node.getAttribute('style')]);
      try {
        for(const [node] of old) node.style.setProperty('display','none','important');
        return document.body.innerText;
      } finally {
        for(const [node,value] of old) {
          if(value===null) node.removeAttribute('style'); else node.setAttribute('style',value);
        }
      }
    }""",list(selectors))


def snapshot(page, cfg=Settings()) -> dict:
    raw = masked_text(page,cfg.mask_text)
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
    return any(outcome.get(key) for key in ("text_added", "text_removed", "route_change", "downloads", "actions_added", "actions_removed", "page_errors", "http_errors", "control_change"))


def http_failure(resource_type, status):
    """Observe server failures in API requests and failed document navigation."""
    return (resource_type == "document" and status >= 400) or (resource_type in ("fetch","xhr") and status >= 500)


def validate_path(path, cfg, form_values=None):
    if len(path) > cfg.depth:
        raise ValueError("Journey exceeds configured depth")
    form_values=form_values or {}
    for i,a in enumerate(path):
        allowed=("textbox","searchbox","checkbox","combobox") if i in form_values else ("button","link","reload")
        if a.role not in allowed or not isinstance(a.name, str) or not 1 <= len(a.name) <= 120:
            raise ValueError("Unsupported action in journey")
        if i not in form_values:continue
        value=form_values[i]
        valid=False
        if a.role in ("textbox","searchbox"):
            valid=isinstance(value,str) and len(value)<=500
            valid=valid or isinstance(value,dict) and set(value)=={"op","key"} and value["op"]=="press" and value["key"] in ("Enter","Escape")
        elif a.role=="checkbox":
            valid=isinstance(value,dict) and set(value)=={"op"} and value["op"] in ("check","uncheck")
        elif a.role=="combobox":
            valid=isinstance(value,dict) and set(value)=={"op","label"} and value["op"]=="select" and isinstance(value["label"],str) and 1<=len(value["label"])<=200
        if not valid:raise ValueError("Invalid explicit form operation")


class BoundedEvents(list):
    """Keep a bounded sample and flag overflow rather than silently passing."""
    def __init__(self, limit):
        super().__init__()
        self.limit=limit
        self.overflow=False

    def append(self,value):
        if len(self)<self.limit:
            super().append(value)
        else:
            self.overflow=True

    def clear(self):
        super().clear()
        self.overflow=False


def source_locations(stack,allowed):
    """Bounded same-origin stack coordinates; no query strings or raw stack retained."""
    found=[]
    if not isinstance(stack,str):return found
    for match in re.finditer(r"(https?://[^\s()]+?):(\d+):(\d+)(?=\s|\)|$)",stack[:12000]):
        url,line,column=match.groups()
        try:
            if origin(url)!=allowed:continue
        except ValueError:continue
        path=urlsplit(url).path[:300]
        loc={"path":path,"line":int(line),"column":int(column)}
        if loc not in found:found.append(loc)
        if len(found)>=5:break
    return found


def experiment(browser: Browser, url: str, path: tuple[Action, ...], cfg: Settings, storage_state=None, form_values=None) -> dict:
    """Every path starts in a fresh browser context; no real user session is used."""
    form_values=form_values or {}
    validate_path(path, cfg,form_values)
    if any(ignored(a,cfg) for a in path):
        return {"status":"inconclusive","reason":"Action excluded by safety rules","steps":[]}
    context = browser.new_context(accept_downloads=True, service_workers="block",storage_state=local_storage_state(storage_state,url),viewport={"width":1000,"height":700})
    allowed = origin(url)
    blocked = BoundedEvents(20)
    downloads = BoundedEvents(8)
    page_errors = BoundedEvents(20)
    http_errors = BoundedEvents(20)
    error_locations = BoundedEvents(100)
    pages = BoundedEvents(2)
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
        # Overflow is classified as inconclusive before hashing any downloads.

    def on_response(response):
        # Redirects may bypass request interception. Observe unexpected responses
        # as a second check, without claiming they were prevented.
        try:
            same_origin=origin(response.url)==allowed
        except ValueError:
            same_origin=False
        if not same_origin:
            blocked.append("Unexpected off-origin HTTP response")
        kind=response.request.resource_type
        if http_failure(kind,response.status):
            # Do not retain query strings, request bodies, headers or credentials.
            http_errors.append({"resource":kind,"status":response.status,"path":urlsplit(response.url).path[:300]})

    def on_page_error(exc):
        page_errors.append(normal(str(exc))[:500])
        for location in source_locations(getattr(exc,"stack",None),allowed):
            if location not in error_locations:error_locations.append(location)

    def watch(page):
        pages.append(page)
        page.on('download', on_download)
        page.on('pageerror', on_page_error)

    context.route('**/*', gate)
    if hasattr(context, 'route_web_socket'):
        context.route_web_socket('**/*', lambda ws: (blocked.append('WebSocket'), ws.close()))
    context.on('response', on_response)
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
        initial = snapshot(page,cfg)
        if page_errors:
            return {"status":"inconclusive", "reason":"Uncaught exception during initial load", "page_errors":page_errors[:20], "steps":steps}
        if http_errors:
            return {"status":"inconclusive","reason":"HTTP failure during initial load","http_errors":http_errors[:20],"steps":steps}
        previous = initial
        for i, action in enumerate(path):
            downloads.clear()
            page_errors.clear()
            http_errors.clear()
            error_locations.clear()
            control_change=None
            if action.role == 'reload':
                response = page.reload(wait_until='domcontentloaded', timeout=cfg.timeout_ms)
                if response is None or not response.ok:
                    return {"status":"inconclusive", "reason":"Reload HTTP response failed", "steps":steps}
            else:
                locator = page.get_by_role(action.role, name=action.name, exact=True)
                count = locator.count()
                if count == 0:
                    return {"status":"unmatched", "at":i, "reason":"Accessible action not found", "steps":steps, "blocked":blocked, "suggestions":suggestions(action.role,action.name,available(page))}
                if count != 1 or not locator.is_visible() or not locator.is_enabled():
                    return {"status":"inconclusive", "at":i, "reason":"Ambiguous, hidden or disabled action", "steps":steps, "blocked":blocked}
                if action.role in ("textbox","searchbox"):
                    typ=(locator.get_attribute("type") or "text").casefold()
                    if typ not in ("text","email","search","url","tel") or not locator.is_editable():
                        return {"status":"inconclusive","reason":"Unsupported or read-only form field","steps":steps}
                    if re.search(r"password|passcode|secret|token|credit.card|card.number|cvv|otp",action.name,re.I):
                        return {"status":"inconclusive","reason":"Sensitive form field excluded","steps":steps}
                    operation=form_values[i]
                    if isinstance(operation,str):locator.fill(operation,timeout=cfg.timeout_ms)
                    else:locator.press(operation["key"],timeout=cfg.timeout_ms)
                elif action.role in ("checkbox","combobox"):
                    if re.search(r"password|passcode|secret|token|credit.card|card.number|cvv|otp",action.name,re.I):
                        return {"status":"inconclusive","reason":"Sensitive form field excluded","steps":steps}
                    operation=form_values[i]
                    if action.role=="checkbox":
                        if not locator.evaluate("e => e.tagName==='INPUT' && e.type==='checkbox'"):
                            return {"status":"inconclusive","reason":"Only native checkbox controls supported","steps":steps}
                        old=locator.is_checked()
                        locator.set_checked(operation["op"]=="check",timeout=cfg.timeout_ms)
                        new=locator.is_checked()
                    else:
                        if not locator.evaluate("e => e.tagName==='SELECT' && !e.multiple"):
                            return {"status":"inconclusive","reason":"Only native single-select controls supported","steps":steps}
                        old=locator.evaluate("e => e.selectedIndex")
                        locator.select_option(label=operation["label"],timeout=cfg.timeout_ms)
                        new=locator.evaluate("e => e.selectedIndex")
                    if old!=new:control_change={"role":action.role,"from":old,"to":new}
                else:
                    locator.click(timeout=cfg.timeout_ms)
            page.wait_for_timeout(cfg.settle_ms)
            if len(pages) != 1:
                return {"status":"inconclusive", "reason":"Popup navigation unsupported", "steps":steps, "blocked":blocked}
            if blocked:
                return {"status":"inconclusive", "reason":"Network policy blocked a request", "steps":steps, "blocked":blocked}
            if origin(page.url) != allowed:
                return {"status":"inconclusive", "reason":"Navigation left the authorized origin", "steps":steps}
            current = snapshot(page,cfg)
            if any(x.overflow for x in (downloads,page_errors,http_errors)):
                return {"status":"inconclusive","reason":"Browser event observation limit exceeded","steps":steps}
            files = []
            total_download_bytes=0
            for item in downloads:
                if item.failure():
                    return {"status":"inconclusive", "reason":"Download did not complete", "steps":steps}
                p = Path(item.path())
                size = p.stat().st_size
                total_download_bytes += size
                if total_download_bytes > 20 * 1024 * 1024:
                    return {"status":"inconclusive","reason":"Aggregate download observation limit (20 MiB) exceeded","steps":steps}
                if size > 10 * 1024 * 1024:
                    return {"status":"inconclusive", "reason":"Download exceeds 10 MiB observation limit", "steps":steps}
                data = p.read_bytes()
                files.append({"name":item.suggested_filename,"bytes":size,"sha256":hashlib.sha256(data).hexdigest(),
                              "format_hint":"pdf" if data.startswith(b'%PDF-') else "other"})
            if any(x.overflow for x in (downloads,page_errors,http_errors)):
                return {"status":"inconclusive","reason":"Browser event observation limit exceeded","steps":steps}
            outcome=delta(previous,current,files)
            if control_change is not None:outcome["control_change"]=control_change
            outcome["page_errors"]=sorted(page_errors[:20])
            if error_locations:outcome["source_locations"]=sorted(error_locations,key=stable_json)
            if http_errors:
                outcome["http_errors"]=sorted(http_errors,key=stable_json)[:20]
            steps.append({"action":asdict(action), "outcome":outcome})
            previous = current
        if blocked:
            return {"status":"inconclusive", "reason":"Network policy blocked a request", "steps":steps, "blocked":blocked}
        result={"status":"ok", "initial":initial, "final":previous, "steps":steps}
        if cfg.screenshots:
            try:
                image=page.screenshot(type="jpeg",quality=65,timeout=cfg.timeout_ms,mask=[page.locator(s) for s in cfg.mask_text])
                if len(image)<=512*1024:
                    result["screenshot_jpeg"]=base64.b64encode(image).decode("ascii")
            except Error:
                result["screenshot_note"]="Screenshot unavailable"
        return result
    except (Error, OSError, ValueError) as exc:
        reason="Explicit form journey failed" if form_values else str(exc).splitlines()[0][:350]
        return {"status":"inconclusive", "reason":reason, "steps":steps, "blocked":blocked}
    finally:
        try:
            context.close()
        except Error:
            pass


def signature(result: dict) -> str:
    if result['status'] != 'ok':
        return stable_json({k: result.get(k) for k in ('status','at','reason','steps','suggestions','page_errors','http_errors','blocked')})
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
    if any(o.get('page_errors') or o.get('http_errors') for o in aout):
        return 'inconclusive','Baseline journey raised an exception or HTTP failure; cannot establish a healthy baseline'
    if any(o.get('page_errors') for o in bout):
        return 'behavior_changed','Candidate journey raised a reproducible uncaught exception'
    if any(o.get('http_errors') for o in bout):
        return 'behavior_changed','Candidate journey produced a reproducible HTTP failure'
    if aout == bout:
        if not any(has_signal(o) for o in aout):
            return 'unobserved','Both paths executed, but neither produced a supported observable change'
        return 'equivalent_observed','Repeated observable action outcomes matched'
    if any(x['downloads'] != y['downloads'] for x,y in zip(aout,bout)):
        return 'download_changed','Download occurrence, name, size or bytes differ; inspect intent'
    return 'behavior_changed','Observable action outcomes differ; inspect intent'


def repeated(browser,url,path,cfg,state,reset=False):
    results=[]
    for i in range(cfg.repeats):
        if reset and not reset_backend(url):
            results.append({"status":"inconclusive","reason":"Explicit backend reset failed","steps":[]})
            continue
        results.append(experiment(browser,url,path,replace(cfg,screenshots=cfg.screenshots and i==0),state))
    return results


@contextmanager
def candidate_worker(cfg):
    """Optional second browser, kept on its own Playwright thread."""
    if not cfg.parallel:
        yield None
        return
    with ThreadPoolExecutor(max_workers=1,thread_name_prefix="ghostdiff-candidate") as pool:
        state={}
        def start():
            p=sync_playwright().start()
            try:
                state["browser"]=launch_browser(p,cfg)
                state["playwright"]=p
            except BaseException:
                p.stop()
                raise
        def stop():
            try:
                state["browser"].close()
            finally:
                state["playwright"].stop()
        def run(url,path,storage):
            return repeated(state["browser"],url,path,cfg,storage)
        pool.submit(start).result()
        try:
            yield lambda url,path,storage: pool.submit(run,url,path,storage)
        finally:
            pool.submit(stop).result()


def compare(before_url: str, after_url: str, cfg: Settings, before_state=None, after_state=None, *, reset=False) -> dict:
    cfg.validate()
    validate_url(before_url); validate_url(after_url)
    if type(reset) is not bool:raise ValueError("Reset authorization must be boolean")
    if reset:
        if reset_target(before_url)==reset_target(after_url) or cfg.parallel or cfg.allow_writes:
            raise ValueError("Reset requires separate disposable local servers, sequential execution and read-policy browser actions")
    if cfg.parallel and origin(before_url)==origin(after_url):
        raise ValueError("Parallel mode requires separate local origins and independent test backends")
    if cfg.parallel and cfg.allow_writes:
        raise ValueError("Parallel mode does not allow write-enabled runs")
    started=perf_counter()
    rows = []
    queue = deque([()])
    seen_paths = {()}
    candidate_only = []
    baseline_only = []
    skipped = []
    omitted_budget = 0
    depth_frontiers = 0
    with sync_playwright() as p, candidate_worker(cfg) as submit:
        browser = launch_browser(p,cfg)
        try:
            while queue and len(rows) < cfg.budget:
                path = queue.popleft()
                pending=submit(after_url,path,after_state) if submit else None
                before=repeated(browser,before_url,path,cfg,before_state,reset)
                after=pending.result() if pending else repeated(browser,after_url,path,cfg,after_state,reset)
                status,reason = compare_path(before,after)
                a,b = before[0],after[0]
                rows.append({"path":[asdict(x) for x in path],"status":status,"reason":reason,"before":before,"after":after})
                if status != 'inconclusive' and a['status']==b['status']=='ok':
                    aa={Action(**x) for x in a['final']['actions']}; ba={Action(**x) for x in b['final']['actions']}
                    for action in sorted(ba-aa):
                        candidate_only.append({"path":[asdict(x) for x in path],"action":asdict(action)})
                    for action in sorted(aa-ba):
                        if not ignored(action,cfg):
                            baseline_only.append({"path":[asdict(x) for x in path],"action":asdict(action)})
                if a['status'] != 'ok' or len({signature(r) for r in before})!=1:
                    continue
                if len(path)>=cfg.depth:
                    depth_frontiers += 1
                    continue
                acts = [Action(**x) for x in a['final']['actions']]
                if path and path[-1].role != 'reload':
                    acts.insert(0, Action('reload','Reload page'))
                for action in acts:
                    if ignored(action,cfg):
                        skipped.append({"path":[asdict(x) for x in path],"action":asdict(action)})
                        continue
                    new = path+(action,)
                    if new in seen_paths:
                        continue
                    if len(seen_paths)<cfg.budget:
                        seen_paths.add(new); queue.append(new)
                    else:
                        omitted_budget += 1
        finally:
            browser.close()
    elapsed=perf_counter()-started
    return {"schema":"ghostdiff.evidence/v1","performance":{"elapsed_seconds":round(elapsed,3),"paths_per_second":round(len(rows)/max(elapsed,0.001),3),"parallel":cfg.parallel},"before_url":before_url,"after_url":after_url,
            "observation_revision":3,"backend_reset":reset,"authenticated_baseline":before_state is not None,"authenticated_candidate":after_state is not None,"settings":asdict(cfg),"summary":dict(Counter(r['status'] for r in rows)),"candidate_only_actions":candidate_only,"baseline_only_actions":baseline_only,
            "paths":rows,"skipped_actions":skipped,"coverage":{"executed_paths":len(rows),"path_budget":cfg.budget,"depth_limit":cfg.depth,"budget_reached":len(rows)>=cfg.budget,"omitted_budget_branches":omitted_budget,"depth_frontiers":depth_frontiers,"skipped_action_entries":len(skipped)},"limits":"Bounded baseline exploration without state pruning; exact accessible names; observed deltas, not proof of functional equivalence."}


def replay(before_url, after_url, path, cfg, before_state=None, after_state=None):
    cfg.validate(); validate_url(before_url); validate_url(after_url)
    validate_path(path,cfg)
    with sync_playwright() as p:
        browser=launch_browser(p,cfg)
        try:
            a=[experiment(browser,before_url,path,cfg,before_state) for _ in range(cfg.repeats)]
            b=[experiment(browser,after_url,path,cfg,after_state) for _ in range(cfg.repeats)]
            status,reason=compare_path(a,b)
            return {"status":status,"reason":reason,"path":[asdict(x) for x in path],"before":a,"after":b}
        finally:
            browser.close()
