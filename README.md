# Biophysics Research Site

Welcome to the Biophys research site repository of the Biophysics group at the University of Turin (Unito) and the National Institute for Nuclear Physics (INFN). This repository hosts the source code and content for our research website.

## About

Our research site serves as a platform to showcase our group's projects, publications, team members, and other related information in the field of biophysics.

## Website

The live version of this research site is hosted on GitHub Pages and can be accessed [here](https://biophys-turin.github.io/).

## How to edit

Members and papers live in plain JSON files under `_data/`. Commit a change to `main` and GitHub Pages rebuilds the site within a minute or two.

- **Add a member:** add their profile to `_data/researchers.json` and their photo to `images/profiles/` (square JPEG, about 400×400 px, well under 100 KB). Each key under `socials` needs a matching icon in `images/icons/<key>.svg`; available: `mail`, `github`, `linkedin`, `twitter`, `x`, `bluesky`, `mastodon`, `pixelfed`, `substack`, `orcid`, `personal-page`, `publications`. Add their ORCID as `"orcid": "https://orcid.org/0000-…"` under `socials` if they have one.
- **Move a member to former members:** move their profile from `_data/researchers.json` to `_data/researchers_former.json`.
- **Add a paper:** add an entry to `_data/papers.json`. Papers are listed newest year first; within a year they keep the order of the file, so put new papers at the top. The five most recent also appear on the home page. Separate authors with `", "`. The BibTeX shown by the Cite button is generated from the entry's fields.
- **New papers are also found automatically:** every Monday the *Find new papers* Action looks on [OpenAlex](https://openalex.org) for recent work by current members with an ORCID, and opens a pull request "New papers to review" adding them to `_data/papers.json`. Delete the entries that aren't group papers, fix any names or venues, and merge; deleted papers won't be proposed again. It only proposes papers where a current member is listed with a Turin affiliation; affiliations, topics to skip and other settings are in `tools/find_papers.json`. The same pull request also completes recent entries: preprints that have since been published become the journal article, and articles missing their volume or pages get them from Crossref. You can also run it by hand from the Actions tab.
- **News:** the News page embeds an Elfsight widget; its content is managed from the Elfsight dashboard, not from this repository.
- **Collaboration network:** the graph on the About page (`network/network.html`) is rebuilt by a GitHub Action whenever the researchers or papers files change. To rebuild it locally: `pip install -r network/requirements.txt && python network/network.py`.
- For everything else ask either Federico or Filippo.

## How the site is built

The site is built by [Jekyll](https://jekyllrb.com/), which GitHub Pages runs automatically.

| Path | What it is |
| --- | --- |
| `index.html`, `about.html`, `researchers.html`, `papers.html`, `news.html`, `404.html` | The pages. The block between `---` lines at the top sets the title, URL and description. |
| `_layouts/default.html` | The page skeleton shared by every page |
| `_includes/` | Shared pieces: `<head>`, navigation, footer, social links, paper entry, BibTeX template |
| `_data/` | The content (current and former members, papers) |
| `styles.css`, `scripts/`, `images/`, `css/` | Static assets, served as-is. All colours are variables at the top of `styles.css`, with a light and a dark set; the site follows the visitor's system setting |
| `_config.yml` | Site settings |

### Previewing locally (optional)

With Ruby installed:

```sh
bundle install
bundle exec jekyll serve   # then open http://localhost:4000
```

Or with Docker only:

```sh
docker run --rm -it -p 4000:4000 -v "$PWD":/srv -w /srv ruby:3.3 \
  bash -c "bundle install && bundle exec jekyll serve --host 0.0.0.0"
```

## License
© 2024–2026 BioPhys Turin. This work is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
