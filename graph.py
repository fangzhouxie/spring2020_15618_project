# Helper script to generate random graphs

import argparse
import random

DEFAULT_NNODE = 10
DEFAULT_NEDGE = 20
DEFAULT_SEED = 1

GRAPH_DIRECTORY = "./graphs"

def generate_graph(nnode, nedge, seed):
    total_edges = nnode * (nnode - 1) / 2; # undirected
    all_edges = []
    for i in range(nnode):
        for j in range(i+1, nnode):
            all_edges.append((i, j))

    random.seed(seed)
    edges = random.sample(all_edges, nedge)

    res = []
    for e in edges:
        weight = random.randint(1, 10)
        flip = random.randint(0, 1)
        if flip > 0:
            res.append((e[1], e[0], weight))
        else:
            res.append((e[0], e[1], weight))

    gname = graphName(nnode, nedge, seed)
    f = open(gname, "w")
    f.write("{}\n".format(nnode))
    f.write("{}\n".format(nedge))
    for r in sorted(res):
      f.write("{} {} {}\n".format(r[0], r[1], r[2]))
    f.close()

def graphName(nnode, nedge, seed):
    return "{}/n{}-e{}-s{}.txt".format(GRAPH_DIRECTORY, nnode, nedge, seed)

if __name__ == "__main__":
    doAll = False

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--nnode", type=int, help="Number of nodes")
    parser.add_argument("-e", "--nedge", type=int, help="Number of edges")
    parser.add_argument("-s", "--seed", type=int, help="Random seed")

    args = parser.parse_args()

    nnode = args.nnode or DEFAULT_NNODE
    nedge = args.nedge or DEFAULT_NEDGE
    seed = args.seed or DEFAULT_SEED

    generate_graph(nnode, nedge, seed)
