#include "johnson.hpp"
#include <iomanip>

char display;

static void Usage(char *name) {
    char use_string[] = "-g GFILE [-v]";
    printf("Usage: %s %s\n", name, use_string);
    printf("   -h        Print this message\n");
    printf("   -g GFILE  Graph file\n");
    printf("   -v        Operate in verbose mode\n");
    printf("   -t THD    Set number of threads for OMP (default is number of processors)\n");
    exit(0);
}

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
    BellmanFord(graph);
    AllPairsDijkstra(graph);
}

int main(int argc, char *argv[]) {
    int c;
    FILE *graph_file = NULL;
    Graph *graph;
    display = 0;
    #if OMP
    int thread_count = omp_get_num_procs();
    #endif

    // parse command line arguments
    while ((c = getopt(argc, argv, "hg:t:v")) != -1) {
        switch(c) {
            case 'g':
                graph_file = fopen(optarg, "r");
                if (graph_file == NULL)
                    printf("Couldn't open graph file %s\n", optarg);
                break;
            case 'v':
                display = 1;
                break;
            case 't':
                #if OMP
                thread_count = atoi(optarg);
                #else
                printf("Setting number of threads for sequential version has no effect\n");
                #endif
                break;
            case 'h':
                Usage(argv[0]);
                break;
            default:
                printf("Unknown option '%c'\n", c);
                Usage(argv[0]);
        }
    }

    if (graph_file == NULL) {
	    printf("Need graph file\n");
        Usage(argv[0]);
        return 0;
    }

    #if OMP
    omp_set_num_threads(thread_count);
    #endif

    graph = LoadGraph(graph_file);
    Johnson(graph);

    for (int i = 0; i < graph->nnode; ++i) {
      for (int j = 0; j < graph->nnode; ++j) {
        if (graph->distance[i][j] == IntMax)
        std::cout << std::setw(5) << "inf";
        else
        std::cout << std::setw(5) << graph->distance[i][j];
      }
      std::cout << std::endl;
    }

    // Write result to file
    // std::ofstream f;
    // f.open("result.txt");
    // for (int i = 0; i < graph->nnode; i++) {
    //     for (int j = 0; j < graph->nnode; j++)
    //         if (graph->distance[i][j] == IntMax)
    //             f << "inf\t\t";
    //         else
    //             f << graph->distance[i][j] << "\t\t";
    //     f << "\n";
    // }
    // f.close();
}
