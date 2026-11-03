"""Propose new group papers for _data/papers.json.

Asks OpenAlex (https://openalex.org) for recent works by the current members
listed in _data/researchers.json (those with an ORCID under "socials"), keeps
the ones that look like group papers, and adds them to the top of
_data/papers.json for a person to review in a pull request.

A work is proposed when all of these hold:
  * its type is in "include_types" and its subfield is not in
    "exclude_subfields" (tools/find_papers.json);
  * at least one current member is listed on it with an affiliation containing
    one of "affiliations" (this filters out namesakes and members' work done
    elsewhere);
  * it is not already in papers.json (same DOI, arXiv ID or title) and has not
    been proposed before (tools/papers_seen.json).

Every proposed work is recorded in tools/papers_seen.json, so a paper deleted
during review is not proposed again.

Usage: python tools/find_papers.py [--dry-run] [--pr-body > body.md]
Progress goes to stderr; with --pr-body a pull request description is printed
to stdout. Only the Python standard library is needed.
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


# --- Helpers ------------------------------------------------------------------

def read_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


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
    return " ".join(text.split()).rstrip(".")


def identifiers(text):
    """DOIs and arXiv IDs found in a string (lower-case)."""
    text = (text or "").lower()
    found = {doi.rstrip(".") for doi in re.findall(r"10\.\d{4,9}/[^\s?#\"]+", text)}
    found |= set(re.findall(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", text))
    found |= set(re.findall(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", text))
    return found


def orcid_id(url):
    return (url or "").rstrip("/").rsplit("/", 1)[-1]


# --- Reading OpenAlex works ---------------------------------------------------

def work_identifiers(work):
    ids = identifiers(work.get("doi"))
    for location in work.get("locations") or []:
        ids |= identifiers(location.get("landing_page_url"))
    return ids


def venue(work):
    source = (work.get("primary_location") or {}).get("source") or {}
    name = clean(source.get("display_name"))
    if source.get("type") == "repository" and name.endswith(")"):
        name = name.split(" (")[0]  # "arXiv (Cornell University)" -> "arXiv"
    return name


def subfield(work):
    return ((work.get("primary_topic") or {}).get("subfield") or {}).get("display_name", "")


def is_preprint(work):
    return work["type"] == "preprint" or venue(work).lower() in PREPRINT_VENUES


def has_group_affiliation(authorship, affiliations):
    places = [i["display_name"] for i in authorship["institutions"]]
    places += authorship.get("raw_affiliation_strings") or []
    text = " ".join(places).lower()
    return any(name.lower() in text for name in affiliations)


def is_group_work(work, config, current):
    """Right type and subfield, and a current member is listed with a group affiliation."""
    if work["type"] not in config["include_types"] or subfield(work) in config["exclude_subfields"]:
        return False
    return any(orcid_id(a["author"].get("orcid")) in current
               and has_group_affiliation(a, config["affiliations"])
               for a in work["authorships"])


def is_published_version(work, existing):
    """True if work is the journal version of a preprint entry already on the site."""
    existing_is_preprint = (existing.get("type") == "misc"
                            or (existing.get("journal") or "").lower() in PREPRINT_VENUES)
    return existing_is_preprint and not is_preprint(work)


def to_entry(work, names_by_orcid):
    """Convert an OpenAlex work to the papers.json format."""
    authors = [names_by_orcid.get(orcid_id(a["author"].get("orcid")), a["author"].get("display_name") or "")
               for a in work["authorships"]]
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
    first, last = biblio.get("first_page"), biblio.get("last_page")
    if first:
        entry["pages"] = f"{first}-{last}" if last and last != first else first
    if work.get("doi"):
        entry["doi"] = work["doi"].replace("https://doi.org/", "")
    return entry


# --- Finding candidates -------------------------------------------------------

def load_members():
    """Return ({orcid: site name} for current and former members, {orcids of current members})."""
    current = read_json(MEMBERS)
    everyone = current + read_json(FORMER)
    names = {orcid_id(m["socials"]["orcid"]): m["name"] for m in everyone if (m.get("socials") or {}).get("orcid")}
    current_ids = {orcid_id(m["socials"]["orcid"]) for m in current if (m.get("socials") or {}).get("orcid")}
    return names, current_ids


def recent_works(orcids, since):
    """All works by these ORCIDs published since the given date, by OpenAlex ID."""
    works = {}
    for orcid in sorted(orcids):
        cursor = "*"
        while cursor:
            page = fetch(f"{API}?filter=author.orcid:{orcid},from_publication_date:{since}"
                         f"&per-page=100&cursor={cursor}&select={FIELDS}")
            works.update((w["id"], w) for w in page["results"])
            cursor = page["meta"].get("next_cursor")
            time.sleep(0.2)
    return works


def find(config, papers, seen):
    """Return (new, published).

    new: [(entry, work, member names)] for works to add, newest first.
    published: [work] for journal versions of preprints already on the site.
    Every returned work is appended to seen.
    """
    names, current = load_members()
    known_ids = set().union(*(identifiers(p.get("link")) | identifiers(p.get("doi")) for p in papers))
    known_titles = {normalize(p["title"]): p for p in papers}
    seen_ids = {s["openalex"] for s in seen}
    since = f"{datetime.date.today().year - config['lookback_years']}-01-01"

    candidates = {}  # normalized title -> work, keeping the published version over a preprint
    published = []
    for work in recent_works(current, since).values():
        if work["id"] in seen_ids or not work.get("title") or not is_group_work(work, config, current):
            continue
        if work_identifiers(work) & known_ids:
            continue
        title = normalize(work["title"])
        if title in known_titles:
            if is_published_version(work, known_titles[title]):
                published.append(work)
            continue
        if title not in candidates or (is_preprint(candidates[title]) and not is_preprint(work)):
            candidates[title] = work

    proposed = sorted(candidates.values(), key=lambda w: w.get("publication_date") or "", reverse=True)
    for work in proposed + published:
        seen.append({"openalex": work["id"], "title": clean(work["title"])})
    new = []
    for work in proposed:
        who = sorted({names[orcid_id(a["author"].get("orcid"))] for a in work["authorships"]
                      if orcid_id(a["author"].get("orcid")) in names})
        new.append((to_entry(work, names), work, who))
    return new, published


# --- Output -------------------------------------------------------------------

def insert_at_top(entries):
    """Add entries at the start of papers.json without reformatting the rest of the file."""
    with open(PAPERS, encoding="utf-8") as file:
        raw = file.read()
    start = raw.index("[") + 1
    block = ",\n".join("  " + json.dumps(e, indent=2, ensure_ascii=False).replace("\n", "\n  ") for e in entries)
    updated = raw[:start] + "\n" + block + ",\n  " + raw[start:].lstrip()
    json.loads(updated)  # must still be valid JSON
    with open(PAPERS, "w", encoding="utf-8") as file:
        file.write(updated)


def save_seen(seen):
    with open(SEEN, "w", encoding="utf-8") as file:
        json.dump(seen, file, indent=2, ensure_ascii=False)
        file.write("\n")


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
        lines += [f"- [{clean(w['title'])}]({w.get('doi') or w['id']}) in {venue(w)}" for w in published]
    lines += ["", "_Opened by the weekly **Find new papers** workflow (`tools/find_papers.py`)._"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print what would be proposed, change nothing")
    parser.add_argument("--pr-body", action="store_true", help="print a pull request description to stdout")
    args = parser.parse_args()

    seen = read_json(SEEN) if SEEN.exists() else []
    new, published = find(read_json(CONFIG), read_json(PAPERS), seen)
    for entry, _, who in new:
        venue_name = entry.get("journal") or entry.get("booktitle")
        print(f"NEW  {entry['year']}  {entry['title'][:80]}  [{venue_name}]  ({', '.join(who)})", file=sys.stderr)
    for work in published:
        print(f"PUBLISHED  {clean(work['title'])[:80]}  [{venue(work)}]", file=sys.stderr)
    if not new and not published:
        print("Nothing new.", file=sys.stderr)
        return
    if args.dry_run:
        return
    if new:
        insert_at_top([entry for entry, _, _ in new])
    save_seen(seen)
    if args.pr_body:
        print(pr_body(new, published), end="")


if __name__ == "__main__":
    main()
