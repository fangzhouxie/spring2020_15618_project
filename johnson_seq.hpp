#include <iostream>
#include <fstream>
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>

#define MaxLineLength 1024
#define IntMax __INT32_MAX__

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

Graph *LoadGraph(FILE *graph_file);

void BellmanFord(Graph *g);

void AllPairsDijkstra(Graph *graph);

void Johnson(Graph *graph);