"""
scrape_purdue_catalog.py
Scrapes the Purdue University course catalog (catalog.purdue.edu)
and loads courses into purdue_courses.db.

Usage
-----
# Specific departments only (recommended for targeted imports)
python3 scrape_purdue_catalog.py --dept CS MA ECE ME

# All undergraduate courses across the full catalog (~6 000+ courses, takes ~4 hrs)
python3 scrape_purdue_catalog.py

# Faster with a shorter delay (less polite to the server)
python3 scrape_purdue_catalog.py --dept CS --delay 1

# Re-scrape courses that were already fetched
python3 scrape_purdue_catalog.py --dept CS --no-cache

Dependencies
------------
pip install requests beautifulsoup4 lxml
"""

import re
import sys
import json
import time
import sqlite3
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Install with:\n  pip install requests beautifulsoup4 lxml")
    sys.exit(1)

# ── Catalog constants ─────────────────────────────────────────────────────────

BASE_URL = "https://catalog.purdue.edu"
CATOID   = 18       # 2025-26 catalog year (update if catalog.purdue.edu rolls over)
NAVOID   = 23635    # "Courses" listing page navoid
DB_PATH  = "purdue_courses.db"
TOTAL_LISTING_PAGES = 86   # known page count; updated dynamically if wrong

# Only index undergraduate/dual-level courses (exclude pure-grad 60000+ and professional 80000+)
MIN_COURSE_NUM = 10000
MAX_COURSE_NUM = 59999

# ── HTTP session ──────────────────────────────────────────────────────────────

_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Purdue-CoursePlanner-Scraper/1.0 "
        "(open-source academic project)"
    )
})


def _get(url: str, params: dict, delay: float, retries: int = 3) -> Optional[BeautifulSoup]:
    """GET a URL with rate-limiting and exponential back-off on failure."""
    for attempt in range(retries):
        try:
            time.sleep(delay)
            resp = _session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as exc:
            wait = delay * (attempt + 2)
            print(f"    [warn] attempt {attempt + 1}/{retries} failed — {exc}; "
                  f"retrying in {wait:.0f}s…")
            time.sleep(wait)
    print(f"    [error] giving up on {url} {params}")
    return None


# ── Listing-page helpers ──────────────────────────────────────────────────────

# Link text is "DEPT NNNNN - Course Title"
_LINK_RE = re.compile(r'^([A-Z]{2,6})\s+(\d{4,6})\s*-\s*(.+)$')


def _extract_course_links(soup: BeautifulSoup) -> List[Tuple[int, str, str]]:
    """
    Return a list of (coid, course_number, title) for every course link on a listing page.
    The course number and title are parsed from the visible link text so we can
    filter by department without an extra HTTP request.
    """
    results = []
    for a in soup.select('a[href*="preview_course_nopop.php"]'):
        href = a.get('href', '')
        m_id = re.search(r'coid=(\d+)', href)
        if not m_id:
            continue
        coid = int(m_id.group(1))
        text = a.get_text(' ', strip=True)
        m_txt = _LINK_RE.match(text)
        if not m_txt:
            continue
        dept, num_str, title = m_txt.group(1), m_txt.group(2), m_txt.group(3).strip()
        results.append((coid, f"{dept} {num_str}", title))
    return results


def _has_next_page(soup: BeautifulSoup, current: int) -> bool:
    next_str = str(current + 1)
    return bool(
        soup.find('a', string=next_str) or
        soup.find('a', {'aria-label': f'Page {next_str}'})
    )


def _current_page_num(soup: BeautifulSoup) -> Optional[int]:
    el = soup.select_one('span[aria-current="page"] strong')
    if el:
        try:
            return int(el.get_text(strip=True))
        except ValueError:
            pass
    return None


# ── Catalog-wide listing scrape ───────────────────────────────────────────────

def fetch_all_course_links(
    delay: float,
    dept_filter: Optional[Set[str]] = None,
) -> List[Tuple[int, str, str]]:
    """
    Walk every listing page of the catalog and return (coid, course_number, title) tuples.
    If dept_filter is given (e.g. {'CS', 'MA'}), only tuples whose dept prefix matches
    are returned — but all 86 listing pages are still traversed (server-side filtering
    is unreliable on this Acalog install).
    """
    all_links: List[Tuple[int, str, str]] = []
    page = 1

    while True:
        soup = _get(
            f"{BASE_URL}/content.php",
            params={
                'catoid': CATOID,
                'navoid': NAVOID,
                'filter[cpage]': page,
                'filter[only_active]': 1,
            },
            delay=delay,
        )
        if soup is None:
            break

        links = _extract_course_links(soup)
        if not links:
            break

        if dept_filter:
            kept = [(coid, num, t) for coid, num, t in links
                    if num.split()[0] in dept_filter]
        else:
            kept = links

        all_links.extend(kept)

        cur = _current_page_num(soup)
        if cur is None or not _has_next_page(soup, cur):
            break

        # Progress line (overwrite in place)
        total_known = TOTAL_LISTING_PAGES
        pct = cur / total_known * 100
        filtered_label = (
            f" ({len(all_links)} matching)" if dept_filter else ""
        )
        print(
            f"  Scanning listing pages: {cur}/{total_known} ({pct:.0f}%){filtered_label}",
            end='\r', flush=True,
        )
        page = cur + 1

    print()   # newline after the \r progress line
    return all_links


# ── Course detail parsing ─────────────────────────────────────────────────────

_PREREQ_RE     = re.compile(r'[Pp]rerequisite[s]?\s*(?:\(s\))?\s*:?\s*([^.;]+)', re.IGNORECASE)
_COREQ_RE      = re.compile(r'[Cc]orequisite[s]?\s*(?:\(s\))?\s*:?\s*([^.;]+)', re.IGNORECASE)
_COURSE_NUM_RE = re.compile(r'\b([A-Z]{2,6})\s+(\d{4,6})\b')


def _extract_course_numbers(text: str) -> List[str]:
    return [f"{m.group(1)} {m.group(2)}" for m in _COURSE_NUM_RE.finditer(text)]


def parse_course_detail(soup: BeautifulSoup, coid: int) -> Optional[Dict]:
    """
    Parse a preview_course_nopop.php page.
    Returns a dict ready for DB insertion, or None for grad/invalid courses.
    """
    h1 = soup.select_one('h1#course_preview_title')
    if not h1:
        return None

    raw_title = h1.get_text(' ', strip=True)
    m = re.match(r'^([A-Z]{2,6})\s+(\d{4,6})\s*-\s*(.+)$', raw_title)
    if not m:
        return None

    dept, num_str, title = m.group(1), m.group(2), m.group(3).strip()
    course_number = f"{dept} {num_str}"

    try:
        num = int(num_str)
    except ValueError:
        return None
    if not (MIN_COURSE_NUM <= num <= MAX_COURSE_NUM):
        return None

    # Find the <p> that contains the h1 (the main content block)
    content_p = next(
        (p for p in soup.find_all('p') if p.find('h1', id='course_preview_title')),
        None,
    )

    # Credits
    credits = 3
    if content_p:
        m_cr = re.search(r'Credit Hours:\s*([\d.]+)', content_p.get_text())
        if m_cr:
            credits = round(float(m_cr.group(1)))

    # Description — text between "Credit Hours: X.XX." and the first <hr>
    description = ""
    if content_p:
        p_html = str(content_p)
        m_desc = re.search(
            r'Credit Hours:\s*[\d.]+\.\s*(.*?)<hr',
            p_html,
            re.DOTALL | re.IGNORECASE,
        )
        if m_desc:
            raw = m_desc.group(1)
            desc_soup = BeautifulSoup(raw, 'lxml')
            description = re.sub(r'\s+', ' ', desc_soup.get_text(' ')).strip()

    # Prerequisites / Corequisites embedded in description text
    prerequisites: List[str] = []
    corequisites:  List[str] = []

    pm = _PREREQ_RE.search(description)
    if pm:
        prerequisites = _extract_course_numbers(pm.group(1))

    cm = _COREQ_RE.search(description)
    if cm:
        corequisites = _extract_course_numbers(cm.group(1))

    return {
        'course_number': course_number,
        'title':         title,
        'description':   description,
        'credits':       credits,
        'department':    dept,
        'prerequisites': prerequisites,
        'corequisites':  corequisites,
        'terms_offered': ["Fall", "Spring"],   # not published per-course in Purdue catalog
        'is_required':   0,
        '_coid':         coid,
    }


# ── Database helpers ──────────────────────────────────────────────────────────

def _init_cache(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _scrape_cache (
            coid       INTEGER PRIMARY KEY,
            scraped_at TEXT
        )
    """)
    conn.commit()


def _cached_coids(conn: sqlite3.Connection) -> Set[int]:
    _init_cache(conn)
    return {row[0] for row in conn.execute("SELECT coid FROM _scrape_cache")}


def _mark_done(conn: sqlite3.Connection, coid: int):
    conn.execute(
        "INSERT OR REPLACE INTO _scrape_cache (coid, scraped_at) VALUES (?, ?)",
        (coid, datetime.now().isoformat()),
    )
    conn.commit()


def _ensure_department(conn: sqlite3.Connection, code: str):
    """Insert a stub department row if the code doesn't already exist."""
    if not conn.execute(
        "SELECT code FROM departments WHERE code = ?", (code,)
    ).fetchone():
        conn.execute(
            "INSERT OR IGNORE INTO departments "
            "(code, name, required_credits, required_courses) VALUES (?, ?, 120, '[]')",
            (code, code),
        )
        conn.commit()


def _upsert_course(conn: sqlite3.Connection, course: Dict):
    conn.execute(
        """INSERT OR REPLACE INTO courses
             (course_number, title, description, credits, department,
              prerequisites, corequisites, terms_offered, is_required)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            course['course_number'],
            course['title'],
            course['description'],
            course['credits'],
            course['department'],
            json.dumps(course['prerequisites']),
            json.dumps(course['corequisites']),
            json.dumps(course['terms_offered']),
            course['is_required'],
        ),
    )
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape the Purdue course catalog into purdue_courses.db",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dept", nargs="+", metavar="PREFIX",
        help="Limit to these department prefixes, e.g. --dept CS MA ECE. "
             "All listing pages are still scanned; filtering happens client-side.",
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Seconds between HTTP requests (default: 2.0).",
    )
    parser.add_argument(
        "--db", default=DB_PATH,
        help=f"SQLite database path (default: {DB_PATH})",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Re-scrape course detail pages even if already cached.",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    already_done = set() if args.no_cache else _cached_coids(conn)
    if already_done:
        print(f"Resume mode: {len(already_done)} coids already cached (skipping detail fetch).")

    dept_filter: Optional[Set[str]] = None
    if args.dept:
        dept_filter = {d.upper().strip() for d in args.dept}
        print(f"Department filter: {', '.join(sorted(dept_filter))}")

    # ── Phase 1: scan listing pages ───────────────────────────────────────
    print(f"\nPhase 1 — scanning all {TOTAL_LISTING_PAGES} listing pages…")
    course_links = fetch_all_course_links(args.delay, dept_filter)

    # De-duplicate by coid (same course can appear multiple times in listing)
    seen: Set[int] = set()
    unique_links = []
    for coid, num, title in course_links:
        if coid not in seen:
            seen.add(coid)
            unique_links.append((coid, num, title))

    # Filter out courses outside undergraduate range using number from link text
    unique_links = [
        (coid, num, t) for coid, num, t in unique_links
        if MIN_COURSE_NUM <= int(num.split()[1]) <= MAX_COURSE_NUM
    ]

    print(f"Found {len(unique_links)} unique qualifying course IDs.")

    # ── Phase 2: fetch detail pages ───────────────────────────────────────
    to_fetch = [(coid, num, t) for coid, num, t in unique_links
                if coid not in already_done]
    cached_count = len(unique_links) - len(to_fetch)

    print(f"\nPhase 2 — fetching {len(to_fetch)} detail pages "
          f"(skipping {cached_count} cached)…\n")

    scraped = skipped_invalid = errors = 0

    for i, (coid, num, title_hint) in enumerate(to_fetch, 1):
        prefix_str = f"[{i}/{len(to_fetch)}]"
        soup = _get(
            f"{BASE_URL}/preview_course_nopop.php",
            params={'catoid': CATOID, 'coid': coid},
            delay=args.delay,
        )
        if soup is None:
            errors += 1
            print(f"  {prefix_str} ✗ ERROR  coid={coid}  ({num})")
            continue

        course = parse_course_detail(soup, coid)
        _mark_done(conn, coid)

        if course is None:
            skipped_invalid += 1
            continue

        _ensure_department(conn, course['department'])
        _upsert_course(conn, course)
        scraped += 1

        prereq_info = (
            f"  prereqs: {', '.join(course['prerequisites'])}"
            if course['prerequisites'] else ""
        )
        print(
            f"  {prefix_str} ✓  {course['course_number']:16s}"
            f"{course['title'][:46]:46s}  ({course['credits']} cr){prereq_info}"
        )

    # ── Summary ───────────────────────────────────────────────────────────
    total_in_db = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    print(
        f"\n{'─' * 64}\n"
        f"Done.\n"
        f"  Scraped this run : {scraped}\n"
        f"  Skipped (invalid): {skipped_invalid}\n"
        f"  Errors           : {errors}\n"
        f"  Total in DB now  : {total_in_db}\n"
        f"  Database         : {args.db}"
    )
    conn.close()


if __name__ == "__main__":
    main()
