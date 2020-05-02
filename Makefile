CXX=g++
CXXFLAGS=-O3 -m64 -Wall
OMP=-fopenmp -DOMP
NVCC=nvcc
NVCCFLAGS=-O3 -m64 --gpu-architecture compute_61
LDFLAGS=-L/usr/local/depot/cuda-10.2/lib64/ -lcudart

CFILES=johnson.cpp bellman_ford.cpp dijkstra.cpp cycletimer.cpp instrument.cpp
HFILES=johnson.hpp cycletimer.hpp instrument.hpp
CUDAFILES=johnson.cu
BCFILES=johnson-boost.cpp
BHFILES=johnson-boost.hpp
ICFILES = cycletimer.cpp instrument.cpp
IHFILES = cycletimer.hpp instrument.hpp

.PHONY: clean

all: john_seq john_omp john_cuda john_boost

john_seq: $(CFILES) $(HFILES)
	$(CXX) $(CXXFLAGS) -o johnson_seq $(CFILES)

john_omp: $(CFILES) $(HFILES)
	$(CXX) $(CXXFLAGS) $(OMP) -o johnson_omp $(CFILES)

john_cuda: $(CUDAFILES) $(ICFILES) $(IHFILES)
	$(NVCC) $(NVCCFLAGS) -o johnson_cuda $(CUDAFILES) $(ICFILES)

john_boost: $(BCFILES) $(BHFILES)
	$(CXX) $(CXXFLAGS) -o johnson_boost $(BCFILES)

clean:
	rm -f johnson_seq
	rm -f johnson_omp
	rm -f johnson_boost
	rm -f johnson_cuda
