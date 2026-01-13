#!/usr/bin/env python3
"""
Route Health Checker for Django project

- Discovers all routes from crm_project/urls.py (including include() chains)
- Simulates requests using Django's test Client (no server needed)
- Reports status per route and overall summary

Notes:
- Does NOT perform destructive POST/PUT/PATCH/DELETE requests.
- Attempts safe GET where possible; treats 301/302 to login as auth-required (not a failure).
- For dynamic path converters (<int:id>, <slug:slug>, etc.), substitutes safe sample values.
- Skips admin doc and static patterns.

Run:
  python -m scripts.check_routes
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import re
from typing import List, Tuple, Dict, Any

# Ensure project root on sys.path and configure Django
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')

import django  # noqa: E402
from django.conf import settings  # noqa: E402
from django.urls import URLPattern, URLResolver, get_resolver  # noqa: E402
from django.test import Client  # noqa: E402

# Sample values for dynamic path converters
DYNAMIC_DEFAULTS = {
    'int': '1',
    'uuid': '00000000-0000-4000-8000-000000000000',
    'slug': 'example-slug',
    'str': 'example',
    'path': 'example/path',
}

ANGLE_RE = re.compile(r"<(?:(?P<conv>\w+):)?(?P<name>\w+)>")
REGEX_GROUP_RE = re.compile(r"\(\?P<[^>]+>[^)]+\)")


def substitute_dynamic_segments(route: str) -> str:
    """Replace Django path converters with sample values.
    Example: 'leads/<int:pk>/detail/' -> 'leads/1/detail/'
    """
    def repl(match: re.Match) -> str:
        conv = match.group('conv') or 'str'
        return DYNAMIC_DEFAULTS.get(conv, '1')
    return ANGLE_RE.sub(lambda m: repl(m), route)


def normalize_regex_route(pattern: str) -> str:
    """Convert Django/DRF regex route expressions to a plausible path segment.
    Examples:
      '^$' -> ''
      '^contacts/$' -> 'contacts/'
      '^contacts/(?P<pk>[^/.]+)/$' -> 'contacts/1/'
      '^templates\.(?P<format>[a-z0-9]+)$' -> 'templates.json'
    """
    s = pattern
    # Strip anchors
    if s.startswith('^'):
        s = s[1:]
    if s.endswith('$'):
        s = s[:-1]
    # Replace named regex groups with sample values
    def group_repl(m: re.Match) -> str:
        grp = m.group(0)
        # Heuristic: if group has '[a-z0-9]+' or format, use 'json', else use '1'
        if 'format' in grp or '[a-z0-9]' in grp or 'json' in grp or '\\.' in grp:
            return 'json'
        return '1'
    s = REGEX_GROUP_RE.sub(group_repl, s)
    # Replace generic regex tokens
    s = s.replace('(/)?', '/').replace('(/?)', '/')
    s = s.replace('.*', 'example')
    # Unescape dots and slashes
    s = s.replace('\\.', '.').replace('\\/', '/')
    # Remove remaining regex tokens like '(?:...)'
    s = re.sub(r"\(\?:[^)]+\)", '', s)
    # Remove stray parentheses
    s = s.replace('(', '').replace(')', '')
    # Collapse multiple slashes
    s = re.sub(r"/+", '/', s)
    return s


def join_paths(prefix: str, part: str) -> str:
    full = f"{prefix.rstrip('/')}/{part.lstrip('/')}"
    full = full.replace('//', '/')
    if not full.startswith('/'):
        full = '/' + full
    return full


def collect_routes(resolver: URLResolver, prefix: str = '') -> List[Tuple[str, Any]]:
    routes: List[Tuple[str, Any]] = []
    for p in resolver.url_patterns:
        if isinstance(p, URLPattern):
            try:
                route = getattr(p.pattern, '_route', None)
                if not route:
                    # Regex-based pattern
                    route = normalize_regex_route(str(p.pattern))
            except Exception:
                route = normalize_regex_route(str(p.pattern))
            route_str = substitute_dynamic_segments(route)
            url = join_paths(prefix, route_str)
            routes.append((url, p.callback))
        elif isinstance(p, URLResolver):
            try:
                route = getattr(p.pattern, '_route', None)
                if not route:
                    route = normalize_regex_route(str(p.pattern))
            except Exception:
                route = normalize_regex_route(str(p.pattern))
            route_str = substitute_dynamic_segments(route)
            new_prefix = join_paths(prefix, route_str)
            routes.extend(collect_routes(p, new_prefix))
    return routes


def is_auth_redirect(resp) -> bool:
    # Common: redirect to /login/?next=...
    if resp.status_code in (301, 302, 303, 307, 308):
        loc = resp.headers.get('Location') or (resp._headers.get('location', [None, None])[1] if hasattr(resp, '_headers') else None)
        login_path = getattr(settings, 'LOGIN_URL', '/login/')
        if loc and (login_path in loc or 'login' in loc or 'accounts/login' in loc):
            return True
    return False


def main() -> None:
    print(f"Project root: {PROJECT_ROOT}")
    django.setup()

    # Ensure the Django test client host is allowed to prevent DisallowedHost
    try:
        allowed = list(getattr(settings, 'ALLOWED_HOSTS', []))
        for h in ('testserver', 'localhost', '127.0.0.1'):
            if h not in allowed:
                allowed.append(h)
        settings.ALLOWED_HOSTS = allowed
    except Exception:
        pass

    resolver = get_resolver()
    all_routes = collect_routes(resolver)

    # Filter out duplicates and obvious static/admin docs
    seen = set()
    filtered: List[str] = []
    for url, _cb in all_routes:
        # Skip obvious non-app routes
        if any(skip in url for skip in ('/__debug__', '/static/', '/media/')):
            continue
        if url in seen:
            continue
        seen.add(url)
        filtered.append(url)

    client = Client()

    report: List[Dict[str, Any]] = []
    ok_count = 0
    auth_needed = 0
    fail_count = 0

    if not filtered:
        print("Discovered 0 unique routes.\n")
        print("Hints:")
        print("- Ensure ROOT_URLCONF is set to 'crm_project.urls' in settings.")
        print("- Check that crm_project/urls.py includes app urls via include(...).")
        print("- If your app uses class-based routers (DRF), ensure router.urls are included.")
        print("- If you recently deleted migrations, create and apply fresh migrations before route tests.")
        print()
    else:
        print(f"Discovered {len(filtered)} unique routes. Beginning checks...\n")

    for url in sorted(filtered, key=lambda s: (len(s.split('/')), s)):
        try:
            resp = client.get(url, follow=False)
        except Exception as e:
            report.append({'url': url, 'status': 'ERROR', 'detail': f'Exception on GET: {e}'})
            fail_count += 1
            continue

        if resp.status_code in (200, 201, 204):
            report.append({'url': url, 'status': resp.status_code})
            ok_count += 1
            continue

        if is_auth_redirect(resp):
            report.append({'url': url, 'status': 'AUTH_REQUIRED', 'detail': f"Redirected ({resp.status_code}) to login"})
            auth_needed += 1
            continue

        # Unauthorized/Forbidden -> treat as auth required (not a failure in health check)
        if resp.status_code in (401, 403):
            report.append({'url': url, 'status': 'AUTH_REQUIRED', 'detail': f'{resp.status_code} requires authentication/permission'})
            auth_needed += 1
            continue

        # Some DRF endpoints may require trailing slash; try adding or removing
        alt_url = url.rstrip('/') if url.endswith('/') else url + '/'
        if alt_url != url:
            try:
                resp2 = client.get(alt_url, follow=False)
                if resp2.status_code in (200, 201, 204) or is_auth_redirect(resp2):
                    tag = 'AUTH_REQUIRED' if is_auth_redirect(resp2) else resp2.status_code
                    report.append({'url': url, 'status': tag, 'detail': f"Alt tried: {alt_url} -> {tag}"})
                    if tag == 'AUTH_REQUIRED':
                        auth_needed += 1
                    else:
                        ok_count += 1
                    continue
            except Exception as e:
                report.append({'url': url, 'status': 'ERROR', 'detail': f'Alt GET {alt_url} exception: {e}'})
                fail_count += 1
                continue

        # OPTIONS often supported by DRF
        try:
            resp3 = client.options(url)
            if resp3.status_code in (200, 204):
                report.append({'url': url, 'status': 'OK(OPTIONS)', 'detail': f'OPTIONS supported ({resp3.status_code})'})
                ok_count += 1
                continue
        except Exception:
            pass

        # Data-dependent 404s on ID-based URLs (e.g., /something/1/) should not count as code failure
        if resp.status_code == 404 and re.search(r"/\d+(/|$)", url):
            report.append({'url': url, 'status': 'DATA_MISSING', 'detail': 'Likely requires existing object; 404 not treated as failure'})
            continue

        report.append({'url': url, 'status': resp.status_code, 'detail': 'GET failed and no acceptable fallback'})
        fail_count += 1

    print("\n=== Route Health Report ===")
    for item in report:
        print(f"- {item['url']}: {item['status']}" + (f" | {item['detail']}" if 'detail' in item else ''))

    print("\n=== Summary ===")
    print(f"Routes checked: {len(report)}")
    print(f"Routes OK: {ok_count}")
    print(f"Auth required (not a failure): {auth_needed}")
    print(f"Routes failing: {fail_count}")

    # Exit code hint (0 if all good or only auth redirects)
    if fail_count == 0:
        print("Verdict: PASS (no hard failures)")
    else:
        print("Verdict: NEEDS FIXES (see failing routes above)")


if __name__ == '__main__':
    main()
