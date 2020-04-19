#include "john-seq.h"

graph_t *load_graph(FILE *gfile) {
    graph_t *g = (graph_t *)malloc(sizeof(graph_t));
    char linebuf[MAXLINELEN];
    int src_id, dst_id, weight;
    int prev_src_id = 0;
    int lineno = 0;

    fgets(linebuf, MAXLINELEN, gfile);
    if (sscanf(linebuf, "%d", &g->nnode) < 1) {
        printf("ERROR. Malformed graph file header (line 1)\n");
        return NULL;
    }

    fgets(linebuf, MAXLINELEN, gfile);
    if (sscanf(linebuf, "%d", &g->nedge) < 1) {
        printf("ERROR. Malformed graph file header (line 1)\n");
        return NULL;
    }

    g->node = (int *)calloc(g->nnode+1, sizeof(int));
    g->node[g->nnode] = g->nedge;
    g->edge = (int *)malloc(g->nedge * sizeof(int));
    g->weight = (int *)malloc(g->nedge * sizeof(int));

    while (fgets(linebuf, MAXLINELEN, gfile) != NULL) {
        if (sscanf(linebuf, "%d %d %d", &src_id, &dst_id, &weight) < 3) {
            printf("ERROR. Malformed graph file header (line 1)\n");
            return NULL;
        }

        if (prev_src_id != src_id) {
            for (int i = prev_src_id+1; i <= src_id; i++)
                g->node[i] = lineno;
            prev_src_id = src_id;
        }

        g->edge[lineno] = dst_id;
        g->weight[lineno] = weight;

        lineno++;
    }

    return g;
}

int main(int argc, char *argv[]) {
    int c;
    FILE *gfile = NULL;
    graph_t *g;

    // parse command line arguments
    while ((c = getopt(argc, argv, "g:")) != -1) {
        switch(c) {
            case 'g':
                gfile = fopen(optarg, "r");
                if (gfile == NULL)
                    printf("Couldn't open graph file %s\n", optarg);
                break;
            default:
                printf("Unknown option '%c'\n", c);
        }
    }

    if (gfile == NULL) {
	    printf("Need graph file\n");
        return 0;
    }

    g = load_graph(gfile);

    // int start = g->node[0];
    // int end = g->node[0+1];
    // for (int i = start; i < end; i++)
    //     printf("0 -> %d with weight %d\n", g->edge[i], g->weight[i]);
}