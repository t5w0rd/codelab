#!/usr/bin/env python

import shell
import walkdir

import sys
import os
import shutil

_pngcrush = '%s/Platforms/iPhoneOS.platform/Developer/usr/bin/pngcrush -revert-iphone-optimizations -q' % (shell.shell('xcode-select -print-path').splitlines()[0],)

def _everyfile(parent, child, isDir, dst=None, src_base_index=None, cmds=None):
    src = walkdir.join(parent, child)
    dst = walkdir.join(walkdir.join(dst, parent[src_base_index:]), child)
    if isDir:
        #print 'D', dst
        os.mkdir(dst, 0755)
        cmd = {'c': 'mkdir', 'dst': dst, 'mode': 0755}
        cmds.append(cmd)
    else:
        #print 'F', dst
        #print 'cp %s %s' % (src, dst)
        if os.path.splitext(src)[1].lower() == '.png':
            #print shell.shell('%s \'%s\' \'%s\'' % (_pngcrush, src, dst)),
            cmd = {'c': 'shell', 'shell': '%s \'%s\' \'%s\'' % (_pngcrush, src, dst)}
            cmds.append(cmd)
        else:
            #shutil.copy(src, dst)
            cmd = {'c': 'cp', 'src': src, 'dst': dst}
            cmds.append(cmd)

if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    src_base = os.path.basename(src)
    src_base_index = src.index(src_base)
    dstdir = walkdir.join(dst, src_base)
    os.makedirs(dstdir, 0755)

    cmds = []
    walkdir.walkdir(src, _everyfile, dst=dst, src_base_index=src_base_index, cmds=cmds)
    print len(cmds)
