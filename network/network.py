import networkx as nx
import json

G = nx.Graph()

supervisors = ["Michele Caselle", "Matteo Osella"]
group = []
former = []

  
class Network:
    def __init__(self):
        self.authors = {}
        self.G = nx.Graph()
        self.total_nodes = -1
        
    def add_author(self, auth)->int:
        if auth in self.authors:
            return self.authors[auth]
        else:
            self.total_nodes+=1
            self.G.add_node(self.total_nodes, name=auth, kind="auth")
            self.authors[auth]=self.total_nodes
            return self.total_nodes
            
    def add_paper(self, paper, authors:list, doi="", link="")->None:
        self.total_nodes+=1
        paper_idx = self.total_nodes
        self.G.add_node(paper_idx, name=paper, doi=doi, link=link, kind="paper")
        for author in authors:
            auth_idx = self.add_author(author)
            self.G.add_edge(auth_idx, paper_idx)
            
    def add_thesis(self, paper, authors:list, link="")->None:
        self.total_nodes+=1
        paper_idx = self.total_nodes
        self.G.add_node(paper_idx, name=paper, link=link, kind="thesis")
        for author in authors:
            auth_idx = self.add_author(author)
            self.G.add_edge(auth_idx, paper_idx)
        
    def _get_scolar_url(self, node):
        return "https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q="+'+'.join(node[1]["name"].split(" "))

    def _get_hyperlink(self, node):
        if node[1]["kind"]=="auth":
            return self._get_scolar_url(node)
        if node[1]["kind"]=="paper":
            if node[1]["doi"]!="":
                return "https://doi.org/"+node[1]["doi"]
            else:
                return node[1]["link"]
        if node[1]["kind"]=="thesis":
            return node[1]["link"]
        
    def _get_num_kind(self, node):
        global group
        if node[1]["kind"]=="auth":
            if node[1]["name"] in group:
                return 1
            if node[1]["name"] in former:
                return 2
            if node[1]["name"] in supervisors:
                return 3
            return 4
        elif node[1]["kind"]=="paper":
            return 5
        elif node[1]["kind"]=="thesis":
            return 6
        else:
            return 7
            
        
    def _get_group(self):
        return list(map(self._get_num_kind,self.G.nodes(data=True)))
    
    def __repr__(self):
        return json.dumps({"x":{"links":{
            "source":[e[0] for e in self.G.edges],
            "target":[e[1] for e in self.G.edges],
            "value":[1 for e in self.G.edges],
            "colour":["#666" for e in self.G.edges],
        }, "nodes":{
            "name":[n[1]["name"] for n in self.G.nodes(data=True)],
            "group":self._get_group(),
            "hyperlink":list(map(self._get_hyperlink, self.G.nodes(data=True)))
        },
        "options":{"NodeID":"name",
                   "Group":"group","colourScale":"d3.scaleOrdinal()\n            .domain([\"1\", \"2\", \"3\", \"4\", \"5\", \"6\"])\n            .range("+json.dumps(["#a361c7","#5ba962","#c75b89","#ac973e","#648ace","#cb6042"])+");",
                   "fontSize":12,
                   "fontFamily":"serif",
                   "clickTextSize":30,
                   "linkDistance":50,
                   "linkWidth":"function(d) { return Math.sqrt(d.value); }",
                   "charge":-30,
                   "opacity":1,
                   "zoom":True,
                   "legend":False,
                   "arrows":False,
                   "nodesize":False,
                   "radiusCalculation":" Math.sqrt(d.nodesize)+6",
                   "bounded":False,
                   "opacityNoHover":0,
                   "clickAction":"window.open(d.hyperlink)"},
            },
        "evals":[],
        "jsHooks":[]})

net = Network()

with open("../files/researchers.json", "r") as f:
    researchers = json.load(f)
    
for researcher in researchers:
    group.append(researcher["name"])
    
with open("../files/researchers-former.json", "r") as f:
    researchers = json.load(f)
    
for researcher in researchers:
    former.append(researcher["name"])
    
print(former)

with open("../papers/paper.json", "r") as f:
    papers = json.load(f)
    
for paper in papers:
    net.add_paper(paper["title"], paper["author"].split(", "), link=paper["link"])

    
print(former)

nx.draw(net.G, node_color=net._get_group())

with open("network.html.template", "r") as f:    
    template = f.read()
    
template = template.replace("TOREPLACE_NETWORK", str(net))

with open("network.html", "w") as f:
    f.write(template)
