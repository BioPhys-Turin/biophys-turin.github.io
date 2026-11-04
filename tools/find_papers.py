"""Propose new group papers and updates for _data/papers.json.

Asks OpenAlex (https://openalex.org) for recent works by the current members
listed in _data/researchers.json (those with an ORCID under "socials"), and
changes _data/papers.json for a person to review in a pull request:

New papers are added at the top when all of these hold:
  * the work's type is in "include_types" and its subfield is not in
    "exclude_subfields" (tools/find_papers.json);
  * at least one current member is listed on it with an affiliation containing
    one of "affiliations" (this filters out namesakes and members' work done
    elsewhere);
  * it is not already in papers.json (same DOI, arXiv ID or title) and has not
    been proposed before (tools/papers_seen.json).
Every proposed work is recorded in tools/papers_seen.json, so a paper deleted
during review is not proposed again.

Recent entries that are incomplete are updated:
  * a preprint whose published version appears on OpenAlex becomes the
    journal article;
  * an article missing its volume, issue or pages gets them from Crossref
    (https://www.crossref.org), which usually has them before OpenAlex.
Titles and author lists are never changed. Only entries from the last
"lookback_years" years are checked, so this costs a few requests per run.

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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "_data" / "papers.json"
MEMBERS = ROOT / "_data" / "researchers.json"
FORMER = ROOT / "_data" / "researchers_former.json"
CONFIG = ROOT / "tools" / "find_papers.json"
SEEN = ROOT / "tools" / "papers_seen.json"

OPENALEX = "https://api.openalex.org/works"
CROSSREF = "https://api.crossref.org/works/"
FIELDS = ("id,ids,doi,title,type,publication_date,publication_year,"
          "primary_location,locations,authorships,biblio,primary_topic")
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
PREPRINT_VENUES = {"arxiv", "biorxiv", "medrxiv", "research square", "ssrn"}
# OpenAlex and Crossref work types -> BibTeX entry types (anything else is "article")
BIBTEX_TYPES = {"preprint": "misc", "book-chapter": "incollection", "conference-paper": "inproceedings",
                "proceedings-article": "inproceedings"}
PUBLISHED_CROSSREF_TYPES = {"journal-article", "proceedings-article", "book-chapter"}
BIBLIO_FIELDS = ("volume", "number", "pages")


# --- Helpers ------------------------------------------------------------------

def read_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def fetch(url):
    """GET a JSON API; None if the record does not exist."""
    key = os.environ.get("OPENALEX_API_KEY")
    if key and url.startswith(OPENALEX):
        url += "&api_key=" + urllib.parse.quote(key)
    request = urllib.request.Request(url, headers={"User-Agent": "biophys-turin-paper-finder"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if attempt == 3:
                raise
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


def entry_identifiers(entry):
    return identifiers(entry.get("link")) | identifiers(entry.get("doi"))


def orcid_id(url):
    return (url or "").rstrip("/").rsplit("/", 1)[-1]


def venue_key(entry):
    return "booktitle" if entry["type"] in ("incollection", "inproceedings") else "journal"


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


def is_preprint_entry(entry):
    return entry.get("type") == "misc" or (entry.get("journal") or "").lower() in PREPRINT_VENUES


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
    entry[venue_key(entry)] = venue(work)
    biblio = work.get("biblio") or {}
    first, last = biblio.get("first_page"), biblio.get("last_page")
    for key, value in (("volume", biblio.get("volume")), ("number", biblio.get("issue")),
                       ("pages", f"{first}-{last}" if first and last and last != first else first)):
        if value:
            entry[key] = value
    if work.get("doi"):
        entry["doi"] = work["doi"].replace("https://doi.org/", "")
    return entry


# --- Crossref -----------------------------------------------------------------

def published_doi(entry):
    """The entry's DOI if it is a published (non-preprint) one."""
    if is_preprint_entry(entry):
        return None
    dois = [found for found in sorted(entry_identifiers(entry))
            if found.startswith("10.") and not found.startswith("10.48550/")]
    return dois[0] if dois else None


def crossref(doi):
    """Publication details of a DOI from Crossref, or None if it is not a published work."""
    record = fetch(CROSSREF + urllib.parse.quote(doi, safe="/"))
    message = (record or {}).get("message") or {}
    if message.get("type") not in PUBLISHED_CROSSREF_TYPES:
        return None
    date = ((message.get("issued") or {}).get("date-parts") or [[None]])[0]
    details = {
        "type": BIBTEX_TYPES.get(message["type"], "article"),
        "venue": clean((message.get("container-title") or [""])[0]),
        "volume": message.get("volume"),
        "number": message.get("issue"),
        "pages": message.get("page") or message.get("article-number"),
        "year": str(date[0]) if date[0] else None,
        "month": MONTHS[date[1] - 1] if len(date) > 1 and date[1] else None,
        "doi": message["DOI"].lower(),
    }
    return {key: value for key, value in details.items() if value}


# --- Finding new papers and updates -------------------------------------------

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
            page = fetch(f"{OPENALEX}?filter=author.orcid:{orcid},from_publication_date:{since}"
                         f"&per-page=100&cursor={cursor}&select={FIELDS}")
            works.update((w["id"], w) for w in page["results"])
            cursor = page["meta"].get("next_cursor")
            time.sleep(0.2)
    return works


def find_new(works, papers, seen, config, names, current):
    """New group papers as [(entry, work, member names)], newest first; appends them to seen."""
    known_ids = set().union(*(entry_identifiers(p) for p in papers))
    known_titles = {normalize(p["title"]) for p in papers}
    seen_ids = {s["openalex"] for s in seen}

    candidates = {}  # normalized title -> work, keeping the published version over a preprint
    for work in works.values():
        if work["id"] in seen_ids or not work.get("title") or not is_group_work(work, config, current):
            continue
        title = normalize(work["title"])
        if work_identifiers(work) & known_ids or title in known_titles:
            continue
        if title not in candidates or (is_preprint(candidates[title]) and not is_preprint(work)):
            candidates[title] = work

    new = []
    for work in sorted(candidates.values(), key=lambda w: w.get("publication_date") or "", reverse=True):
        seen.append({"openalex": work["id"], "title": clean(work["title"])})
        who = sorted({names[orcid_id(a["author"].get("orcid"))] for a in work["authorships"]
                      if orcid_id(a["author"].get("orcid")) in names})
        new.append((to_entry(work, names), work, who))
    return new


def matching_work(entry, works):
    """The OpenAlex work that is the same paper as entry, preferring a published version."""
    ids, title = entry_identifiers(entry), normalize(entry["title"])
    matches = [w for w in works.values() if work_identifiers(w) & ids or normalize(w.get("title")) == title]
    matches.sort(key=is_preprint)
    return matches[0] if matches else None


def work_doi(work):
    return work["doi"].replace("https://doi.org/", "") if work and work.get("doi") else None


def doi_to_check(entry, works):
    """DOI to look up for an incomplete entry: its published version for a preprint, else its own DOI."""
    if is_preprint_entry(entry):
        work = matching_work(entry, works)
        return work_doi(work) if work and not is_preprint(work) else None
    return published_doi(entry) or work_doi(matching_work(entry, works))


def published_version(entry, details):
    """Fields that turn a preprint entry into the published paper (title and authors are kept)."""
    changes = {"type": details["type"], "link": "https://doi.org/" + details["doi"], "doi": details["doi"]}
    changes.update({key: details[key] for key in ("year", "month", *BIBLIO_FIELDS) if key in details})
    changes[venue_key(changes)] = details.get("venue", "")
    return changes


def update_entry(entry, works):
    """Fill in publication details of an incomplete entry in place; return {field: new value}."""
    doi = doi_to_check(entry, works)
    details = crossref(doi) if doi else None
    if not details:
        return {}
    if is_preprint_entry(entry):
        changes = published_version(entry, details)
        entry.pop(venue_key(entry), None)  # "journal": "arXiv" may become "booktitle"
    else:
        changes = {key: details[key] for key in BIBLIO_FIELDS if key in details and not entry.get(key)}
    changes = {key: value for key, value in changes.items() if entry.get(key) != value}
    entry.update(changes)
    return changes


def find_updates(works, papers, since_year):
    """Update recent incomplete entries in place; return [(entry, changes)]."""
    updates = []
    for entry in papers:
        if not entry.get("year", "").isdigit() or int(entry["year"]) < since_year:
            continue
        if not is_preprint_entry(entry) and all(entry.get(key) for key in ("volume", "pages")):
            continue
        changes = update_entry(entry, works)
        if changes:
            updates.append((entry, changes))
    return updates


# --- Output -------------------------------------------------------------------

def pr_body(new, updates):
    lines = []
    if new:
        lines += ["**New papers** by current members, found on [OpenAlex](https://openalex.org) "
                  "and added to the top of `_data/papers.json`:", "",
                  "| Year | Paper | Venue | Members | OpenAlex subfield |", "| --- | --- | --- | --- | --- |"]
        for entry, work, who in new:
            title = entry["title"].replace("|", "\\|")
            lines.append(f"| {entry['year']} | [{title}]({entry['link']}) | {entry.get(venue_key(entry), '')} "
                         f"| {', '.join(who)} | {subfield(work)} |")
        lines += ["", "Delete the entries that are not group papers, and check titles, author names and venue "
                  "names (OpenAlex sometimes gets these slightly wrong). Deleted papers are not proposed again, "
                  "because they are recorded in `tools/papers_seen.json`.", ""]
    if updates:
        lines += ["**Updated entries** (publication details from [Crossref](https://www.crossref.org); "
                  "titles and authors unchanged):", ""]
        for entry, changes in updates:
            details = ", ".join(f"{key}: {value}" for key, value in changes.items())
            lines.append(f"- [{entry['title']}]({entry['link']}): {details}")
        lines.append("")
    lines += ["_Opened by the weekly **Find new papers** workflow (`tools/find_papers.py`)._"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print what would change, change nothing")
    parser.add_argument("--pr-body", action="store_true", help="print a pull request description to stdout")
    args = parser.parse_args()

    config = read_json(CONFIG)
    papers = read_json(PAPERS)
    seen = read_json(SEEN) if SEEN.exists() else []
    since_year = datetime.date.today().year - config["lookback_years"]
    names, current = load_members()
    works = recent_works(current, f"{since_year}-01-01")

    new = find_new(works, papers, seen, config, names, current)
    updates = find_updates(works, papers, since_year)
    for entry, _, who in new:
        print(f"NEW      {entry['year']}  {entry['title'][:80]}  [{entry.get(venue_key(entry))}]  ({', '.join(who)})",
              file=sys.stderr)
    for entry, changes in updates:
        print(f"UPDATED  {entry['title'][:80]}  {changes}", file=sys.stderr)
    if not new and not updates:
        print("Nothing new.", file=sys.stderr)
        return
    if args.dry_run:
        return
    write_json(PAPERS, [entry for entry, _, _ in new] + papers)
    write_json(SEEN, seen)
    if args.pr_body:
        print(pr_body(new, updates), end="")


if __name__ == "__main__":
    main()
