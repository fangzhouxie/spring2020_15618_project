#!/usr/bin/python
# Measure overall performance
# Adapted from https://github.com/cmu15418/asst3-s20/blob/master/code/benchmark.py

import argparse
import getopt
import math
import os
import os.path
import random
import subprocess
import sys
import time

from regress import checkFiles
from graph import generate_graph, graphName

# General information
stdProgram = "./johnson_boost"
seqProgram = "./johnson_seq"
ompProgram = "./johnson_omp"
cudaProgram = "./johnson_cuda"

graphProgram = "python3 graph.py"

graphDirectory = "./graphs"

outFile = None

doCheck = True
saveDirectory = "./check"

testFileName = ""
referenceFileName = ""

doInstrument = False

# How many times does each benchmark get run?
runCount = 3

# How many mismatched lines warrant detailed report
mismatchLimit = 5

# Graph: (#node, #edge, #seed)
benchmarkDict = {
    "A": (64,   200,    1),
    "B": (512,  4000,   2),
    "C": (1024, 10000,  3),
}

defaultTests = benchmarkDict.keys()

# Does the test program run on GPU
gpu = False

# Latedays machines have 12 cores
threadLimit = 12
host = os.getenv('HOSTNAME')
# Reduce default number of threads on GHC machines
if host is not None and 'ghc' in host:
    threadLimit = 8
defaultThreadCount = threadLimit
threadCounts = [defaultThreadCount]

uniqueId = ""

def outmsg(s, noreturn = False):
    if len(s) > 0 and s[-1] != '\n' and not noreturn:
        s += "\n"
    sys.stdout.write(s)
    sys.stdout.flush()
    if outFile is not None:
        outFile.write(s)

def testName(testId, threadCount):
    root = "%sx%.2d" % (testId, threadCount)
    if uniqueId != "":
        root +=  ("-" + uniqueId)
    return root + ".txt"

def graphFileName(fname):
    return graphDirectory + '/' + fname

def saveFileName(useRef, testId, threadCount):
    return saveDirectory + "/" + ("ref-" if useRef else "tst-") + testName(testId, threadCount)

def doRun(cmdList, progFileName):
    cmdLine = " ".join(cmdList)
    progFile = subprocess.PIPE
    if progFileName is not None:
        try:
            progFile = open(progFileName, 'w')
        except:
            print("Couldn't open output file '%s'" % progFileName)
            return None
    tstart = time.perf_counter()
    try:
        outmsg("Running '%s > %s'" % (cmdLine, progFileName))
        progProcess = subprocess.Popen(cmdList, stdout = progFile, stderr = subprocess.PIPE)
        progProcess.wait()
        if progFile != subprocess.PIPE:
            progFile.close()
        returnCode = progProcess.returncode
        # Echo any results printed by simulator on stderr onto stdout
        for line in progProcess.stderr:
            outmsg(line)
    except Exception as e:
        print("Execution of command '%s' failed. %s" % (cmdLine, e))
        if progFile != subprocess.PIPE:
            progFile.close()
        return None
    if returnCode == 0:
        delta = time.perf_counter() - tstart
        msecs = delta * 1e6
        if progFile != subprocess.PIPE:
            progFile.close()
        return msecs
    else:
        print("Execution of command '%s' gave return code %d" % (cmdLine, returnCode))
        if progFile != subprocess.PIPE:
            progFile.close()
        return None

def bestRun(cmdList, progFileName):
    sofar = 1e6
    for r in range(runCount):
        if runCount > 1:
            outmsg("Run #%d:" % (r+1), noreturn = True)
        secs = doRun(cmdList, progFileName)
        if secs is None:
            return None
        sofar = min(sofar, secs)
    return sofar

def getGraph(nnode, nedge, seed):
    gfname = graphName(nnode, nedge, seed)
    if not os.path.exists(gfname):
        # generate graph
        generate_graph(nnode, nedge, seed)
    return gfname

def runBenchmark(useRef, testId, threadCount):
    global referenceFileName, testFileName
    nnode, nedge, seed = benchmarkDict[testId]
    gfname = getGraph(nnode, nedge, seed)
    results = [nnode, nedge, seed, str(threadCount)]
    prog = stdProgram if useRef else seqProgram if threadCount == 1 else ompProgram
    clist = ["-g", graphFileName(gfname)]#, "-t", str(threadCount)]
    # if doInstrument:
    #     clist += ["-I"]
    fileName = None
    if not useRef:
        name = testName(testId, threadCount)
        outmsg("+++++++++++++++++ Benchmark %s +++++++++++++++++" % name)
    if doCheck:
        if not os.path.exists(saveDirectory):
            try:
                os.mkdir(saveDirectory)
            except Exception as e:
                outmsg("Couldn't create directory '%s' (%s)" % (saveDirectory, str(e)))
                progFile = subprocess.PIPE
        fileName = saveFileName(useRef, testId, threadCount)
        if useRef:
            referenceFileName = fileName
        else:
            testFileName = fileName

    cmd = [prog] + clist
    cmdLine = " ".join(cmd)
    secs = bestRun(cmd, fileName)
    if secs is None:
        return None
    else:
        results.append("%.2f" % secs)
        return results

def formatTitle():
    ls = ["# Node", "# Edge", "Seed", "Threads", "Test (ms)"]
    if doCheck:
         ls += ["Ref (ms)"]
    return " ".join("{0:<10}".format(t) for t in ls)

def sweep(testList, threadCount):
    tcount = 0
    rcount = 0
    sum = 0.0
    refSum = 0.0
    resultList = []
    cresults = None
    totalPoints = 0
    for t in testList:
        ok = True
        results = runBenchmark(False, t, threadCount)
        if results is not None and doCheck:
            cresults = runBenchmark(True, t, threadCount)
            if referenceFileName != "" and testFileName != "":
                ok = checkFiles(referenceFileName, testFileName)
        if not ok:
            outmsg("TEST FAILED")
        if  results is not None:
            tcount += 1
            if cresults is not None:
                msecs = cresults[-1]
                results += [msecs]
            resultList.append(results)
    outmsg("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    outmsg(formatTitle())
    outmsg("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    for result in resultList:
        outmsg(" ".join("{0:<10}".format(r) for r in result))

def generateFileName(template):
    global uniqueId
    myId = ""
    n = len(template)
    ls = []
    for i in range(n):
        c = template[i]
        if c == 'X':
            c = chr(random.randint(ord('0'), ord('9')))
        ls.append(c)
        myId += c
    if uniqueId == "":
        uniqueId = myId
    return "".join(ls)

def run():
    global threadCounts
    global gpu

    testList = list(defaultTests)

    if gpu:
        raise NotImplementedException();
    else:
        gstart = time.perf_counter()
        for t in threadCounts:
            tstart = time.perf_counter()
            sweep(testList, t)
            secs = time.perf_counter() - tstart
            print("Test time for %d threads = %.2f secs." % (t, secs))
        if len(threadCounts) > 1:
            secs = time.perf_counter() - gstart
            print("Overall test time = %.2f secs." % (secs))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-Q", "--quick", action="store_true",
                    help="Quick mode: do not compare with reference solution")
    parser.add_argument("-I", "--instrument", action="store_true",
                    help="Instrument activities")
    parser.add_argument("-r", "--runs", type=int,
                    help="Specify number of times each benchmark is run")
    parser.add_argument("-t", "--threadCount", type=int,
                    help="Specify number of OMP threads.\n If > 1, will run johnson_omp.  Else will run johnson_seq")
    parser.add_argument("-G", "--gpu", action="store_true",
                    help="Run johnson_cuda")
    parser.add_argument("-f", "--outfile", type=str,
                    help="Create output file recording measurements")

    args = parser.parse_args()

    doCheck = not args.quick if args.quick is not None else doCheck
    doInstrument = args.instrument if args.instrument is not None else doInstrument
    runCount = args.runs if args.runs is not None else runCount
    threadCounts = [args.threadCount] if args.threadCount is not None else threadCounts
    gpu = args.gpu if args.gpu is not None else gpu
    outFile = args.outfile if args.outfile is not None else outFile

    run()
