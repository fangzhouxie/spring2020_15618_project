#include <iomanip>
#include <iostream>
#include <fstream>
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>

#include <cuda.h>
#include <cuda_runtime.h>
#include <driver_functions.h>

#include "cycletimer.hpp"
#include "instrument.hpp"

#define MaxLineLength 1024
#define IntMax __INT32_MAX__
#define cudaCheckErrors(msg) \
    do { \
        cudaError_t __err = cudaGetLastError(); \
        if (__err != cudaSuccess) { \
            fprintf(stderr, "Fatal error: %s (%s at %s:%d)\n", \
                msg, cudaGetErrorString(__err), \
                __FILE__, __LINE__); \
            fprintf(stderr, "*** FAILED - ABORTING\n"); \
            exit(1); \
        } \
    } while (0)

#define cudaCheckError(ans) cudaAssert((ans), __FILE__, __LINE__);
inline void cudaAssert(cudaError_t code, const char *file, int line, bool abort=true) {
    if (code != cudaSuccess) {
        fprintf(stderr, "CUDA Error: %s at %s:%d\n",
            cudaGetErrorString(code), file, line);
        if (abort) exit(code);
    }
}

char display;

struct GlobalConstants {
    int nnode;
    int nedge;

    int *node;
    int *edge;
    int *weight;
};

typedef struct {
    int nnode;
    int nedge;

    int *node;
    int *edge;
    int *weight;
    int *new_weight;

    int *distance;
    int *predecessor;
} Graph;

__constant__ GlobalConstants constGraphParams;

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
    graph->distance = (int *)malloc(graph->nnode * graph->nnode * sizeof(int));
    graph->predecessor = (int *)malloc(graph->nnode * graph->nnode * sizeof(int));

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

void freeGraph(Graph* graph) {
    free(graph->node);
    free(graph->edge);
    free(graph->weight);
    free(graph->new_weight);
    free(graph->distance);
    free(graph->predecessor);
    free(graph);
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
__device__ __inline__ void CalculateOriginalDistance(int src_nid, int nid, int *distance, int *predecessor) {
    int current_nid = nid;
    int prev_nid = predecessor[current_nid];

    int *node = constGraphParams.node;
    int *edge = constGraphParams.edge;
    int *weight = constGraphParams.weight;

    if (distance[nid] != -1)   // Distance is already alculated
        return;
    else if (nid == src_nid)    // This is the source node
        distance[nid] = 0;
    else if (predecessor[nid] == -1)    // No valid path to this node exists
        distance[nid] = IntMax;
    else {
        if (distance[prev_nid] == -1)
            CalculateOriginalDistance(src_nid, prev_nid, distance, predecessor);
        // Distance increment by original edge weight
        for (int eid = node[prev_nid]; eid < node[prev_nid+1]; eid++)
            if (edge[eid] == current_nid)
                distance[nid] = weight[eid] + distance[prev_nid];
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

__global__ void dijkstra_kernel(int* new_weight, int* distance, int* tmp_distance, int* predecessor, char* visited) {
    int src_nid = blockIdx.x * blockDim.x + threadIdx.x;
    int nnode = constGraphParams.nnode;
    if (src_nid >= nnode) return;

    int *node = constGraphParams.node;
    int *edge = constGraphParams.edge;

    int *distance_local = &distance[src_nid * nnode];
    // malloc would fail for large graphs
    int *predecessor_local = &predecessor[src_nid * nnode];
    int *tmp_distance_local = &tmp_distance[src_nid * nnode];
    char *visited_local = &visited[src_nid * nnode];

    for (int nid = 0; nid < nnode; nid++) {
        distance_local[nid] = -1;
        predecessor_local[nid] = -1;
        tmp_distance_local[nid] = IntMax;
        visited_local[nid] = 0;
    }
    tmp_distance_local[src_nid] = 0;
    predecessor_local[src_nid] = src_nid;

    for (int iter = 0; iter < nnode; iter++) {
        int min_nid = FindIndexOfUnvisitedNodeWithMinDistance(nnode, tmp_distance_local, visited_local);
        // No reachable unvisted nodes left
        if (tmp_distance_local[min_nid] == IntMax) break;

        visited_local[min_nid] = 1;
        for (int eid = node[min_nid]; eid < node[min_nid+1]; eid++) {
            int neighbor_nid = edge[eid];
            if (tmp_distance_local[neighbor_nid] > new_weight[eid] + tmp_distance_local[min_nid]) {
                tmp_distance_local[neighbor_nid] = new_weight[eid] + tmp_distance_local[min_nid];
                predecessor_local[neighbor_nid] = min_nid;
            }
        }
    }

    for (int nid = 0; nid < nnode; nid++)
        CalculateOriginalDistance(src_nid, nid, distance_local, predecessor_local);

}

__global__ void bellman_ford_kernel(int* src_nodes, int* dst_nodes, int* distance) {
    int eid = blockIdx.x * blockDim.x + threadIdx.x;
    int nedge = constGraphParams.nedge;
    if (eid >= nedge) return;

    int u = src_nodes[eid];
    int v = dst_nodes[eid];

    int* weight = constGraphParams.weight;

    int new_distance = distance[u] + weight[eid];

    // do we need atomicCAS?
    //if (distance[v] > new_distance) distance[v] = new_distance;
    atomicMin(&distance[v], new_distance);
}

///////////////////////////////////////////////////////////////////////////////
/// End of kernels
///////////////////////////////////////////////////////////////////////////////

__host__ void bellman_ford_host(Graph *graph) {
    int distance[graph->nnode];

    // Initialize distances from new source node to all nodes
    for (int nid = 0; nid < graph->nnode; nid++)
        distance[nid] = 0;

    /**************************************************************/
    int* srcNodes = (int *)malloc(graph->nedge * sizeof(int));
    int* dstNodes = (int *)malloc(graph->nedge * sizeof(int));

    for (int u=0; u < graph->nnode; u++) {
        for (int eid = graph->node[u]; eid < graph->node[u+1]; eid++) {
            int v = graph->edge[eid];
            srcNodes[eid] = u;
            dstNodes[eid] = v;
        }
    }

    // Iterate through the graph V - 1 times
    int threadsPerBlock = 32;
    int blocks = (graph->nedge + threadsPerBlock - 1) / threadsPerBlock;

    int* deviceSrcNodes;
    int* deviceDstNodes;
    int* deviceDistance;

    cudaMalloc(&deviceSrcNodes, graph->nedge * sizeof(int));
    cudaMalloc(&deviceDstNodes, graph->nedge * sizeof(int));
    cudaMalloc(&deviceDistance, graph->nnode * sizeof(int));
    // cudaCheckErrors("bellman_ford cudaMalloc");

    cudaMemcpy(deviceSrcNodes, srcNodes, graph->nedge * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(deviceDstNodes, dstNodes, graph->nedge * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(deviceDistance, distance, graph->nnode * sizeof(int), cudaMemcpyHostToDevice);
    // cudaCheckErrors("bellman_ford cudaMemcpyHostToDevice");

    for (int iter = 0; iter < graph->nnode; iter++) {
        bellman_ford_kernel<<<blocks, threadsPerBlock>>>(deviceSrcNodes, deviceDstNodes, deviceDistance);
        cudaDeviceSynchronize(); // sync before next iteration
    }

    // cudaCheckErrors("bellman_ford_kernel");

    // TODO: should this memcpy go inside the loop?
    cudaMemcpy(distance, deviceDistance, graph->nnode * sizeof(int), cudaMemcpyDeviceToHost);
    // cudaCheckErrors("bellman_ford cudaMemcpyDeviceToHost");

    cudaFree(deviceSrcNodes);
    cudaFree(deviceDstNodes);
    cudaFree(deviceDistance);
    free(srcNodes);
    free(dstNodes);
    /**************************************************************/

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

__host__ void dijkstra_host(Graph *graph) {
    int* deviceNewWeights;
    int* deviceDistance;
    int* devicePredecessor;
    char* deviceVisited;
    int* deviceTmpDistance;

    int nnode = graph->nnode;
    int nedge = graph->nedge;

    cudaMalloc(&deviceNewWeights, nedge * sizeof(int));
    cudaMalloc(&deviceDistance, nnode * nnode * sizeof(int));
    cudaMalloc(&deviceTmpDistance, nnode * nnode * sizeof(int));
    cudaMalloc(&devicePredecessor, nnode * nnode * sizeof(int));
    cudaMalloc(&deviceVisited, nnode * nnode * sizeof(char));
    // cudaCheckErrors("dijkstra cudaMalloc");

    cudaMemcpy(deviceNewWeights, graph->new_weight, sizeof(int) * nedge, cudaMemcpyHostToDevice);
    // cudaCheckErrors("dijkstra cudaMemcpyHostToDevice");

    int threadsPerBlock = 512;
    int blocks = (nnode + threadsPerBlock - 1) / threadsPerBlock;
    dijkstra_kernel<<<blocks, threadsPerBlock>>>(deviceNewWeights, deviceDistance, deviceTmpDistance, devicePredecessor, deviceVisited);
    cudaDeviceSynchronize();
    // cudaCheckErrors("dijkstra_kernel");

    cudaMemcpy(graph->distance, deviceDistance, nnode * nnode * sizeof(int), cudaMemcpyDeviceToHost);
    // cudaCheckErrors("dijkstra cudaMemcpyDeviceToHost");

    cudaFree(deviceNewWeights);
    cudaFree(deviceDistance);
    cudaFree(deviceTmpDistance);
    cudaFree(devicePredecessor);
    cudaFree(deviceVisited);
}

__host__ void johnson_host(Graph *graph) {
    START_ACTIVITY(ACTIVITY_OVERHEAD);
    int* deviceNodes;
    int* deviceEdges;
    int* deviceWeights;

    int nnode = graph->nnode;
    int nedge = graph->nedge;

    cudaMalloc(&deviceNodes, (nnode + 1) * sizeof(int));
    cudaMalloc(&deviceEdges, nedge * sizeof(int));
    cudaMalloc(&deviceWeights, nedge * sizeof(int));
    // cudaCheckErrors("johnson cudaMalloc");

    cudaMemcpy(deviceNodes, graph->node, sizeof(int) * (nnode + 1), cudaMemcpyHostToDevice);
    cudaMemcpy(deviceEdges, graph->edge, sizeof(int) * nedge, cudaMemcpyHostToDevice);
    cudaMemcpy(deviceWeights, graph->weight, sizeof(int) * nedge, cudaMemcpyHostToDevice);
    // cudaCheckErrors("johnson cudaMemcpyHostToDevice");

    GlobalConstants graphParams;
    graphParams.nnode = nnode;
    graphParams.nedge = nedge;
    graphParams.node = deviceNodes;
    graphParams.edge = deviceEdges;
    graphParams.weight = deviceWeights;

    cudaMemcpyToSymbol(constGraphParams, &graphParams, sizeof(GlobalConstants));
    // cudaCheckErrors("johnson cudaMemcpyToSymbol");

    FINISH_ACTIVITY(ACTIVITY_OVERHEAD);

    // bellman_ford
    START_ACTIVITY(BELLMAN_FORD);
    bellman_ford_host(graph);
    FINISH_ACTIVITY(BELLMAN_FORD);

    // dijkstra
    START_ACTIVITY(DIJKSTRA);
    dijkstra_host(graph);
    FINISH_ACTIVITY(DIJKSTRA);

    cudaFree(deviceNodes);
    cudaFree(deviceEdges);
    cudaFree(deviceWeights);
}

static void Usage(char *name) {
    char use_string[] = "-g GFILE [-v]";
    printf("Usage: %s %s\n", name, use_string);
    printf("   -h        Print this message\n");
    printf("   -g GFILE  Graph file\n");
    printf("   -v        Operate in verbose mode\n");
    exit(0);
}

int main(int argc, char *argv[]) {
    // Initialize cuda kernel mode driver
    cudaFree(0);

    int c;
    FILE *graph_file = NULL;
    Graph *graph;
    display = 0;
    bool instrument = false;
    bool showMem = false;
    bool doPrint = false;

    // parse command line arguments
    while ((c = getopt(argc, argv, "hg:vIMP")) != -1) {
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
            case 'M':
                showMem = true;
                break;
            case 'P':
                doPrint = true;
                break;
            default:
                printf("Unknown option '%c'\n", c);
                Usage(argv[0]);
        }
    }

    if (showMem) {
        int deviceCount;
        cudaDeviceProp deviceProp;
        cudaGetDeviceCount(&deviceCount);
        for (int d = 0; d < deviceCount; ++d) {
            cudaGetDeviceProperties(&deviceProp, d);
            std::cout
                << "***Device " << d << "***\n"
                << "Name: " << deviceProp.name << "\n"
        	      << "Total Global Memory (kB): " << deviceProp.totalGlobalMem / 1024 << "\n"
                << "Shared Memory per Block: " << deviceProp.sharedMemPerBlock << "\n"
                << "Total Constant Memory (B): " << deviceProp.totalConstMem << "\n"
                << "L2 Cache (B): " << deviceProp.l2CacheSize << "\n";
        }
        return 0;
    }

    track_activity(instrument);

    if (graph_file == NULL) {
	      printf("Need graph file\n");
        Usage(argv[0]);
        return 0;
    }

    START_ACTIVITY(LOAD_GRAPH);
    graph = LoadGraph(graph_file);
    FINISH_ACTIVITY(LOAD_GRAPH);

    johnson_host(graph);

    if (doPrint) {
        // output
        START_ACTIVITY(PRINT_GRAPH);
        for (int i = 0; i < graph->nnode; ++i) {
          for (int j = 0; j < graph->nnode; ++j) {
            if (graph->distance[i * graph->nnode + j] == IntMax)
                std::cout << std::setw(5) << "inf";
            else
                std::cout << std::setw(5) << graph->distance[i * graph->nnode + j];
          }
          std::cout << std::endl;
        }
        FINISH_ACTIVITY(PRINT_GRAPH);
    }

    SHOW_ACTIVITY(stderr, instrument);

    freeGraph(graph);
}
