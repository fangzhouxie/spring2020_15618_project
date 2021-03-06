/*************************************************************************************
* Code adapted from Boost Johnson's algorithm for all-pairs shortest path example:
* https://www.boost.org/doc/libs/1_72_0/libs/graph/example/johnson-eg.cpp
***************************************************************************************/

#include "johnson-boost.hpp"

int main(int argc, char *argv[]){
  int c;
  FILE *gfile = NULL;
  bool instrument = false;
  bool doPrint = false;
  // parse command line arguments
  while ((c = getopt(argc, argv, "g:IP")) != -1) {
    switch(c) {
      case 'g':
        gfile = fopen(optarg, "r");
        if (gfile == NULL)
          printf("Couldn't open graph file %s\n", optarg);
        break;
      case 'I':
        instrument = true;
        break;
      case 'P':
        doPrint = true;
        break;
      default:
      printf("Unknown option '%c'\n", c);
    }
  }

  // track_activity(instrument);

  if (gfile == NULL) {
    printf("Need graph file\n");
    return 0;
  }

  // START_ACTIVITY(LOAD_GRAPH);

  using namespace boost;
  typedef adjacency_list<vecS, vecS, directedS, no_property,
  property< edge_weight_t, int, property< edge_weight2_t, int > > > Graph;
  typedef std::pair < int, int >Edge;

  char linebuf[MAXLINELEN];
  int from_node, to_node, weight;
  int lineno = 0;
  int nnode, nedge;

  fgets(linebuf, MAXLINELEN, gfile);
  if (sscanf(linebuf, "%d", &nnode) < 1) {
    printf("ERROR. Malformed graph file header (line 1)\n");
    return -1;
  }

  fgets(linebuf, MAXLINELEN, gfile);
  if (sscanf(linebuf, "%d", &nedge) < 1) {
    printf("ERROR. Malformed graph file header (line 2)\n");
    return -1;
  }

  Edge edge_array[nedge];
  int weight_array[nedge];
  const int V = nnode;

  while (fgets(linebuf, MAXLINELEN, gfile) != NULL) {
    if (sscanf(linebuf, "%d %d %d", &from_node, &to_node, &weight) < 3) {
      printf("ERROR. Malformed graph file weights\n");
      return -1;
    }

    edge_array[lineno] = Edge(from_node, to_node);
    weight_array[lineno] = weight;

    lineno++;
  }

  const std::size_t E = sizeof(edge_array) / sizeof(Edge);
  #if defined(BOOST_MSVC) && BOOST_MSVC <= 1300
  // VC++ can't handle the iterator constructor
  Graph g(V);
  for (std::size_t j = 0; j < E; ++j)
  add_edge(edge_array[j].first, edge_array[j].second, g);
  #else
  Graph g(edge_array, edge_array + E, V);
  #endif

  property_map < Graph, edge_weight_t >::type w = get(edge_weight, g);
  int *wp = weight_array;

  graph_traits < Graph >::edge_iterator e, e_end;
  for (boost::tie(e, e_end) = edges(g); e != e_end; ++e)
  w[*e] = *wp++;

  std::vector < int >d(V, (std::numeric_limits < int >::max)());
  //variably modified type 'int [V][V]' cannot be used as a template argument
  //instead use a double pointer
  int *DD = new int[V*V];
  int **D = new int*[V];
  for(int i=0; i<V; i++) {
    D[i] = &DD[i*V];
  }

  // FINISH_ACTIVITY(LOAD_GRAPH);

  // START_ACTIVITY(JOHNSON_BOOST);
  johnson_all_pairs_shortest_paths(g, D, distance_map(&d[0]));
  // FINISH_ACTIVITY(JOHNSON_BOOST);

  if (doPrint) {
    // START_ACTIVITY(PRINT_GRAPH);
    for (int i = 0; i < V; ++i) {
      for (int j = 0; j < V; ++j) {
        if (D[i][j] == (std::numeric_limits<int>::max)())
        std::cout << std::setw(5) << "inf";
        else
        std::cout << std::setw(5) << D[i][j];
      }
      std::cout << std::endl;
    }
    // FINISH_ACTIVITY(PRINT_GRAPH);
  }

  // SHOW_ACTIVITY(stderr, instrument);

  return 0;
}
