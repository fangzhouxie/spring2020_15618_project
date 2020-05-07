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
doRegress = False
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
    "small":  (256,   16384,   1),
    "medium": (1024,  262144,  2),
    "large":  (4096,  4194304, 3),
    # density = 0.125
    "medium-sparse": (1024, 65536, 2)
}

scalingList = ['small', 'medium', 'medium-sparse', 'large']

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
        outmsg("Running '%s > %s'" % (cmdLine, progFileName) if progFileName is not None else "Running '%s'" % (cmdLine))
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
    return sofar, d

def getGraph(nnode, nedge, seed):
    gfname = graphName(nnode, nedge, seed)
    if not os.path.exists(gfname):
        # generate graph
        generate_graph(nnode, nedge, seed)
    return gfname

def getProgram(useRef, threadCount, gpu):
    if useRef: return seqProgram #stdProgram
    if gpu: return cudaProgram
    if threadCount > 1: return ompProgram
    return seqProgram

def runBenchmark(useRef, testId, threadCount, gpu=False):
    global referenceFileName, testFileName
    nnode, nedge, seed = benchmarkDict[testId]
    gfname = getGraph(nnode, nedge, seed)
    results = [nnode, nedge, seed, str(threadCount)]
    prog = getProgram(useRef, threadCount, gpu)
    clist = ["-g", gfname]
    if prog == ompProgram:
        clist += ["-t", str(threadCount)]
    if doInstrument:
        clist += ["-I"]
    fileName = None
    if not useRef:
        name = testName(testId, threadCount)
        outmsg("+++++++++++++++++ Benchmark %s +++++++++++++++++" % name)
    if doRegress: #doCheck:
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
        clist += ["-P"] # print output graph

    cmd = [prog] + clist
    cmdLine = " ".join(cmd)
    secs, instDict = bestRun(cmd, fileName)
    if secs is None:
        return None, {}
    else:
        results.append("%.2f" % secs)
        return results, instDict

def formatTitle():
    ls = ["# Node", "# Edge", "Seed", "GPU" if gpu else "Threads", "Test (ms)"]
    if doCheck:
         ls += ["Base (ms)", "Speedup"]
    return " ".join("{0:<10}".format(t) for t in ls)

def printTitle():
    outmsg("+" * 75)
    outmsg(formatTitle())
    outmsg("+" * 75)

def sweep(testList, threadCounts, gpu=False):
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
        # run benchmark baseline once at the beginning
        if (len(threadCounts) > 1 or gpu) and doCheck:
            outmsg("+++++++++++++++++ Benchmark Baseline +++++++++++++++++")
            cresults, cinstResult = runBenchmark(True, t, 1)

        for tc in threadCounts:
            tstart = time.perf_counter()
            ok = True
            results, instResult = runBenchmark(False, t, tc, gpu)
            if results is not None and doCheck and (len(threadCounts) <= 1 and not gpu):
                cresults, _ = runBenchmark(True, t, tc, gpu)
                if doRegress and referenceFileName != "" and testFileName != "":
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

        if len(threadCounts) > 1 or gpu: #one table per test
            if doInstrument:
                generateInstResultTable(resultList, instResultList, cinstResult)
            else:
                printTable(resultList)

            resultList = []
            instResultList = []

    # print one table at the end
    if len(threadCounts) == 1 and not gpu:
        if doInstrument:
            generateInstResultTable(resultList, instResultList, cinstResult)
        else:
            printTable(resultList)

def printTable(resultList):
    printTitle() # one table in total
    for result in resultList:
        outmsg(" ".join("{0:<10}".format(r) for r in result))

def generateInstResultTable(resultList, instResultList, cinstResult):
    bf, dijkstra = None, None

    outmsg("+" * 105)
    if len(resultList) > 0:
        nnode, nedge, seed = resultList[0][:3]
        outmsg(" " * 35 + "{} Nodes, {} Edges, Seed {}".format(nnode, nedge, seed))
    msg = "{0:<8} {1:<14} {2:<10} {3:<10} {4:<8} {5:<8} {6:<12} {7:<12} {8:<15}".format("GPU" if gpu else "Thread", "bellman_ford", "dijkstra", "overhead", "unknown", "elapsed", "BF Speedup", "D Speedup", "Overall Speedup")
    outmsg(msg)
    outmsg("+" * 105)

    bf_ref, d_ref, elapsed_ref = 0., 0., 0.

    if cinstResult is not None:
        l, p, bf, d, o, u, e = [cinstResult.get(c, 0.0) for c in instColumns]
        msg = "{0:<8} {1:<14} {2:<10} {3:<10} {4:<8} {5:<8}".format("Ref", bf, d, o, u, e)
        outmsg(msg)
        bf_ref, d_ref, elapsed_ref = float(bf), float(d), (float(e) - float(l) - float(p)) # remove load_graph and print_graph
    for result, instResult in zip(resultList, instResultList):
        l, p, bf, d, o, u, e = [instResult.get(c, 0.0) for c in instColumns]
        elapsed = float(e) - float(l) - float(p) # remove load_graph and print_graph
        e = "%.2f" % elapsed
        bf_speedup, dijkstra_speedup, speedup = "-", "-", "-"
        if bf and bf_ref:
            bf_speedup = "%.2fx" % (bf_ref/float(bf))
        if d and d_ref:
            dijkstra_speedup = "%.2fx" % (d_ref/float(d))
        if e and elapsed_ref:
            speedup = "%.2fx" % (elapsed_ref/elapsed)
        msg = "{0:<8} {1:<14} {2:<10} {3:<10} {4:<8} {5:<8} {6:<12} {7:<12} {8:<15}".format("x" if gpu else result[3], bf, d, o, u, e, bf_speedup, dijkstra_speedup, speedup)
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

    gstart = time.perf_counter()
    sweep(testList, threadCounts, gpu)
    if len(threadCounts) > 1:
        secs = time.perf_counter() - gstart
        print("Overall test time = %.2f secs." % (secs))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-Q", "--quick", action="store_true",
                    help="Quick mode: do not compare performance with reference solution")
    parser.add_argument("-V", "--verify", action="store_true",
                    help="Verify result against reference solution")
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
    doRegress = args.verify if doCheck else False
    doInstrument = args.instrument if args.instrument is not None else doInstrument
    runCount = args.runs if args.runs is not None else runCount
    if doInstrument:
        stdProgram = seqProgram # instrumentation not available for johnson_boost
    # Scaling mode: vary the number of threads
    if args.scale:
        threadCounts = list(range(2, defaultThreadCount+1))
        defaultTests = scalingList
        stdProgram = seqProgram # use seq program as baseline when checking for perf scaling
    else:
        threadCounts = [args.threadCount] if args.threadCount is not None else threadCounts
    if args.gpu:
        gpu = True
        threadCounts = [1]
    outFile = args.outfile if args.outfile is not None else outFile

    run()
