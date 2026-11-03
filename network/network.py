"""Build the collaboration network shown on the About page.

Reads researchers and papers from the JSON data files and writes
network/network.html from network/network.html.template.
Run from anywhere: `python network/network.py`.
"""
import json
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent

SUPERVISORS = ["Michele Caselle", "Matteo Osella"]

# Node groups (used for colouring in the template's colour scale)
GROUP_CURRENT, GROUP_FORMER, GROUP_SUPERVISOR, GROUP_EXTERNAL, GROUP_PAPER, GROUP_THESIS, GROUP_OTHER = range(1, 8)


def load_json(relative_path):
    with open(ROOT / relative_path, encoding="utf-8") as f:
        return json.load(f)


class Network:
    def __init__(self, current, former):
        self.current = set(current)
        self.former = set(former)
        self.authors = {}
        self.G = nx.Graph()
        self.total_nodes = -1

    def add_author(self, auth) -> int:
        if auth not in self.authors:
            self.total_nodes += 1
            self.G.add_node(self.total_nodes, name=auth, kind="auth")
            self.authors[auth] = self.total_nodes
        return self.authors[auth]

    def add_paper(self, paper, authors: list, doi="", link="") -> None:
        self.total_nodes += 1
        paper_idx = self.total_nodes
        self.G.add_node(paper_idx, name=paper, doi=doi, link=link, kind="paper")
        for author in authors:
            self.G.add_edge(self.add_author(author), paper_idx)

    def add_thesis(self, paper, authors: list, link="") -> None:
        self.total_nodes += 1
        paper_idx = self.total_nodes
        self.G.add_node(paper_idx, name=paper, link=link, kind="thesis")
        for author in authors:
            self.G.add_edge(self.add_author(author), paper_idx)

    @staticmethod
    def _get_scholar_url(node):
        return "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q=" + "+".join(node[1]["name"].split(" "))

    def _get_hyperlink(self, node):
        kind = node[1]["kind"]
        if kind == "auth":
            return self._get_scholar_url(node)
        if kind == "paper" and node[1]["doi"]:
            return "https://doi.org/" + node[1]["doi"]
        return node[1]["link"]

    def _get_num_kind(self, node):
        kind = node[1]["kind"]
        if kind == "auth":
            name = node[1]["name"]
            if name in SUPERVISORS:
                return GROUP_SUPERVISOR
            if name in self.current:
                return GROUP_CURRENT
            if name in self.former:
                return GROUP_FORMER
            return GROUP_EXTERNAL
        if kind == "paper":
            return GROUP_PAPER
        if kind == "thesis":
            return GROUP_THESIS
        return GROUP_OTHER

    def _get_group(self):
        return [self._get_num_kind(n) for n in self.G.nodes(data=True)]

    def __repr__(self):
        return json.dumps({"x": {"links": {
            "source": [e[0] for e in self.G.edges],
            "target": [e[1] for e in self.G.edges],
            "value": [1 for e in self.G.edges],
            "colour": ["#666" for e in self.G.edges],
        }, "nodes": {
            "name": [n[1]["name"] for n in self.G.nodes(data=True)],
            "group": self._get_group(),
            "hyperlink": [self._get_hyperlink(n) for n in self.G.nodes(data=True)],
        },
            "options": {"NodeID": "name",
                        "Group": "group", "colourScale": "d3.scaleOrdinal()\n            .domain([\"1\", \"2\", \"3\", \"4\", \"5\", \"6\"])\n            .range(" + json.dumps(["#a361c7", "#5ba962", "#c75b89", "#ac973e", "#648ace", "#cb6042"]) + ");",
                        "fontSize": 12,
                        "fontFamily": "serif",
                        "clickTextSize": 30,
                        "linkDistance": 50,
                        "linkWidth": "function(d) { return Math.sqrt(d.value); }",
                        "charge": -30,
                        "opacity": 1,
                        "zoom": True,
                        "legend": False,
                        "arrows": False,
                        "nodesize": False,
                        "radiusCalculation": " Math.sqrt(d.nodesize)+6",
                        "bounded": False,
                        "opacityNoHover": 0,
                        "clickAction": "window.open(d.hyperlink)"},
        },
            "evals": [],
            "jsHooks": []})


def main():
    current = [r["name"] for r in load_json("_data/researchers.json")]
    former = [r["name"] for r in load_json("_data/researchers_former.json")]
    net = Network(current, former)

    for paper in load_json("_data/papers.json"):
        authors = [a.strip() for a in paper["author"].split(",") if a.strip()]
        net.add_paper(paper["title"].strip(), authors, doi=paper.get("doi", ""), link=paper["link"])

    template = (ROOT / "network/network.html.template").read_text(encoding="utf-8")
    (ROOT / "network/network.html").write_text(template.replace("TOREPLACE_NETWORK", str(net)), encoding="utf-8")
    print(f"Wrote network with {len(net.authors)} authors and {net.G.number_of_nodes() - len(net.authors)} papers")


if __name__ == "__main__":
    main()
