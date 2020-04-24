CC=g++
CXXFLAGS=-g -O3
OMP=-fopenmp -DOMP

CFILES=johnson.cpp bellman_ford.cpp dijkstra.cpp
HFILES=johnson.hpp

.PHONY: clean

all: john_seq john_omp john_boost

john_seq: $(CFILES) $(HFILES)
	$(CC) $(CXXFLAGS) -o johnson_seq $(CFILES)

john_omp: $(CFILES) $(HFILES)
	$(CC) $(CXXFLAGS) $(OMP) -o johnson_omp $(CFILES)

john_boost: johnson-boost.cpp
	$(CC) $(CXXFLAGS) -o johnson_boost johnson-boost.cpp

clean:
	rm -f johnson_seq
	rm -f johnson_omp
	rm -f johnson_boost
