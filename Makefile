CC=g++
CXXFLAGS=-g -O3

.PHONY: clean

john-seq: john-seq.cpp john-seq.h
	$(CC) $(CXXFLAGS) -o john-seq john-seq.cpp

clean:
	rm -f john-seq