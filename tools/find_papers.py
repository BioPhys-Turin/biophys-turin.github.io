"""Propose new group papers for _data/papers.json.

Asks OpenAlex (https://openalex.org) for recent works by the current members
listed in _data/researchers.json (those with an ORCID under "socials"), keeps
the ones that look like group papers, and adds them to the top of
_data/papers.json for a person to review in a pull request.

A work is proposed when all of these hold:
  * its type is in "include_types" and its subfield is not in
    "exclude_subfields" (tools/find_papers.json);
  * at least one current member is listed on it with an affiliation matching
    "affiliation_pattern" (this filters out namesakes and members' work done
    elsewhere);
  * it is not already in papers.json (same DOI, arXiv ID or title) and has not
    been proposed before (tools/papers_seen.json).

Every proposed work is recorded in tools/papers_seen.json, so a paper deleted
during review is not proposed again.

Usage: python tools/find_papers.py [--body PR_BODY.md] [--dry-run]
Only the Python standard library is needed.
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "_data" / "papers.json"
MEMBERS = ROOT / "_data" / "researchers.json"
FORMER = ROOT / "_data" / "researchers_former.json"
CONFIG = ROOT / "tools" / "find_papers.json"
SEEN = ROOT / "tools" / "papers_seen.json"

API = "https://api.openalex.org/works"
FIELDS = ("id,ids,doi,title,type,publication_date,publication_year,"
          "primary_location,locations,authorships,biblio,primary_topic")
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
PREPRINT_VENUES = {"arxiv", "biorxiv", "medrxiv", "research square", "ssrn"}
BIBTEX_TYPES = {"preprint": "misc", "book-chapter": "incollection",
                "conference-paper": "inproceedings"}


def fetch(url):
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        url += "&api_key=" + urllib.parse.quote(key)
    request = urllib.request.Request(url, headers={"User-Agent": "biophys-turin-paper-finder"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    return None


def normalize(text):
    """Lower-case letters and digits only, accents removed: for comparing titles."""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def clean(text):
    text = re.sub(r"<[^>]+>", "", html.unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip().rstrip(".")


def identifiers(text):
    """DOIs and arXiv IDs found in a string (lower-case)."""
    text = (text or "").lower()
    found = {doi.rstrip(".") for doi in re.findall(r"10\.\d{4,9}/[^\s?#\"]+", text)}
    found |= set(re.findall(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", text))
    found |= set(re.findall(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", text))
    return found


def work_identifiers(work):
    ids = identifiers(work.get("doi"))
    for location in work.get("locations") or []:
        ids |= identifiers(location.get("landing_page_url"))
    return ids


def venue(work):
    source = (work.get("primary_location") or {}).get("source") or {}
    name = clean(source.get("display_name"))
    if source.get("type") == "repository":
        name = re.sub(r"\s*\(.*\)$", "", name)  # "arXiv (Cornell University)" -> "arXiv"
    return name


def is_preprint(work):
    return work["type"] == "preprint" or venue(work).lower() in PREPRINT_VENUES


def orcid_id(url):
    return (url or "").rstrip("/").rsplit("/", 1)[-1]


def to_entry(work, names_by_orcid):
    """Convert an OpenAlex work to the papers.json format."""
    authors = []
    for authorship in work["authorships"]:
        author = authorship["author"]
        authors.append(names_by_orcid.get(orcid_id(author.get("orcid")), author.get("display_name") or ""))
    entry = {
        "type": BIBTEX_TYPES.get(work["type"], "article"),
        "title": clean(work["title"]),
        "link": work.get("doi") or (work.get("primary_location") or {}).get("landing_page_url") or work["id"],
        "author": ", ".join(a for a in authors if a),
        "year": str(work["publication_year"]),
    }
    date = work.get("publication_date") or ""
    if len(date) >= 7:
        entry["month"] = MONTHS[int(date[5:7]) - 1]
    entry["booktitle" if entry["type"] in ("incollection", "inproceedings") else "journal"] = venue(work)
    biblio = work.get("biblio") or {}
    if biblio.get("volume"):
        entry["volume"] = biblio["volume"]
    if biblio.get("issue"):
        entry["number"] = biblio["issue"]
    if biblio.get("first_page"):
        last = biblio.get("last_page")
        entry["pages"] = biblio["first_page"] + (f"-{last}" if last and last != biblio["first_page"] else "")
    if work.get("doi"):
        entry["doi"] = work["doi"].replace("https://doi.org/", "")
    return entry


def recent_works(orcid, since):
    page_filter = f"author.orcid:{orcid},from_publication_date:{since}"
    cursor = "*"
    while cursor:
        page = fetch(f"{API}?filter={page_filter}&per-page=100&cursor={cursor}&select={FIELDS}")
        yield from page["results"]
        cursor = page["meta"].get("next_cursor")
        time.sleep(0.2)


def subfield(work):
    return ((work.get("primary_topic") or {}).get("subfield") or {}).get("display_name", "")


def is_group_work(work, config, current, affiliation):
    """Right type and subfield, and a current member is listed with a group affiliation."""
    if work["type"] not in config["include_types"] or subfield(work) in config["exclude_subfields"]:
        return False
    for authorship in work["authorships"]:
        if orcid_id(authorship["author"].get("orcid")) not in current:
            continue
        places = [i["display_name"] for i in authorship["institutions"]]
        places += authorship.get("raw_affiliation_strings") or []
        if affiliation.search(" ".join(places)):
            return True
    return False


def is_published_version(work, existing):
    """True if work is the journal version of a preprint entry already on the site."""
    existing_is_preprint = (existing.get("type") == "misc"
                            or (existing.get("journal") or "").lower() in PREPRINT_VENUES)
    return existing_is_preprint and not is_preprint(work)


def find(config, papers, seen):
    """Return (new_works, published_preprints); both are lists of (work, member names)."""
    members = json.loads(MEMBERS.read_text(encoding="utf-8"))
    former = json.loads(FORMER.read_text(encoding="utf-8"))
    names_by_orcid = {orcid_id(m["socials"]["orcid"]): m["name"]
                      for m in members + former if (m.get("socials") or {}).get("orcid")}
    current = {orcid_id(m["socials"]["orcid"]) for m in members if (m.get("socials") or {}).get("orcid")}

    known_ids = set()
    for paper in papers:
        known_ids |= identifiers(paper.get("link")) | identifiers(paper.get("doi"))
    known_titles = {normalize(p["title"]): p for p in papers}
    seen_ids = {s["openalex"] for s in seen}
    affiliation = re.compile(config["affiliation_pattern"], re.IGNORECASE)
    since = f"{datetime.date.today().year - config['lookback_years']}-01-01"

    works = {}
    for orcid in sorted(current):
        for work in recent_works(orcid, since):
            works[work["id"]] = work

    candidates = {}
    published = []
    for work in works.values():
        if work["id"] in seen_ids or not work.get("title"):
            continue
        if not is_group_work(work, config, current, affiliation) or work_identifiers(work) & known_ids:
            continue
        who = sorted({names_by_orcid[orcid_id(a["author"]["orcid"])] for a in work["authorships"]
                      if orcid_id(a["author"].get("orcid")) in names_by_orcid})
        title = normalize(work["title"])
        if title in known_titles:
            if is_published_version(work, known_titles[title]):
                published.append((work, who))
            continue
        # Keep one version per title, preferring the published one over a preprint
        other = candidates.get(title)
        if other is None or (is_preprint(other[0]) and not is_preprint(work)):
            candidates[title] = (work, who)
        seen.append({"openalex": work["id"], "title": clean(work["title"])})

    for work, _ in published:
        seen.append({"openalex": work["id"], "title": clean(work["title"])})
    new = sorted(candidates.values(), key=lambda c: c[0].get("publication_date") or "", reverse=True)
    return [(to_entry(w, names_by_orcid), w, who) for w, who in new], published


def insert_at_top(entries):
    """Add entries at the start of papers.json without reformatting the rest of the file."""
    raw = PAPERS.read_text(encoding="utf-8")
    start = raw.index("[") + 1
    block = ",\n".join("  " + json.dumps(e, indent=2, ensure_ascii=False).replace("\n", "\n  ") for e in entries)
    updated = raw[:start] + "\n" + block + ",\n  " + raw[start:].lstrip()
    json.loads(updated)  # must still be valid JSON
    PAPERS.write_text(updated, encoding="utf-8")


def pr_body(new, published):
    lines = []
    if new:
        lines += ["These papers by current members were found on [OpenAlex](https://openalex.org) "
                  "and added to the top of `_data/papers.json`.", "",
                  "**To review:** delete the entries that are not group papers (or edit them on this branch), "
                  "check titles, author names and venue names (OpenAlex sometimes gets these slightly wrong), "
                  "then merge. Deleted papers are not proposed again, "
                  "because they are recorded in `tools/papers_seen.json`.", "",
                  "| Year | Paper | Venue | Members | OpenAlex subfield |", "| --- | --- | --- | --- | --- |"]
        for entry, work, who in new:
            title = entry["title"].replace("|", "\\|")
            venue_name = entry.get("journal") or entry.get("booktitle", "")
            lines.append(f"| {entry['year']} | [{title}]({entry['link']}) | {venue_name} "
                         f"| {', '.join(who)} | {subfield(work)} |")
    if published:
        lines += ["", "**Preprints on the site that now have a published version** "
                  "(not changed automatically; update the entry if you want):", ""]
        for work, _ in published:
            lines.append(f"- [{clean(work['title'])}]({work.get('doi') or work['id']}) in {venue(work)}")
    lines += ["", "_Opened by the weekly **Find new papers** workflow (`tools/find_papers.py`)._"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--body", help="write a pull request description to this file")
    parser.add_argument("--dry-run", action="store_true", help="print what would be proposed, change nothing")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    papers = json.loads(PAPERS.read_text(encoding="utf-8"))
    seen = json.loads(SEEN.read_text(encoding="utf-8")) if SEEN.exists() else []

    new, published = find(config, papers, seen)
    for entry, _, who in new:
        print(f"NEW  {entry['year']}  {entry['title'][:80]}  [{entry.get('journal') or entry.get('booktitle')}]  ({', '.join(who)})")
    for work, _ in published:
        print(f"PUBLISHED  {clean(work['title'])[:80]}  [{venue(work)}]")
    if not new and not published:
        print("Nothing new.")
        return
    if args.dry_run:
        return
    if new:
        insert_at_top([entry for entry, _, _ in new])
    SEEN.write_text(json.dumps(seen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.body:
        Path(args.body).write_text(pr_body(new, published), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
