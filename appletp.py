#!/usr/bin/env python

import shell
import walkdir
import multijobs

import sys
import os
import multiprocessing
import plistlib

_pngcrush = '%s/Platforms/iPhoneOS.platform/Developer/usr/bin/pngcrush -revert-iphone-optimizations -q \'%%s\' \'%%s\'' % (shell.shell('xcode-select -print-path').splitlines()[0],)
_plutil = 'plutil -convert xml1 \'%s\' -o \'%s\''

def _everyfile(parent, child, isDir, dstdir=None, src_base_index=None, cmds=None):
    src = walkdir.join(parent, child)
    dst = walkdir.join(walkdir.join(dstdir, parent[src_base_index:]), child)
    if not isDir:
        nm, ext = os.path.splitext(src)
        src_png = nm + '.png'
        if ext == '.plist' and os.path.exists(src_png):
            cmd = {'c': 'plist', 'tmpl': _plutil, 'src': src, 'dst': dst}
            cmds.put(cmd)
            dst_png = os.path.splitext(dst)[0] + '.png'
            cmd = {'c': 'png', 'tmpl': _pngcrush, 'src': src_png, 'dst': dst_png}
            cmds.put(cmd)

def _worker(idx, cmds, msz):
    while True:
        try:
            print '[%d] @@4' % (idx,)
            cmd = cmds.get_nowait()
            print '[%d] @@4e' % (idx,)
            if cmd['c'] in ('plist', 'png'):
                src = cmd['src']
                dst = cmd['dst']
                dnm = os.path.dirname(dst)
                if not os.path.exists(dnm):
                    os.makedirs(dnm, 0755)

                print '[%d] @@3 %s' % (idx, cmd['tmpl'] % (src, dst))
                shell.shell(cmd['tmpl'] % (src, dst))
                print '[%d] @@3e' % (idx,)
                if cmd['c'] == 'plist':
                    pl = plistlib.readPlist(dst)
                    changed = False
                    if 'textureFileName' not in pl['metadata']:
                        pl['metadata']['textureFileName'] = os.path.splitext(os.path.basename(dst))[0] + '.png'
                        changed = True
                    to_rename = {}
                    for frame, v in pl['frames'].iteritems():
                        nm, ext = os.path.splitext(frame)
                        if ext != '.png':
                            ext, n = ext.split()
                            to_rename[frame] = '%s_%s%s' % (nm, n, ext)
                    for f, t in to_rename.iteritems():
                        pl['frames'][t] = pl['frames'].pop(f)
                    changed = changed or bool(to_rename)
                    if changed:
                        print '[%d] @@2' % (idx,)
                        plistlib.writePlist(pl, dst)
                        print '[%d] @@2e' % (idx,)

            print '[%d] @@1' % (idx,)
            proc = msz - cmds.qsize()
            print '[%d] @@1e' % (idx,)
            print '[%d] %d/%d %.1f%%' % (idx, proc, msz, proc*100.0/msz)

        except multiprocessing.managers.Queue.Empty, e:
            break

    print '[%d] exited' % (idx,)

if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    src_base = os.path.basename(src)
    src_base_index = src.index(src_base)

    mgr = multiprocessing.Manager()
    cmds = mgr.Queue()
    walkdir.walkdir(src, _everyfile, dstdir=dst, src_base_index=src_base_index, cmds=cmds)
    n = multiprocessing.cpu_count()
    argslist = [(i, cmds, cmds.qsize()) for i in xrange(n)]
    multijobs.multijobs(_worker, argslist, n)
    mgr.shutdown()
    mgr.join()
    
