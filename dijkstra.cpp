#include "johnson.hpp"

// Functionality is explaned by function name
int FindIndexOfUnvisitedNodeWithMinDistance(int nnode, int *distance, char *visited) {
    int min_nid = -1;
    int min_distance = IntMax;

    for (int nid = 0; nid < nnode; nid++)
        if (!visited[nid] && distance[nid] <= min_distance) {
            min_nid = nid;
            min_distance = distance[nid];
        }

    return min_nid;
}

void Dijkstra(Graph *graph, int src_nid) {
    int *distance = graph->distance[src_nid];
    int *predecessor = graph->predecessor[src_nid];
    int tmp_distance[graph->nnode];
    char visited[graph->nnode];

    for (int nid = 0; nid < graph->nnode; nid++) {
        predecessor[nid] = -1;
        tmp_distance[nid] = IntMax;
        distance[nid] = IntMax;
        visited[nid] = 0;
    }
    predecessor[src_nid] = src_nid;
    tmp_distance[src_nid] = 0;
    distance[src_nid] = 0;

    for (int iter = 0; iter < graph->nnode; iter++) {
        int min_nid = FindIndexOfUnvisitedNodeWithMinDistance(graph->nnode, tmp_distance, visited);
        // No reachable unvisted nodes left
        if (tmp_distance[min_nid] == IntMax) break;

        visited[min_nid] = 1;
        for (int eid = graph->node[min_nid]; eid < graph->node[min_nid+1]; eid++) {
            int neighbor_nid = graph->edge[eid];
            if (tmp_distance[neighbor_nid] > graph->new_weight[eid] + tmp_distance[min_nid]) {
                tmp_distance[neighbor_nid] = graph->new_weight[eid] + tmp_distance[min_nid];
                distance[neighbor_nid] = graph->weight[eid] + distance[min_nid];
                predecessor[neighbor_nid] = min_nid;
            }
        }
    }
}

void AllPairsDijkstra(Graph *graph) {
    #if OMP
    #pragma omp parallel for schedule(dynamic, 32)
    #endif
    for (int nid = 0; nid < graph->nnode; nid++) {
        if (display)
            printf("Dijkstra started for node %d\n", nid);
        Dijkstra(graph, nid);
    }
}
