#include "johnson.hpp"

// Recursively calculate original weights
void CalculateOriginalDistance(int src_nid, int nid, int *distance, int *predecessor, Graph *graph) {
    int current_nid = nid;
    int current_distance = 0;
    int prev_nid = predecessor[current_nid];

    if (distance[nid] != -1)   // Distance is already alculated
        return;
    else if (nid == src_nid)    // This is the source node
        distance[nid] = 0;
    else if (predecessor[nid] == -1)    // No valid path to this node exists
        distance[nid] = IntMax;
    else {
        if (distance[prev_nid] == -1)
            CalculateOriginalDistance(src_nid, prev_nid, distance, predecessor, graph);
        // Distance increment by original edge weight
        for (int eid = graph->node[prev_nid]; eid < graph->node[prev_nid+1]; eid++)
            if (graph->edge[eid] == current_nid)
                distance[nid] = graph->weight[eid] + distance[prev_nid];
    }
}

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
        distance[nid] = -1;
        predecessor[nid] = -1;
        tmp_distance[nid] = IntMax;
        visited[nid] = 0;
    }
    tmp_distance[src_nid] = 0;
    predecessor[src_nid] = src_nid;

    for (int iter = 0; iter < graph->nnode; iter++) {
        int min_nid = FindIndexOfUnvisitedNodeWithMinDistance(graph->nnode, tmp_distance, visited);
        // No reachable unvisted nodes left
        if (tmp_distance[min_nid] == IntMax) break;

        visited[min_nid] = 1;
        for (int eid = graph->node[min_nid]; eid < graph->node[min_nid+1]; eid++) {
            int neighbor_nid = graph->edge[eid];
            if (tmp_distance[neighbor_nid] > graph->new_weight[eid] + tmp_distance[min_nid]) {
                tmp_distance[neighbor_nid] = graph->new_weight[eid] + tmp_distance[min_nid];
                predecessor[neighbor_nid] = min_nid;
            }
        }
    }

    for (int nid = 0; nid < graph->nnode; nid++)
        CalculateOriginalDistance(src_nid, nid, distance, predecessor, graph);
}

void AllPairsDijkstra(Graph *graph) {
    for (int nid = 0; nid < graph->nnode; nid++) {
        #if DEBUG
        printf("Dijkstra started for node %d\n", nid);
        #endif
        Dijkstra(graph, nid);
    }
}
