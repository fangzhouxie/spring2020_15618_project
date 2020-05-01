#include "johnson.hpp"

void BellmanFord(Graph *graph) {
    if (display)
        printf("BellmanFord started\n");
    int distance[graph->nnode];

    #if OMP
    #pragma omp parallel for
    #endif
    // Initialize distances from new source node to all nodes
    for (int nid = 0; nid < graph->nnode; nid++)
        distance[nid] = 0;

    #if OMP
    int** eid_matrix = (int**)malloc(graph->nnode * sizeof(int *));
    for (int nid = 0; nid < graph->nnode; nid++) {
        eid_matrix[nid] = (int *)malloc(graph->nnode * sizeof(int));
        #pragma omp parallel for
        for (int nnid = 0; nnid < graph->nnode; nnid++) {
            eid_matrix[nid][nnid] = -1;
        }
    }

    #pragma omp parallel for
    for (int u = 0; u < graph->nnode; u++) {
        for (int eid = graph->node[u]; eid < graph->node[u+1]; eid++) {
            int v = graph->edge[eid];
            eid_matrix[u][v] = eid;
        }
    }

    int* rev_node = (int*)malloc((graph->nnode+1) * sizeof(int *));
    int* rev_edge = (int*)malloc(graph->nedge * sizeof(int *));
    int* rev_eid = (int*)malloc(graph->nedge * sizeof(int *));

    int i = 0;

    for (int v = 0; v < graph->nnode; v++) {
        for (int u = 0; u < graph->nnode; u++) {
            int eid = eid_matrix[u][v];
            if (eid != -1) {
                rev_eid[i] = eid;
                rev_edge[i] = u;
                i += 1;
            }
        }
        rev_node[v+1] = i;
    }

    #pragma omp parallel for
    for (int nid = 0; nid < graph->nnode; nid++) {
        free(eid_matrix[nid]);
    }
    free(eid_matrix);

    // Iterate through the graph V - 1 times
    for (int iter = 0; iter < graph->nnode; iter++)
        #pragma omp parallel for
        for (int v = 0; v < graph -> nnode; v++) {
            for (int i = rev_node[v]; i < rev_node[v+1]; i++) {
                int u = rev_edge[i];
                int eid = rev_eid[i];
                int weight = graph->weight[eid];
                if (distance[v] > distance[u] + weight)
                    distance[v] = distance[u] + weight;
            }
        }

    free(rev_node);
    free(rev_edge);
    free(rev_eid);

    #else

    // Iterate through the graph V - 1 times
    // Entirely sequential
    for (int iter = 0; iter < graph->nnode; iter++)
        // TODO: can we directly add pragma here without reversing u and v?
        for (int u = 0; u < graph->nnode; u++)
            for (int eid = graph->node[u]; eid < graph->node[u+1]; eid++) {
                int v = graph->edge[eid];
                int weight = graph->weight[eid];
                // #pragma omp critical
                if (distance[v] > distance[u] + weight)
                    distance[v] = distance[u] + weight;
            }

    #endif

    #if OMP
    #pragma omp parallel for schedule(dynamic, 32)
    #endif
    // Reweight edge weights
    for (int u = 0; u < graph->nnode; u++)
        for (int eid = graph->node[u]; eid < graph->node[u+1]; eid++) {
            int v = graph->edge[eid];
            graph->new_weight[eid] = graph->weight[eid] + distance[u] - distance[v];
            if (graph->new_weight[eid] < 0) {
                printf("Graph contains negative weight cycle\n");
                exit(0);
            }
        }
}
