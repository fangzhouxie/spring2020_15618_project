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
    #pragma omp parallel for
    #endif
    // Iterate through the graph V - 1 times
    for (int iter = 0; iter < graph->nnode; iter++)
        for (int u = 0; u < graph->nnode; u++)
            for (int eid = graph->node[u]; eid < graph->node[u+1]; eid++) {
                int v = graph->edge[eid];
                int weight = graph->weight[eid];
                if (distance[v] > distance[u] + weight)
                    distance[v] = distance[u] + weight;
            }

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
