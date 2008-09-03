#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    @copyright: 2008 Marko Laakso, Mika Seppänen, Lari Huttunen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import os
import sys
import string
import md5

from xml.dom import minidom

from opencollab.wiki import CLIWiki
from opencollab.meta import Meta, Func
from gzip import GzipFile

def hashfile(filename):
    print "Hashing" + filename;
    f = file(filename,'rb')     
    hash = md5.new(f.read()).hexdigest();
    f.close();

    return hash

def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def uploadFile(wiki, page, filename, path):
    try:
       file = open(path, "rb")
    except IOError:
       print path + " does not exist." 
       return

    for current, total in wiki.putAttachmentChunked(page, filename, file):
        percent = 100.0 * current / float(max(total, 1))
        status = current, total, percent

        sys.stdout.write("\rsent %d/%d bytes (%.02f%%) " % status)
        sys.stdout.flush()

    sys.stdout.write("done\n")
    sys.stdout.flush()

    file.close()

def handledir( collab, page, path ):
    print "Handling directory: " + path
    metas = Meta()
    metas["category"].add("CategoryTestRun")
    page = hashfile(os.path.join(path,'summary.xml'))
    template = "TestRunTemplate"
    xmldoc = minidom.parse(os.path.join(path,'summary.xml'))
    metas["Test plan"].add( '["%s"]' % page )

    for fact in xmldoc.getElementsByTagName("fact"):
        label = fact.getAttribute("label")
        if label:
            metas[label].add(getText(fact.childNodes))

    gzipped = GzipFile(os.path.join(path, "main.log.gz"), "w")
    gzipped.write(open(os.path.join(path, "main.log")).read())
    gzipped.close()

    for label, file in [['Log', 'main.log.gz'], ['Settings', 'run.set'], ['Settings', 'runinfo'], ['Statistics', 'statistics.csv'], ['Summary', 'summary.txt'], ['Summary', 'summary.xml']]:
        if label:
            metas[label].add("See attachment:" + file)
            uploadFile(collab, page, file, os.path.join(path,file))

    for collection in xmldoc.getElementsByTagName("collection"):
        label = collection.getAttribute("label")
        for fact in collection.getElementsByTagName("fact"):
            metas[label].add(getText(fact.childNodes))

    collab.setMeta(page, metas, template=template, replace=True)

def main():
    parser = optparse.OptionParser()
    parser.add_option( "-c", "--config",
        action="store",
        type="string", dest="cpath",
        help="Config file path.")
    parser.add_option("-v",
        action="store_true", dest="verbose", default=False,
        help="Enable verbose output." )
    parser.set_usage("%prog [options] WIKIURL PAGENAME DIRNAME")

    options, args = parser.parse_args()
    if options.cpath:
        if len(args) == 0:
            page, path = parse_config(options.cpath, args)
        elif len(args) == 1:
            page = parse_config(options.cpath, args)
            path = args.pop()
        elif len(args) == 2:
            page, path = args
        elif len(args) == 3:
            url, page, path = args
            collab = CLIWiki(url, config=options.cpath)
        if len(args) < 3:
            collab = CLIWiki(config=options.cpath)
    elif len(args) != 3:
        parser.error("collab url, page name and directory name have to be defined")
    else:
        url, page, path = args
        collab = CLIWiki(url)

    handledir( collab, page, path )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "Script interrupted via CTRL-C."

