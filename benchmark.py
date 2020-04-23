#!/usr/bin/python
# Measure performance
# Adapted from https://github.com/cmu15418/asst3-s20/blob/master/code/benchmark.py

import argparse
import subprocess
import sys
import os
import os.path
import getopt
import math
import datetime
import random

# import rutil

# General information
stdProgram = "./johnson_boost"
seqProgram = "./johnson_seq"
ompProgram = "./johnson_omp"
cudaProgram = "./johnson_cuda"

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

# Graph/rat combinations: testId : (graphFile, ratFile, test name)
benchmarkDict = {
    'small':  'small.txt',
    #'graph1': 'graph1.txt',
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
#defaultSeed = rutil.DEFAULTSEED

uniqueId = ""

def trim(s):
    while len(s) > 0 and s[-1] in '\r\n':
        s = s[:-1]
    return s

def outmsg(s, noreturn = False):
    if len(s) > 0 and s[-1] != '\n' and not noreturn:
        s += "\n"
    sys.stdout.write(s)
    sys.stdout.flush()
    if outFile is not None:
        outFile.write(s)

def testName(testId, threadCount):
    name = benchmarkDict[testId]
    root = "%sx%.2d" % (name, threadCount)
    if uniqueId != "":
        root +=  ("-" + uniqueId)
    return root + ".txt"

def graphFileName(fname):
    return graphDirectory + '/' + fname

def saveFileName(useRef, testId, stepCount, seed, threadCount):
    return saveDirectory + "/" + ("ref" if useRef else "tst") + testName(testId, stepCount, seed, threadCount)

def checkOutputs(referenceFile, testFile, tname):
    if referenceFile == None or testFile == None:
        return True
    badLines = 0
    lineNumber = 0
    while True:
        rline = referenceFile.readline()
        tline = testFile.readline()
        lineNumber +=1
        if rline == "":
            if tline == "":
                break
            else:
                badLines += 1
                outmsg("Test %s.  Mismatch at line %d.  Reference simulation ended prematurely" % (tname, lineNumber))
                break
        elif tline == "":
            badLines += 1
            outmsg("Test %s.  Mismatch at line %d.  Simulation ended prematurely\n" % (tname, lineNumber))
            break
        rline = trim(rline)
        tline = trim(tline)
        if rline != tline:
            badLines += 1
            if badLines <= mismatchLimit:
                outmsg("Test %s.  Mismatch at line %d.  Expected result:'%s'.  Simulation result:'%s'\n" % (tname, lineNumber, rline, tline))
    referenceFile.close()
    testFile.close()
    if badLines > 0:
        outmsg("%d total mismatches.\n" % (badLines))
    return badLines == 0

def doRun(cmdList, simFileName):
    cmdLine = " ".join(cmdList)
    simFile = subprocess.PIPE
    if simFileName is not None:
        try:
            simFile = open(simFileName, 'w')
        except:
            print("Couldn't open output file '%s'" % simFileName)
            return None
    tstart = datetime.datetime.now()
    try:
        outmsg("Running '%s'" % cmdLine)
        simProcess = subprocess.Popen(cmdList, stdout = simFile, stderr = subprocess.PIPE)
        simProcess.wait()
        if simFile != subprocess.PIPE:
            simFile.close()
        returnCode = simProcess.returncode
        # Echo any results printed by simulator on stderr onto stdout
        for line in simProcess.stderr:
            outmsg(line)
    except Exception as e:
        print("Execution of command '%s' failed. %s" % (cmdLine, e))
        if simFile != subprocess.PIPE:
            simFile.close()
        return None
    if returnCode == 0:
        delta = datetime.datetime.now() - tstart
        secs = delta.seconds + 24 * 3600 * delta.days + 1e-6 * delta.microseconds
        if simFile != subprocess.PIPE:
            simFile.close()
        return secs
    else:
        print("Execution of command '%s' gave return code %d" % (cmdLine, returnCode))
        if simFile != subprocess.PIPE:
            simFile.close()
        return None

def bestRun(cmdList, simFileName):
    sofar = 1e6
    for r in range(runCount):
        if runCount > 1:
            outmsg("Run #%d:" % (r+1), noreturn = True)
        secs = doRun(cmdList, simFileName)
        if secs is None:
            return None
        sofar = min(sofar, secs)
    return sofar

def runBenchmark(useRef, testId, threadCount):
    global referenceFileName, testFileName
    gfname = benchmarkDict[testId]
    results = [testId, str(threadCount)]
    prog = stdProgram if useRef else seqProgram if threadCount == 1 else ompProgram
    clist = ["-g", graphFileName(gfname)]#, "-t", str(threadCount)]
    # if doInstrument:
    #     clist += ["-I"]
    simFileName = None
    if not useRef:
        name = testName(testId, threadCount)
        outmsg("+++++++++++++++++ Benchmark %s +++++++++++++++++" % name)
    # if doCheck:
    #     if not os.path.exists(saveDirectory):
    #         try:
    #             os.mkdir(saveDirectory)
    #         except Exception as e:
    #             outmsg("Couldn't create directory '%s' (%s)" % (saveDirectory, str(e)))
    #             simFile = subprocess.PIPE
    #     clist += ["-i", str(stepCount)]
    #     simFileName = saveFileName(useRef, testId, threadCount)
    #     if useRef:
    #         referenceFileName = simFileName
    #     else:
    #         testFileName = simFileName
    # else:
    # clist += ["-q"]

    cmd = [prog] + clist
    cmdLine = " ".join(cmd)
    secs = bestRun(cmd, simFileName)
    if secs is None:
        return None
    else:
        # rmoves = (nodes * load) * stepCount
        # npm = 1e9 * secs/rmoves
        results.append("%.2f" % secs)
        # results.append("%.2f" % npm)
        return results

def score(npm, rnpm):
    if npm == 0.0:
        return 0
    ratio = rnpm/npm
    nscore = 0.0
    if ratio >= upperThreshold:
        nscore = 1.0
    elif ratio >= lowerThreshold:
        nscore = (ratio-lowerThreshold)/(upperThreshold - lowerThreshold)
    return int(math.ceil(nscore * pointsPerRun))

def formatTitle():
    ls = ["Name", "threads", "secs"]
    # if doCheck:
    #     ls += ["BNPM", "Ratio", "Pts"]
    return "\t".join(ls)

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
        # if results is not None and doCheck:
        #     cresults = runBenchmark(True, t, stepCount, threadCount)
        #     if referenceFileName != "" and testFileName != "":
        #         try:
        #             rfile = open(referenceFileName, 'r')
        #         except:
        #             rfile = None
        #             print "Couldn't open reference simulation output file '%s'" % referenceFileName
        #             ok = False
        #         try:
        #             tfile = open(testFileName, 'r')
        #         except:
        #             tfile = None
        #             print "Couldn't open test simulation output file '%s'" % testFileName
        #             ok = False
        #         if rfile is not None and tfile is not None:
        #             ok = checkOutputs(rfile, tfile, t)
        # if not ok:
        #     outmsg("TEST FAILED.  0 points")
        if  results is not None:
            tcount += 1
            npm = float(results[-1])
            sum += npm
            # if cresults is not None:
            #     rcount += 1
            #     cnpm = float(cresults[-1])
            #     refSum += cnpm
            #     ratio = cnpm/npm if npm > 0 else 0
            #     points = score(npm, cnpm) if ok else 0
            #     totalPoints += points
            #     results += [cresults[-1], "%.3f" % ratio, "%d" % points]
            resultList.append(results)
    outmsg("+++++++++++++++++")
    outmsg(formatTitle())
    outmsg("+++++++++++++++++")
    for r in resultList:
        outmsg("\t".join(r))
    if tcount > 0:
        avg = sum/tcount
        astring = "AVG:\t\t\t\t%.2f" % avg
        if refSum > 0:
            ravg = refSum/rcount
            astring += "\t%.2f" % ravg
        outmsg(astring)
        # if doCheck:
        #     tstring = "TOTAL:\t\t\t\t\t\t\t%d" % totalPoints
        #     outmsg(tstring)

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
        gstart = datetime.datetime.now()
        for t in threadCounts:
            tstart = datetime.datetime.now()
            sweep(testList, t)
            delta = datetime.datetime.now() - tstart
            secs = delta.seconds + 24 * 3600 * delta.days + 1e-6 * delta.microseconds
            print("Test time for %d threads = %.2f secs." % (t, secs))
        if len(threadCounts) > 1:
            delta = datetime.datetime.now() - gstart
            secs = delta.seconds + 24 * 3600 * delta.days + 1e-6 * delta.microseconds
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
