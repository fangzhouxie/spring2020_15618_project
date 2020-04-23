DEBUG=0
CC=g++
CXXFLAGS=-g -O3 -DDEBUG=$(DEBUG)

CFILES = johnson_seq.cpp bellman_ford.cpp dijkstra.cpp johnson_seq.hpp

.PHONY: clean

all: john-seq john-boost

john-seq: $(CFILES)
	$(CC) $(CXXFLAGS) -o johnson_seq $(CFILES)

john-boost: johnson-boost.cpp
	$(CC) $(CXXFLAGS) -o johnson-boost johnson-boost.cpp

clean:
	rm -f johnson_seq
	rm -f johnson-boost
