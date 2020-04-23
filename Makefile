DEBUG=1
CC=g++
CXXFLAGS=-g -O3 -DDEBUG=$(DEBUG)
OMP=-fopenmp -DOMP

CFILES=johnson.cpp bellman_ford.cpp dijkstra.cpp
HFILES=johnson.hpp

.PHONY: clean

all: john-seq john-omp john-boost

john-seq: $(CFILES) $(HFILES)
	$(CC) $(CXXFLAGS) -o johnson-seq $(CFILES)

john-omp: $(CFILES) $(HFILES)
	$(CC) $(CXXFLAGS) $(OMP) -o johnson-omp $(CFILES)

john-boost: johnson-boost.cpp
	$(CC) $(CXXFLAGS) -o johnson-boost johnson-boost.cpp

clean:
	rm -f johnson-seq
	rm -f johnson-boost
