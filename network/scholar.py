from scholarly import scholarly


authors = list(scholarly.search_author('Filippo Valle'))
for author in authors:
    if "University of Turin" in author['affiliation']:
        break
scholarly.pprint(author)

scholarly.fill(author, sections=['basics', 'publications'])

for paper in author['publications']:
    title = paper['bib']['title']
    scholarly.fill(paper)
    print(title)
    print(paper["bib"]["author"].split(' and '))
