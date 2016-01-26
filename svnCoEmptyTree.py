#!/usr/bin/env python

import os, sys
#from shell import *
#from walkdir import *
import shell, walkdir

def svnUpEmptyTree(path):
    if path[-1] != "/":
        path += "/"

    listFiles = shell.shell("svn ls \"%s\"" % (path, )).splitlines()
    if len(listFiles) > 0:
        strArgv = ""
        for f in listFiles:
            if f[-1] == "/":
                strArgv += " \"%s%s\"" % (path, f)
                
        if len(strArgv) > 0:
            print shell.shell("svn up --depth empty%s" % (strArgv, ))

            for f in listFiles:
                if f[-1] == "/":
                    svnUpEmptyTree("%s%s" % (path, f))

def svnCoEmptyTree(remote, local):
    print shell.shell("svn co --depth empty \"%s\" \"%s\"" % (remote, local))
    svnUpEmptyTree(local)

def svnCoEmptyTree2(remote, local):
    if local[-1] != "/":
        local += "/"

    print shell.shell("svn co --depth empty \"%s\" \"%s\"" % (remote, local))
    strFiles = shell.shell("svn ls --depth infinity %s" % (local, ))
    listFiles = strFiles.splitlines()
    if len(listFiles) > 0:
        listStrArgv = []
        strArgv = ""
        for f in listFiles:
            if f[-1] == "/":
                strArgv += " \"%s%s\"" % (local, f)
                if len(strArgv) > 4096:
                    listStrArgv.append(strArgv)
                    strArgv = ""

        if len(strArgv) > 0:
            listStrArgv.append(strArgv)

        if len(listStrArgv) > 0:
            for strArgv in listStrArgv:
                print shell.shell("svn up --depth empty%s" % (strArgv, ))
            
def main():
    remote = sys.argv[1]
    local = sys.argv[2]
    svnCoEmptyTree2(remote, local)

if __name__ == "__main__":
    main()
