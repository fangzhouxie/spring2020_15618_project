#ifndef OMP
#define OMP 0
#endif

#include <iostream>
#include <fstream>
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>

#if OMP
#include <omp.h>
#endif

#define MaxLineLength 1024
#define IntMax __INT32_MAX__

extern char display;

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

static void Usage(char *name);

Graph *LoadGraph(FILE *graph_file);

void BellmanFord(Graph *g);

void AllPairsDijkstra(Graph *graph);

void Johnson(Graph *graph);