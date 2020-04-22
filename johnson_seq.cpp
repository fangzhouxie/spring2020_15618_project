#include "johnson_seq.hpp"

Graph *LoadGraph(FILE *graph_file) {
    Graph *graph = (Graph *)malloc(sizeof(Graph));
    char linebuf[MaxLineLength];
    int src_id, dst_id, weight;
    int prev_src_id = 0;
    int lineno = 0;

    //  Load number of nodes and edges
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

    //  Initialize graph
    graph->node = (int *)calloc(graph->nnode+1, sizeof(int));
    graph->node[graph->nnode] = graph->nedge;
    graph->edge = (int *)malloc(graph->nedge * sizeof(int));
    graph->weight = (int *)malloc(graph->nedge * sizeof(int));
    graph->new_weight = (int *)malloc(graph->nedge * sizeof(int));
    graph->distance = (int **)malloc(graph->nnode * sizeof(int *));
    graph->predecessor = (int **)malloc(graph->nnode * sizeof(int *));
    for (int nid = 0; nid < graph->nnode; nid++) {
        graph->distance[nid] = (int *)malloc(graph->nnode * sizeof(int));
        graph->predecessor[nid] = (int *)malloc(graph->nnode * sizeof(int));
    }

    //  Load edges
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

    // Pad all later nodes with 0 out degree
    for (int nid = src_id+1; nid < graph->nnode; nid++) graph->node[nid] = graph->nedge;

    return graph;
}

void Johnson(Graph *graph) {
    BellmanFord(graph, 0);

    AllPairsDijkstra(graph);

    for (int i = 0; i < graph->nnode; i++) {
        for (int j = 0; j < graph->nnode; j++)
            if (graph->distance[i][j] == IntMax)
                printf("inf\t");
            else
                printf("%d\t", graph->distance[i][j]);
        printf("\n");
    }
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

    Johnson(graph);
}