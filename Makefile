CC=g++
CXXFLAGS=-g -O3

CFILES = johnson_seq.cpp bellman_ford.cpp johnson_seq.h

.PHONY: clean

john-seq: $(CFILES)
	$(CC) $(CXXFLAGS) -o johnson_seq $(CFILES)

clean:
	rm -f johnson_seq