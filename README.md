# Biophysics Research Site

Welcome to the Biophys research site repository of the Biophysics group at the University of Turin (Unito) and the National Institute for Nuclear Physics (INFN). This repository hosts the source code and content for our research website.

## About

Our research site serves as a platform to showcase our group's projects, publications, team members, and other related information in the field of biophysics.

## Website

The live version of this research site is hosted on GitHub Pages and can be accessed [here](https://biophys-turin.github.io/).

## How to edit

- Add a member: add their profile to `files/researchers.json` and their photo to `images/profiles/` (square JPEG, about 400×400 px, well under 100 KB)
- Move a member to former members: move their profile from `files/researchers.json` to `files/researchers-former.json`
- Add a paper: add an entry to `papers/paper.json`
- Add a news item: add an entry to `files/news.json`
- The collaboration network on the About page (`network/network.html`) is rebuilt automatically by a GitHub Action whenever the researchers or papers files change. To rebuild it locally: `pip install -r network/requirements.txt && python network/network.py`
- For everything else ask either Federico or Filippo

## License
© 2024–2026 BioPhys Turin. This work is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
