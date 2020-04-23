DEBUG=0
CC=g++
CXXFLAGS=-g -O3 -DDEBUG=$(DEBUG)
OMP=-fopenmp -DOMP

CFILES = johnson.cpp bellman_ford.cpp dijkstra.cpp johnson.hpp

.PHONY: clean

all: john-seq john-boost

john-seq: $(CFILES)
	$(CC) $(CXXFLAGS) -o johnson-seq $(CFILES)

john-omp:

john-boost: johnson-boost.cpp
	$(CC) $(CXXFLAGS) -o johnson-boost johnson-boost.cpp

clean:
	rm -f johnson-seq
	rm -f johnson-boost
