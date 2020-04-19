#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>

#define MAXLINELEN 1024

typedef struct {
    int nnode;
    int nedge;

    int *node;
    int *edge;
    int *weight;
} graph_t;