#!/usr/bin/python

# Perform regression test, comparing outputs of different johnson implementation

import argparse
import subprocess
import sys
import math
import os
import os.path
import getopt

# General information

# Gold-standard reference program
standardProg = "./johnson-boost"

# Simulator being tested
testProg = "./johnson-seq"
ompTestProg = "./johnson-omp"
cudaTestProg = "/johnson-cuda"

# Directories
# graph files
dataDir = "./graphs"
# cache for holding reference solver results
cacheDir = "./regression-cache"

# Limit on how many mismatches get reported
mismatchLimit = 5

# Series of tests to perform.
# Each defined by:
#  graph file name
regressionList = [
    "small.txt",
    "graph1.txt",
    # "graph2.txt",
    # "graph3.txt",
    # "graph4.txt",
    # "graph5.txt",
    # "graph6.txt",
    # "graph7.txt",
    # "graph8.txt",
]

def regressionName(params, standard = True, short = False):
    #name = "%s+%s+%.2d+%s+%.2d" % params
    name = params
    if short:
        return name
    return ("ref" if standard else "tst") +  "-" + name

def regressionCommand(params, standard = True, threadCount = 1, gpu = False):
    graphFile = params

    graphFileName = dataDir + "/" + graphFile

    prog = ''
    prelist = []

    if standard:
        prog = standardProg
    elif gpu:
        prog = cudaTestProg
    elif threadCount > 1:
        prog = ompTestProg
    else:
        prog = testProg

    cmd = prelist + [prog, "-g", graphFileName]

    if standard:
        pass # any additional arg goes here
    elif gpu:
        pass # any additional arg goes here
    elif threadCount > 1:
        cmd += ["-t", str(threadCount)]
    return cmd


def runImpl(params, standard = True, threadCount = 1, gpu = False):
    cmd = regressionCommand(params, standard, threadCount, gpu)
    cmdLine = " ".join(cmd)

    pname = cacheDir + "/" + regressionName(params, standard)
    try:
        outFile = open(pname, 'w')
    except Exception as e:
        sys.stderr.write("Couldn't open file '%s' to write.  %s\n" % (pname, e))
        return False
    try:
        sys.stderr.write("Executing " + cmdLine + " > " + regressionName(params, standard) + "\n")
        graphProcess = subprocess.Popen(cmd, stdout = outFile)
        graphProcess.wait()
        outFile.close()
    except Exception as e:
        sys.stderr.write("Couldn't execute " + cmdLine + " > " + regressionName(params, standard) + " " + str(e) + "\n")
        outFile.close()
        return False
    return True

def checkFiles(refPath, testPath):
    badLines = 0
    lineNumber = 0
    try:
        rf = open(refPath, 'r')
    except:
        sys.sterr.write("Couldn't open reference file '%s'\n" % refPath);
        return False
    try:
        tf = open(testPath, 'r')
    except:
        sys.stderr.write("Couldn't open test file '%s'\n" % testPath);
        return False
    while True:
        rline = rf.readline()
        tline = tf.readline()
        lineNumber +=1
        if rline == "":
            if tline == "":
                break
            else:
                badLines += 1
                sys.stderr.write("Mismatch at line %d.  File %s ended prematurely\n" % (lineNumber, refPath))
                break
        elif tline == "":
            badLines += 1
            sys.stderr.write("Mismatch at line %d.  File %s ended prematurely\n" % (lineNumber, testPath))
            break
        if rline[-1] == '\n':
            rline = rline[:-1]
        if tline[-1] == '\n':
            tline = tline[:-1]
        if rline != tline:
            badLines += 1
            if badLines <= mismatchLimit:
                sys.stderr.write("Mismatch at line %d.\n" % (lineNumber))
                # sys.stderr.write("Mismatch at line %d.  File %s:'%s'.  File %s:'%s'\n" % (lineNumber, refPath, rline, testPath, tline))
    rf.close()
    tf.close()
    if badLines > 0:
        sys.stderr.write("%d total mismatches.  Files %s, %s\n" % (badLines, refPath, testPath))
    return badLines == 0

def regress(params, threadCount, gpu):
    sys.stderr.write("+++++++++++++++++ Regression %s +++++++++++++++\n" % regressionName(params, standard=True, short = True))
    refPath = cacheDir + "/" + regressionName(params, standard = True)
    if not os.path.exists(refPath):
        if not runImpl(params, standard = True, gpu = False):
            sys.stderr.write("Failed to run with reference solver\n")
            return False

    if not runImpl(params, standard = False, threadCount = threadCount, gpu = gpu):
        sys.stderr.write("Failed to run with test solver\n")
        return False

    testPath = cacheDir + "/" + regressionName(params, standard = False)

    return checkFiles(refPath, testPath)

def run(flushCache, threadCount, gpu, doAll):

    if flushCache and os.path.exists(cacheDir):
        try:
            graphProcess = subprocess.Popen(["rm", "-rf", cacheDir])
            graphProcess.wait()
        except Exception as e:
            sys.stderr.write("Could not flush old result cache: %s" % str(e))
    if not os.path.exists(cacheDir):
        try:
            os.mkdir(cacheDir)
        except Exception as e:
            sys.stderr.write("Couldn't create directory '%s'" % cacheDir)
            sys.exit(1)
    goodCount = 0
    allCount = 0
    rlist = regressionList
    for p in rlist:
        allCount += 1
        if regress(p, threadCount, gpu):
            sys.stderr.write("Regression %s Passed\n" % regressionName(p, standard = False))
            goodCount += 1
        else:
            sys.stderr.write("Regression %s Failed\n" % regressionName(p, standard = False))
    totalCount = len(rlist)
    message = "SUCCESS" if goodCount == totalCount else "FAILED"
    sys.stderr.write("Regression set size %d.  %d/%d tests successful. %s\n" % (totalCount, goodCount, allCount, message))

def str_to_bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in {'false', 'f', '0', 'no', 'n'}:
        return False
    elif value.lower() in {'true', 't', '1', 'yes', 'y'}:
        return True
    raise ValueError(f'{value} is not a valid boolean value')

if __name__ == "__main__":
    doAll = False

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--flushCache", action="store_true",
                    help="Clear expected result cache")
    parser.add_argument("-t", "--threadCount", type=int,
                    help="Specify number of OMP threads.\n If > 1, will run johnson-omp.  Else will run johnson-seq")
    parser.add_argument("-g", "--gpu", type=str,
                    help="Run johnson-cuda")

    args = parser.parse_args()

    threadCount = args.threadCount or 8
    flushCache = args.flushCache or False
    gpu = args.gpu or False

    run(flushCache, threadCount, gpu, doAll)
