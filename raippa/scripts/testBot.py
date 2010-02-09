# -*- coding: utf-8 -*-
"""
    @copyright: 2008 by Mika Seppänen, Rauli Puuperä, Erno Kuusela
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

#TODO
# * File handling
# * stderr handling
# * better handling for error bytes in data (monkey_feed, etc)

import socket
import os
import sys
import datetime
import subprocess
import xmlrpclib
import re
import shutil
import tempfile
import time
import traceback
import ConfigParser

from optparse import OptionParser

import opencollab.wiki
import opencollab.util

outputtemplate = '''
{{{
%s
}}}
----
 testname:: %s
 file::
----
CategoryTestOutput
'''

#rmlrpc is broken. this monkey patch should fix it
orig_feed = xmlrpclib.ExpatParser.feed

def monkey_feed(self, data):
    return orig_feed(self, re.sub(ur'[\x00-\x08\x0b-\x19]', '?', data))
xmlrpclib.ExpatParser.feed = monkey_feed

def error(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [error] %s" % (date, msg)

def info(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [info] %s" % (date, msg)

def removeLink(line):
    if line.startswith('[['): return line[13:-2]
    return line

def run(args, input, tempdir, timeout=10):

    #open files for stdout and stderr
    outpath = os.path.join(tempdir, "out.txt")
    errpath = os.path.join(tempdir, "err.txt")
    inpath = os.path.join(tempdir, '__input__')

    outfile = open(outpath, "w")
    errfile = open(errpath, "w")
    
    open(inpath, 'w').write(input)
    infile = open(inpath, 'r')

    p = subprocess.Popen(args, shell=True, stdout=outfile, stderr=errfile, stdin=infile)
 
    for i in range(timeout):
        if p.poll() is not None:
            timedout=0
            break
        time.sleep(1)
        
    output = str()
    error = str()

    if timedout:
        os.kill(p.pid, 9)
            
    outfile.close()
    errfile.close()

    error = open(errpath).read()
    output = open(outpath).read()

    #clean files
    os.remove(outpath)
    os.remove(errpath)
    os.remove(inpath)

    return output, error, timedout

def readConfig(file):
    opts = opencollab.util.parseConfig(file)
    return opts

def checking_loop(wiki):
    url = wiki.host

    while True:
        #Get all new history pages with pending status
        info('Lookig for pages')
        picked_pages = wiki.getMeta('CategoryHistory, overallvalue=pending')
        info('Found %d pages' % len(picked_pages))

        if not picked_pages:
            info('No pages. Sleeping')
            time.sleep(10)
            continue
        
        #go thgrough all new pages
        for page in picked_pages:
            info('%s: picked %s' % (url, page))

            path = tempfile.mkdtemp()
	    os.chdir(path)

            info("Created tempdir %s" % path)

            #change the status to picked
            wiki.setMeta(page, {'overallvalue' : ['picked']}, True)

            metas = picked_pages[page]
            user = metas['user'].single().strip('[]')

            # get the attachment filename from the file meta
            info('Writing files')
 
            for filename in metas['file']:
                attachment_file = removeLink(filename)
                #get the source code
                info("Fetching sourcode from %s" % attachment_file)
                try:
                    code = wiki.getAttachment(page, attachment_file)
                except opencollab.wiki.WikiFault, e:
                    if 'There was an error in the wiki side (Nonexisting attachment' in e.args[0]:
                        code = ''
                    else:
                        raise
                # get rid of the _rev<number> in filenames
                open(re.sub('(_rev\d+)', '', removeLink(filename)), 'w').write(code)

            #if there is wrong amount of question page linksd, leave
            #the returned assignment as picked so that other
            #assignments can be checked. 

            if len(metas['question']) != 1:
                error('Invalid meta data in %s! There we %d values!\n' 
                      % (page, len(metas['question'])))
                continue
            
            #get the question pagenmae
            question = metas['question'].single(None)
            question = question.strip('[]')
            
            #find associataed answerpages
           
            answer_pages = wiki.getMeta(question +'/options').values()[0]['answer']
            info("Found %d answer pages" % len(answer_pages))

            regex = re.compile('{{{\s*(.*)\s*}}}', re.DOTALL)

            wrong = list()
            right = list()
            outputs = list()

            #TODO file handling
            for apage in [x.strip('[]') for x in answer_pages]:
                info('getting answers from %s' % apage)
                answer_meta = wiki.getMeta(apage).values()[0]
                testname = answer_meta['testname'].single()
                
                outputpage = None
                inputpage = None

                if 'output' in answer_meta:
                    outputpage = answer_meta['output'].single().strip('[]')
                    outfilesatt = wiki.listAttachments

                if 'input' in answer_meta:
                    inputpage =  answer_meta['input'].single().strip('[]')

                args = answer_meta['parameters'].single()

                input = ''

                if inputpage:
                    content = wiki.getPage(inputpage)
                    input = regex.search(content).group(1)
                    input_meta = wiki.getMeta(inputpage)
                    filelist = input_meta[inputpage]['file']
                    for attachment in filelist:
                        filename = removeLink(attachment)
                        content = wiki.getAttachment(inputpage, filename)
                        info('Writing input file %s' % filename)
                        open(os.path.join(path, filename), 'w').write(content)

                output = ''
                if outputpage:
                    content = wiki.getPage(outputpage)
                    output = regex.search(content).group(1)
                
                goutput, gerror, timeout = run(args, input, path)
                
                goutput = goutput.strip('\n')
                output = output.strip('\n')
                goutput = gerror.strip('\n') + output

                if timeout:
                    goutput = "***** TIMEOUT *****\nYOUR PROGRAM TIMED OUT!\n\n" + goutput
                
                if goutput != output:
                    info("Test %s failed" % testname)
                    wrong.append(testname)
                else:
                    info("Test %s succeeded" % testname)
                    right.append(testname)

                #put user output to wiki

                outputs.append('[[%s]]' % (user + '/' + outputpage,))
                try:
                    wiki.putPage(user + '/' + outputpage, outputtemplate % (re.sub(ur'[\x00-\x08\x0b-\x19]', '?', goutput), testname))
                except opencollab.wiki.WikiFault, error_message:
                    # It's ok if the comment does not change
                    if 'There was an error in the wiki side (You did not change the page content, not saved!)' in error_message:
                        pass
                    else:
                        raise

            info('Removing ' + path)
            shutil.rmtree(path)

            metas = dict()
            
            #clear old info
            info('Clearing old metas')
            wiki.setMeta(page, {'wrong': [], 'right': []}, True)
        
            if len(wrong) == 0:
                metas['overallvalue'] = ['success']
            else:
                metas['overallvalue'] = ['failure']

            if outputs:
                metas['output'] = outputs

            if wrong:
                metas['wrong'] = wrong

            if right:
                metas['right'] = right

            info('Setting new metas')
            #add metas
            wiki.setMeta(page, metas, True)
            
            info('Done')
            time.sleep(5)

def main():
    #parse commandline parameters
    parser = OptionParser()
    parser.add_option("-u", "--url-to-wiki", dest="url",
                      help="connect to URL", metavar="URL", default = None)
    parser.add_option("-f", "--config-file", dest="file",
                      help="read credentials from FILE", metavar="FILE")

    (options, args) = parser.parse_args()
    
    if args:
        sys.stderr.write('Invalid arguments! Use -h for help\n')
        sys.exit(1)

    if not options.url:
        sys.stderr.write('You must specify a wiki to connect!\n')
        sys.exit(1)
    url = options.url

    if not options.file:
        try:
            wiki = opencollab.wiki.CLIWiki(options.url)
        except socket.error, e:
            sys.stderr.write(e + '\n')
            sys.exit(1)

    else:
        config = ConfigParser.RawConfigParser()
        config.read(options.file)
        uname = config.get('creds', 'username')
        passwd = config.get('creds', 'password')
        while True:
            try:
                wiki = opencollab.wiki.CLIWiki(options.url, uname, passwd)
            except socket.error, e:
                error(e)
                time.sleep(10)
            else:
                break
                
    if not wiki.token:
        sys.stderr.write('Auhtentication failure\n')
        sys.exit(1)

    while True:
        try:
            checking_loop(wiki)
        except opencollab.wiki.WikiFailure:
            error('WIKI PROBLEMS')
            traceback.print_exc()
        except socket.error:
            error('CONNECTION PROBLEMS')
            traceback.print_exc()
        time.sleep(10)
        

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'Bye!'
    
