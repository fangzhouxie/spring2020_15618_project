#include "johnson_seq.h"

Graph *LoadGraph(FILE *graph_file) {
    Graph *graph = (Graph *)malloc(sizeof(Graph));
    char linebuf[MaxLineLength];
    int src_id, dst_id, weight;
    int prev_src_id = 0;
    int lineno = 0;

    fgets(linebuf, MaxLineLength, graph_file);
    if (sscanf(linebuf, "%d", &graph->nnode) < 1) {
        printf("ERROR. Malformed graph file header (line 1)\n");
        return NULL;
    }

    fgets(linebuf, MaxLineLength, graph_file);
    if (sscanf(linebuf, "%d", &graph->nedge) < 1) {
        printf("ERROR. Malformed graph file header (line 1)\n");
        return NULL;
    }

    graph->node = (int *)calloc(graph->nnode+1, sizeof(int));
    graph->node[graph->nnode] = graph->nedge;
    graph->edge = (int *)malloc(graph->nedge * sizeof(int));
    graph->weight = (int *)malloc(graph->nedge * sizeof(int));

    while (fgets(linebuf, MaxLineLength, graph_file) != NULL) {
        if (sscanf(linebuf, "%d %d %d", &src_id, &dst_id, &weight) < 3) {
            printf("ERROR. Malformed graph file header (line 1)\n");
            return NULL;
        }

        if (prev_src_id != src_id) {
            for (int i = prev_src_id+1; i <= src_id; i++)
                graph->node[i] = lineno;
            prev_src_id = src_id;
        }

        graph->edge[lineno] = dst_id;
        graph->weight[lineno] = weight;

        lineno++;
    }

    // Padd all later nodes
    for (int nid = src_id+1; nid < graph->nnode; nid++) graph->node[nid] = graph->nedge;

    return graph;
}

int main(int argc, char *argv[]) {
    int c;
    FILE *graph_file = NULL;
    Graph *graph;

    // parse command line arguments
    while ((c = getopt(argc, argv, "g:")) != -1) {
        switch(c) {
            case 'g':
                graph_file = fopen(optarg, "r");
                if (graph_file == NULL)
                    printf("Couldn't open graph file %s\n", optarg);
                break;
            default:
                printf("Unknown option '%c'\n", c);
        }
    }

    if (graph_file == NULL) {
	    printf("Need graph file\n");
        return 0;
    }

    graph = LoadGraph(graph_file);

    BellmanFord(graph, 0);

    // for (int i = 0; i < graph->nnode; i++) printf("node %d\n", graph->node[i]);
    // for (int i = 0; i < graph->nedge; i++)
    //     if (graph->weight[i] < 0) 
    //         printf("weight %d\n", graph->weight[i]);
    // for (int src_nid = 0; src_nid < graph->nnode; src_nid++)
    //     for (int eid = graph->node[src_nid]; eid < graph->node[src_nid+1]; eid++) {
    //         int dst_nid = graph->edge[eid];
    //         int weight = graph->weight[eid];
    //         printf("%d to %d with weight %d\n", src_nid, dst_nid, weight);
    //     }
}