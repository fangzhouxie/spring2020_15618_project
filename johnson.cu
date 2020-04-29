#include <iostream>
#include <fstream>
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>

#include <cuda.h>
#include <cuda_runtime.h>
#include <driver_functions.h>

#define MaxLineLength 1024
#define IntMax __INT32_MAX__
#define cudaCheckError(ans) cudaAssert((ans), __FILE__, __LINE__);
inline void cudaAssert(cudaError_t code, const char *file, int line, bool abort=true) {
    if (code != cudaSuccess) {
        fprintf(stderr, "CUDA Error: %s at %s:%d\n",
            cudaGetErrorString(code), file, line);
        if (abort) exit(code);
    }
}

char display;

typedef struct {
    int nnode;
    int nedge;

    int *node;
    int *edge;
    int *weight;
    int *new_weight;

    int **distance;
    int **predecessor;
} Graph;

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

///////////////////////////////////////////////////////////////////////////////
// Start of kernels
///////////////////////////////////////////////////////////////////////////////

__device__ __inline__ void BellmanFord(Graph *graph, int nid) {
    extern __shared__ int distance[];
    if (nid < graph->nnode)
        distance[nid] = 0;
    
    __syncthreads();

    for (int u = 0; u < graph->nnode; u++)
        for (int eid = graph->node[u]; eid < graph->node[u+1]; eid++) {
            int v = graph->edge[eid];
            int weight = graph->weight[eid];
            if (distance[v] > distance[u] + weight)
                distance[v] = distance[u] + weight;
        }
    
    __syncthreads();

    if (nid < graph->nnode) {
        int u = nid;
        for (int eid = graph->node[u]; eid < graph->node[u+1]; eid++) {
            int v = graph->edge[eid];
            graph->new_weight[eid] = graph->weight[eid] + distance[u] - distance[v];
            if (graph->new_weight[eid] < 0) {
                printf("Graph contains negative weight cycle\n");
                return;
            }
        }
    }
}

// Recursively calculate original weights
__device__ __inline__ void CalculateOriginalDistance(int src_nid, int nid, int *distance, int *predecessor, Graph *graph) {
    int current_nid = nid;
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
__device__ __inline__ int FindIndexOfUnvisitedNodeWithMinDistance(int nnode, int *distance, char *visited) {
    int min_nid = -1;
    int min_distance = IntMax;

    for (int nid = 0; nid < nnode; nid++)
        if (!visited[nid] && distance[nid] <= min_distance) {
            min_nid = nid;
            min_distance = distance[nid];
        }

    return min_nid;
}

__device__ __inline__ void Dijkstra(Graph *graph, int src_nid) {
    int *distance = graph->distance[src_nid];
    int *predecessor = graph->predecessor[src_nid];
    int *tmp_distance = (int *)malloc(graph->nnode * sizeof(int));
    char *visited = (char *)malloc(graph->nnode * sizeof(char));

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

    free(tmp_distance);
    free(visited);
}

__global__ void KernelJohnson(Graph *device_graph) {
    int index = blockIdx.x * blockDim.x + threadIdx.x;

    if (index == 0) printf("%d\n", device_graph->node[3]);

    // BellmanFord(device_graph, index);
    // Dijkstra(device_graph, index);
}

///////////////////////////////////////////////////////////////////////////////
/// End of kernels
///////////////////////////////////////////////////////////////////////////////

static void Usage(char *name) {
    char use_string[] = "-g GFILE [-v]";
    printf("Usage: %s %s\n", name, use_string);
    printf("   -h        Print this message\n");
    printf("   -g GFILE  Graph file\n");
    printf("   -v        Operate in verbose mode\n");
    exit(0);
}

int main(int argc, char *argv[]) {
    int c;
    FILE *graph_file = NULL;
    Graph *graph;
    display = 0;
    bool instrument = false;

    // parse command line arguments
    while ((c = getopt(argc, argv, "hg:vI")) != -1) {
        switch(c) {
            case 'g':
                graph_file = fopen(optarg, "r");
                if (graph_file == NULL)
                    printf("Couldn't open graph file %s\n", optarg);
                break;
            case 'v':
                display = 1;
                break;
            case 'h':
                Usage(argv[0]);
                break;
            case 'I':
                instrument = true;
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

    graph = LoadGraph(graph_file);

    Graph *device_graph;
    cudaMalloc(&device_graph, sizeof(graph));
    // cudaMalloc(&device_graph->node, graph->nnode * sizeof(int));
    // cudaMalloc(&device_graph->edge, graph->nedge * sizeof(int));
    // cudaMalloc(&device_graph->weight, graph->nedge * sizeof(int));
    // cudaMalloc(&device_graph->new_weight, graph->nedge * sizeof(int));
    // cudaMalloc(&device_graph->distance, graph->nnode * sizeof(int *));
    // cudaMalloc(&device_graph->predecessor, graph->nnode * sizeof(int *));
    // for (int nid = 0; nid < graph->nnode; nid++) {
    //     cudaMalloc(&device_graph->distance[nid], graph->nnode * sizeof(int));
    //     cudaMalloc(&device_graph->predecessor[nid], graph->nnode * sizeof(int));
    // }
    
    cudaMemcpy(device_graph, graph, sizeof(Graph), cudaMemcpyHostToDevice);

    const int ThreadsPerBlock = 512;
    const int Blocks = (graph->nnode + ThreadsPerBlock - 1) / ThreadsPerBlock;

    KernelJohnson<<<Blocks, ThreadsPerBlock, graph->nnode>>>(device_graph);
    cudaCheckError(cudaDeviceSynchronize());
    cudaMemcpy(graph, device_graph, sizeof(graph), cudaMemcpyDeviceToHost);
}