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
instColumns = ["load_graph", "print_graph", "bellman_ford", "dijkstra", "overhead", "unknown", "elapsed"]

# How many times does each benchmark get run?
runCount = 3

# How many mismatched lines warrant detailed report
mismatchLimit = 5

# Graph: (#node, #edge, #seed)
benchmarkDict = {
    # density = 0.5
    "small":  (256,   16320,   1),
    "medium": (1024,  517888,  2),
    # "large":  (4096,  4194304, 3),
    # density = 0.125
    "medium-sparse": (1024, 129472, 2)
}

scalingList = ['small', 'medium', 'medium-sparse']

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
    if isinstance(s, bytes):
        s = s.decode("utf-8", "ignore")
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

def parseInstrumentResult(s):
    res = s.decode("utf-8", "ignore").split()
    msecs, task = res[0], res[-1]
    return msecs, task

def doRun(cmdList, progFileName):
    cmdLine = " ".join(cmdList)
    progFile = subprocess.PIPE
    instDict = {} # instrumentation results
    if progFileName is not None:
        try:
            progFile = open(progFileName, 'w')
        except:
            print("Couldn't open output file '%s'" % progFileName)
            return None, {}
    tstart = time.perf_counter()
    try:
        outmsg("Running '%s > %s'" % (cmdLine, progFileName))
        progProcess = subprocess.Popen(cmdList, stdout = progFile, stderr = subprocess.PIPE)
        progProcess.wait()
        if progFile != subprocess.PIPE:
            progFile.close()
        returnCode = progProcess.returncode
        # Echo any results printed by simulator on stderr onto stdout
        if doInstrument:
            for line in progProcess.stderr:
                msecs, task = parseInstrumentResult(line)
                instDict[task] = msecs
        else:
            for line in progProcess.stderr:
                outmsg(line)
    except Exception as e:
        print("Execution of command '%s' failed. %s" % (cmdLine, e))
        if progFile != subprocess.PIPE:
            progFile.close()
        return None, {}
    if returnCode == 0:
        delta = time.perf_counter() - tstart
        msecs = delta * 1e3
        if progFile != subprocess.PIPE:
            progFile.close()
        return msecs, instDict
    else:
        print("Execution of command '%s' gave return code %d" % (cmdLine, returnCode))
        if progFile != subprocess.PIPE:
            progFile.close()
        return None, {}

def bestRun(cmdList, progFileName):
    sofar = 1e6
    d = {}
    for r in range(runCount):
        if runCount > 1:
            outmsg("Run #%d:" % (r+1), noreturn = True)
        secs, instDict = doRun(cmdList, progFileName)
        if secs is None:
            return None, {}
        if secs < sofar:
            sofar = secs
            d = instDict
        #sofar = min(sofar, secs)
    return sofar, d

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
    clist = ["-g", gfname]
    if prog not in [stdProgram, seqProgram]:
        clist += ["-t", str(threadCount)]
    if doInstrument:
        clist += ["-I"]
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
    secs, instDict = bestRun(cmd, fileName)
    if secs is None:
        return None, {}
    else:
        results.append("%.2f" % secs)
        return results, instDict

def formatTitle():
    ls = ["# Node", "# Edge", "Seed", "Threads", "Test (ms)"]
    if doCheck:
         ls += ["Base (ms)", "Speedup"]
    return " ".join("{0:<10}".format(t) for t in ls)

def printTitle():
    outmsg("+" * 80)
    outmsg(formatTitle())
    outmsg("+" * 80)

def sweep(testList, threadCounts):
    tcount = 0
    rcount = 0
    sum = 0.0
    refSum = 0.0
    resultList = []
    cresults = None
    totalPoints = 0
    instResultList = []
    instResult = None
    cinstResult = None
    for t in testList:
        if len(threadCounts) > 1 and doCheck:
            cresults, cinstResult = runBenchmark(True, t, 1)
        for tc in threadCounts:
            tstart = time.perf_counter()
            ok = True
            results, instResult = runBenchmark(False, t, tc)
            if results is not None and doCheck and len(threadCounts) <= 1:
                cresults, _ = runBenchmark(True, t, tc)
                if referenceFileName != "" and testFileName != "":
                    ok = checkFiles(referenceFileName, testFileName)
            if not ok:
                outmsg("TEST FAILED")
            if results is not None:
                tcount += 1
                if cresults is not None:
                    msecs = cresults[-1]
                    speedup = float(msecs) / float(results[-1])
                    results += [msecs, "%.2fx" % speedup]
                resultList.append(results)
            if instResult is not None:
                instResultList.append(instResult)
            secs = time.perf_counter() - tstart
            print("Test time for %d threads = %.2f secs." % (tc, secs))
        if len(threadCounts) > 1:
            printTitle() # one table per test
            for result in resultList:
                outmsg(" ".join("{0:<10}".format(r) for r in result))

            if len(instResultList) > 0:
                generateInstResultTable(resultList, instResultList, cinstResult)

            resultList = []
            instResultList = []

    if len(threadCounts) == 1:
        printTitle() # one table in total
        for result in resultList:
            outmsg(" ".join("{0:<10}".format(r) for r in result))

        if len(instResultList) > 0:
            generateInstResultTable(resultList, instResultList, cinstResult)


def generateInstResultTable(resultList, instResultList, cinstResult):
    bf, dijkstra = None, None
    cols = ["Thread", "load_graph", "print_graph", "bellman_ford", "dijkstra", "overhead", "unknown", "elapsed", "BF Speedup", "D Speedup"]
    widths = {"Thread": 8, "load_graph": 12, "print_graph": 13, "bellman_ford": 14, "dijkstra": 10, "overhead": 10, "unknown": 8, "elapsed": 8, "BF Speedup": 12, "D Speedup": 12}

    outmsg("+" * 115)
    if len(resultList) > 0:
        nnode, nedge, seed = resultList[0][:3]
        outmsg(" " * 35 + "{} Nodes, {} Edges, Seed {}".format(nnode, nedge, seed))
    msg = "{0:<8} {1:<12} {2:<13} {3:<14} {4:<10} {5:<10} {6:<8} {7:<8} {8:<12} {9:<12}".format("Thread", "load_graph", "print_graph", "bellman_ford", "dijkstra", "overhead", "unknown", "elapsed", "BF Speedup", "D Speedup")
    outmsg(msg)
    outmsg("+" * 115)

    bf_ref, d_ref = 0., 0.

    if cinstResult is not None:
        l, p, bf, d, o, u, e = [cinstResult.get(c, 0.0) for c in instColumns]
        msg = "{0:<8} {1:<12} {2:<13} {3:<14} {4:<10} {5:<10} {6:<8} {7:<8}".format("Ref", l, p, bf, d, o, u, e)
        outmsg(msg)
        bf_ref, d_ref = float(bf), float(d)
    for result, instResult in zip(resultList, instResultList):
        l, p, bf, d, o, u, e = [instResult.get(c, 0.0) for c in instColumns]
        bf_speedup, dijkstra_speedup = "-", "-"
        if bf and bf_ref:
            bf_speedup = "%.2fx" % (bf_ref/float(bf))
        if d and d_ref:
            dijkstra_speedup = "%.2fx" % (d_ref/float(d))
        msg = "{0:<8} {1:<12} {2:<13} {3:<14} {4:<10} {5:<10} {6:<8} {7:<8} {8:<12} {9:<12}".format(result[3], l, p, bf, d, o, u, e, bf_speedup, dijkstra_speedup)
        outmsg(msg)

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
        sweep(testList, threadCounts)
        if len(threadCounts) > 1:
            secs = time.perf_counter() - gstart
            print("Overall test time = %.2f secs." % (secs))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-Q", "--quick", action="store_true",
                    help="Quick mode: do not compare with reference solution")
    parser.add_argument("-I", "--instrument", action="store_true",
                    help="Instrument activities")
    parser.add_argument("-S", "--scale", action="store_true",
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
    # Scaling mode: vary the number of threads
    if args.scale:
        threadCounts = list(range(1, defaultThreadCount+1))
        defaultTests = scalingList
        stdProgram = seqProgram # use seq program as baseline when checking for perf scaling
    else:
        threadCounts = [args.threadCount] if args.threadCount is not None else threadCounts
    gpu = args.gpu if args.gpu is not None else gpu
    outFile = args.outfile if args.outfile is not None else outFile

    run()
