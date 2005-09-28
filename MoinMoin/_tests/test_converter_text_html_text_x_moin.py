# -*- coding: utf-8 -*-
from cStringIO import StringIO
import unittest
import xml.dom.DOMImplementation, xml.dom.ext

import MoinMoin.converter.text_html_text_x_moin as converter
import MoinMoin.parser.wiki, MoinMoin.formatter.text_gedit, MoinMoin.request
convert = converter.convert
error = converter.ConvertError


class BaseTestCase(unittest.TestCase):
    def do_convert_real(self, func_args, successfull = True):
        try:
            ret = convert(*func_args)
        except error, e:
            if successfull:
                self.fail("fails with parse error: %s" % e)
            else:
                return
        if successfull:
            return ret
        else:
            self.fail("don't fail with parse error")

class MinimalConfig(object):
    def __init__(self):
        self.bang_meta = True
        self.siteid = 'test'

class MinimalPage(object):
    def __init__(self):
        self.hilite_re = None
        self.page_name = "testpage"

class MinimalRequest(object):
    def __init__(self):
        self.cfg = MinimalConfig()
        self.clock = MoinMoin.request.Clock()
        self.content_lang = None
        self.current_lang = None
        self.form = {}
        self._page_headings = {}
        self.result = []

    def getText(self, text):
        return text

    def write(self, text):
        self.result.append(text)

class ConvertBlockRepeatableTestCase(BaseTestCase):
    def do(self, text, output):
        text = text.lstrip('\n')
        output = output.strip('\n')
        request = MinimalRequest()
        formatter = MoinMoin.formatter.text_gedit.Formatter(request)
        formatter.setPage(MinimalPage())
        MoinMoin.parser.wiki.Parser(text, request).format(formatter)
        repeat = ''.join(request.result).strip('\n')
        self.failUnlessEqual(repeat, output)
        out = self.do_convert_real([request, repeat])
        self.failUnlessEqual(text, out)

    def testComment01(self):
        test = ur"""
#test
"""
        output = ur"""<!--#test-->"""
        self.do(test, output)

    def testComment02(self):
        test = ur"""
##test
"""
        output = ur"""<!--##test-->"""
        self.do(test, output)

    def testComment03(self):
        test = ur"""
##test
##test
"""
        output = ur"""
<!--##test-->
<!--##test-->
"""
        self.do(test, output)

    def testHeading01(self):
        test = ur"""
= test1 =

"""
        output = ur"""
<h2>test1</h2>
"""
        self.do(test, output)

    def testHeading02(self):
        test = ur"""
= test1 =

== test2 ==

"""
        output = ur"""
<h2>test1</h2>
<h3>test2</h3>
"""
        self.do(test, output)

    def testListSuccess01(self):
        test = ur"""
 * test

"""
        output = ur"""
<ul>
<li><p>test </p>
</li>
</ul>
"""
        self.do(test, output)

    def testListSuccess02(self):
        test = ur"""
 1. test

"""
        output = ur"""
<ol type="1">
<li><p>test </p>
</li>
</ol>
"""
        self.do(test, output)

    def testListSuccess03(self):
        test = ur"""
 test:: test

"""
        output = ur"""
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
"""
        self.do(test, output)

    def testListSuccess04(self):
        test = ur"""
 * test
 * test

"""
        output = ur"""
<ul>
<li><p>test </p>
</li>
<li><p>test </p>
</li>
</ul>
"""
        self.do(test, output)

    def testListSuccess05(self):
        test = ur"""
 1. test
 1. test

"""
        output = ur"""
<ol type="1">
<li><p>test </p>
</li>
<li><p>test </p>
</li>
</ol>
"""
        self.do(test, output)

    def testListSuccess06(self):
        test = ur"""
 test:: test
 test:: test

"""
        output = ur"""
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
"""
        self.do(test, output)

    def testListSuccess07(self):
        test = ur"""
 * test
  
 * test

"""
        output = ur"""
<ul>
<li><p>test </p>
</li>
</ul>
<ul>
<li><p>test </p>
</li>
</ul>
"""
        self.do(test, output)

    def testListSuccess08(self):
        test = ur"""
 1. test
  
 1. test

"""
        output = ur"""
<ol type="1">
<li><p>test </p>
</li>
</ol>
<ol type="1">
<li><p>test </p>
</li>
</ol>
"""
        self.do(test, output)

    def testListSuccess09(self):
        test = ur"""
 test:: test
  
 test:: test

"""
        output = ur"""
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
"""
        self.do(test, output)

    def testListSuccess10(self):
        test = ur"""
 * test
  * test

"""
        output = ur"""
<ul>
<li><p>test </p>
<ul>
<li><p>test </p>
</li>
</ul>
</li>
</ul>
"""
        self.do(test, output)

    def testListSuccess11(self):
        test = ur"""
 1. test
  1. test

"""
        output = ur"""
<ol type="1">
<li><p>test </p>
<ol type="1">
<li><p>test </p>
</li>
</ol>
</li>
</ol>
"""
        self.do(test, output)

    def testListSuccess12(self):
        test = ur"""
 test:: test
  test:: test

"""
        output = ur"""
<dl>
<dt>test</dt>
<dd><p>test </p>
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
</dd>
</dl>
"""
        self.do(test, output)

    def testListSuccess13(self):
        test = ur"""
 * test
  * test
 * test

"""
        output = ur"""
<ul>
<li><p>test </p>
<ul>
<li><p>test </p>
</li>
</ul>
</li>
<li><p>test </p>
</li>
</ul>
"""
        self.do(test, output)

    def testListSuccess14(self):
        test = ur"""
 1. test
  1. test
 1. test

"""
        output = ur"""
<ol type="1">
<li><p>test </p>
<ol type="1">
<li><p>test </p>
</li>
</ol>
</li>
<li><p>test </p>
</li>
</ol>
"""
        self.do(test, output)

    def testListSuccess15(self):
        test = ur"""
 test:: test
  test:: test
 test:: test

"""
        output = ur"""
<dl>
<dt>test</dt>
<dd><p>test </p>
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
</dd>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
"""
        self.do(test, output)

    def testListSuccess16(self):
        test = ur"""
 * test

 1. test

"""
        output = ur"""
<ul>
<li><p>test </p>
</li>
</ul>
<ol type="1">
<li><p>test </p>
</li>
</ol>
"""
        self.do(test, output)

    def testListSuccess17(self):
        test = ur"""
 * test

 test:: test

"""
        output = ur"""
<ul>
<li><p>test </p>
</li>
</ul>
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
"""
        self.do(test, output)

    def testListSuccess18(self):
        test = ur"""
 1. test

 * test

"""
        output = ur"""
<ol type="1">
<li><p>test </p>
</li>
</ol>
<ul>
<li><p>test </p>
</li>
</ul>
"""
        self.do(test, output)

    def testListSuccess19(self):
        test = ur"""
 1. test

 test:: test

"""
        output = ur"""
<ol type="1">
<li><p>test </p>
</li>
</ol>
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
"""
        self.do(test, output)

    def testListSuccess20(self):
        test = ur"""
 test:: test

 * test

"""
        output = ur"""
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
<ul>
<li><p>test </p>
</li>
</ul>
"""
        self.do(test, output)

    def testListSuccess21(self):
        test = ur"""
 test:: test

 1. test

"""
        output = ur"""
<dl>
<dt>test</dt>
<dd><p>test </p>
</dd>
</dl>
<ol type="1">
<li><p>test </p>
</li>
</ol>
"""
        self.do(test, output)

    def testListSuccess23(self):
        test = ur"""
 1. test
  * test

"""
        output = ur"""
<ol type="1">
<li><p>test </p>
<ul>
<li><p>test </p>
</li>
</ul>
</li>
</ol>
"""
        self.do(test, output)

    def testListSuccess26(self):
        test = ur"""
 * test

test

"""
        output = ur"""
<ul>
<li><p>test </p>
</li>
</ul>
<p>test </p>
"""
        self.do(test, output)

    def testListSuccess28(self):
        test = ur"""
 * test

 test

"""
        output = ur"""
<ul>
<li><p>test </p>
<p>test </p>
</li>
</ul>
"""
        self.do(test, output)

    def testListSuccess29(self):
        test = ur"""
 * test
  * test
 test
"""
        output = ur"""
"""
        self.do(test, output)

    def testListSuccess30(self):
        test = ur"""
 * test
  * test
  test
"""
        output = ur"""
"""
        self.do(test, output)

    def testParagraph1(self):
        test = ur"""
test

"""
        output = ur"""
<p>test </p>
"""
        self.do(test, output)

    def testParagraph2(self):
        test = ur"""
test

test

"""
        output = ur"""
<p>test </p>
<p>test </p>
"""
        self.do(test, output)

    def testPreSuccess1(self):
        test = ur"""
{{{
test
}}}

"""
        output = ur"""
<pre>
test
</pre>
"""
        self.do(test, output)

    def testPreSuccess2(self):
        test = ur"""
{{{
test
test
}}}

"""
        output = ur"""
<pre>
test
test
</pre>
"""
        self.do(test, output)

    def testPreSuccess3(self):
        test = ur"""
{{{
test

test
}}}

"""
        output = ur"""
<pre>
test

test
</pre>
"""
        self.do(test, output)

    def testPreSuccess4(self):
        test = ur"""
{{{
 * test
}}}

"""
        output = ur"""
<pre>
 * test
</pre>
"""
        self.do(test, output)

    def testPreSuccess5(self):
        test = ur"""
{{{
  }}}

"""
        output = ur"""
<pre>
  </pre>
"""
        self.do(test, output)

    def testPreSuccess6(self):
        test = ur"""
 * {{{
test
}}}

"""
        output = ur"""
<ul>
<li>
<pre>
test
</pre>
</li>
</ul>
"""
        self.do(test, output)

    def testPreSuccess7(self):
        test = ur"""
 * {{{
   test
   }}}

"""
        output = ur"""
<ul>
<li>
<pre>
   test
   </pre>
</li>
</ul>
"""
        self.do(test, output)

    def testPreSuccess8(self):
        test = ur"""
 * test
 {{{
test
}}}

"""
        output = ur"""
<ul>
<li><p>test 
</p>
<pre>
test
</pre>
</li>
</ul>
"""
        self.do(test, output)

    def testPreSuccess9(self):
        test = ur"""
 * test

{{{
test
}}}

"""
        output = ur"""
<ul>
<li><p>test </p>
</li>
</ul>

<pre>
test
</pre>
"""
        self.do(test, output)

    def testRule1(self):
        test = ur"""
----

"""
        output = ur"""
<hr/>
"""
        self.do(test, output)

    def testTable01(self):
        test = ur"""
|| ||

"""
        output = ur"""
<div>
<table>
<tr>
<td>
<p> </p>
</td>
</tr>
</table>
</div>
"""
        self.do(test, output)

    def testTable02(self):
        test = ur"""
||test||

"""
        output = ur"""
<div>
<table>
<tr>
<td>
<p>test</p>
</td>
</tr>
</table>
</div>
"""
        self.do(test, output)

    def testTable03(self):
        test = ur"""
||test||test||

"""
        output = ur"""
<div>
<table>
<tr>
<td>
<p>test</p>
</td>
<td>
<p>test</p>
</td>
</tr>
</table>
</div>
"""
        self.do(test, output)

    def testTable04(self):
        test = ur"""
||test||
||test||test||

"""
        output = ur"""
<div>
<table>
<tr>
<td>
<p>test</p>
</td>
</tr>
<tr>
<td>
<p>test</p>
</td>
<td>
<p>test</p>
</td>
</tr>
</table>
</div>
"""
        self.do(test, output)

    def testTable05(self):
        test = ur"""
||||test||
||test||test||

"""
        output = ur"""
<div>
<table>
<tr>
<td colspan="2" style="text-align: center;">
<p>test</p>
</td>
</tr>
<tr>
<td>
<p>test</p>
</td>
<td>
<p>test</p>
</td>
</tr>
</table>
</div>
"""
        self.do(test, output)

    def testTable06(self):
        test = ur"""
||||test||test||
||test||||test||

"""
        output = ur"""
<div>
<table>
<tr>
<td colspan="2" style="text-align: center;">
<p>test</p>
</td>
<td>
<p>test</p>
</td>
</tr>
<tr>
<td>
<p>test</p>
</td>
<td colspan="2" style="text-align: center;">
<p>test</p>
</td>
</tr>
</table>
</div>
"""
        self.do(test, output)

class ConvertInlineFormatRepeatableTestCase(BaseTestCase):
    def do(self, text, output):
        text = text.lstrip('\n')
        output = output.strip('\n')
        output = "<p>%s </p>" % output
        request = MinimalRequest()
        formatter = MoinMoin.formatter.text_gedit.Formatter(request)
        formatter.setPage(MinimalPage())
        MoinMoin.parser.wiki.Parser(text, request).format(formatter)
        repeat = ''.join(request.result).strip('\n')
        self.failUnlessEqual(repeat, output)
        out = self.do_convert_real([request, repeat])
        out = out.rstrip('\n')
        self.failUnlessEqual(text, out)

    def testEmphasis01(self):
        test = ur"''test''"
        output = ur"<em>test</em>"
        self.do(test, output)

    def testEmphasis02(self):
        test = ur"'''test'''"
        output = ur"<strong>test</strong>"
        self.do(test, output)

    def testEmphasis03(self):
        test = ur"'''''test'''''"
        output = ur"<em><strong>test</strong></em>"
        self.do(test, output)

    def testEmphasis04(self):
        test = ur"''test'''test'''''"
        output = ur"<em>test<strong>test</strong></em>"
        self.do(test, output)

    def testEmphasis05(self):
        test = ur"'''test''test'''''"
        output = ur"<strong>test<em>test</em></strong>"
        self.do(test, output)

    def testEmphasis06(self):
        test = ur"''test'''test'''test''"
        output = ur"<em>test<strong>test</strong>test</em>"
        self.do(test, output)

    def testEmphasis07(self):
        test = ur"'''test''test''test'''"
        output = ur"<strong>test<em>test</em>test</strong>"
        self.do(test, output)

    def testEmphasis08(self):
        test = ur"''test'''''test'''"
        output = ur"<em>test</em><strong>test</strong>"
        self.do(test, output)

    def testEmphasis09(self):
        test = ur"'''test'''''test''"
        output = ur"<strong>test</strong><em>test</em>"
        self.do(test, output)

    def testEmphasis10(self):
        test = ur"'''''test''test'''"
        output = ur"<strong><em>test</em>test</strong>"
        self.do(test, output)

    def testEmphasis11(self):
        test = ur"'''''test'''test''"
        output = ur"<em><strong>test</strong>test</em>"
        self.do(test, output)

    def testFormatBig01(self):
        test = ur"~+test+~"
        output = ur"<big>test</big>"
        self.do(test, output)

    def testFormatSmall01(self):
        test = ur"~-test-~"
        output = ur"<small>test</small>"
        self.do(test, output)

    def testFormatStrike01(self):
        test = ur"--(test)--"
        output = ur"<strike>test</strike>"
        self.do(test, output)

    def testFormatSub01(self):
        test = ur",,test,,"
        output = ur"<sub>test</sub>"
        self.do(test, output)

    def testFormatSup01(self):
        test = ur"^test^"
        output = ur"<sup>test</sup>"
        self.do(test, output)

    def testFormatUnderline01(self):
        test = ur"__test__"
        output = ur""
        self.do(test, output)

    def testPre01(self):
        test = ur"{{{test}}}"
        output = ur"<tt>test</tt>"
        self.do(test, output)

    def testWhitespace01(self):
        test = ur"''test '''test'''''"
        output = ur"<em>test <strong>test</strong></em>"
        self.do(test, output)

class ConvertInlineItemRepeatableTestCase(BaseTestCase):
    def do(self, text, output):
        text = text.lstrip('\n')
        output = output.strip('\n')
        output = "<p>%s </p>" % output
        request = MinimalRequest()
        formatter = MoinMoin.formatter.text_gedit.Formatter(request)
        formatter.setPage(MinimalPage())
        MoinMoin.parser.wiki.Parser(text, request).format(formatter)
        repeat = ''.join(request.result).strip('\n')
        self.failUnlessEqual(repeat, output)
        out = self.do_convert_real([request, repeat])
        out = out.rstrip('\n')
        self.failUnlessEqual(text, out)

    def testWikiWord01(self):
        test = ur"WikiWord"
        output = ur"""<a href="""""
        self.do(test, output)

    def testNoWikiWord01(self):
        test = ur"!WikiWord"
        output = ur"WikiWord"
        self.do(test, output)

    def testSmiley01(self):
        test = ur":-)"
        output = ur""
        self.do(test, output)

class StripTestCase(unittest.TestCase):
    def do(self, cls, text, output):
        tree = converter.parse(text)
        cls().do(tree)
        out = StringIO()
        xml.dom.ext.Print(tree, out)
        self.failUnlessEqual("<?xml version='1.0' encoding='UTF-8'?>%s" % output, out.getvalue().decode("utf-8"))

class StripBreakTestCase(StripTestCase):
    def do(self, text, output):
        super(StripBreakTestCase, self).do(converter.strip_break, text, output)

class StripWhitespaceTestCase(StripTestCase):
    def do(self, text, output):
        super(StripWhitespaceTestCase, self).do(converter.strip_whitespace, text, output)

    def test1(self):
        test = ur"""
<t/>
"""
        output = ur"""<t/>"""
        self.do(test, output)

    def test2(self):
        test = ur"""
<t>
  <z/>
</t>
"""
        output = ur"""<t><z/></t>"""
        self.do(test, output)

    def test3(self):
        test = ur"""
<t>
  <z>test</z>
</t>
"""
        output = ur"""<t><z>test</z></t>"""
        self.do(test, output)

    def test3(self):
        test = ur"""<p>&nbsp;</p>"""
        output = ur""""""
        self.do(test, output)

    def test4(self):
        test = ur"""<p>test </p>"""
        output = ur"""<p>test</p>"""
        self.do(test, output)

class ConvertBrokenBrowserTestCase(BaseTestCase):
    def do(self, text, output):
        text = text.strip('\n')
        output = output.lstrip('\n')
        request = MinimalRequest()
        out = self.do_convert_real([request, text])
        self.failUnlessEqual(output, out)

    def testList01(self):
        test = ur"""
<ul>
<li>test</li>
<ul>
<li>test</li>
</ul>
<li>test</li>
</ul>
"""
        output = ur"""
 * test
  * test
 * test

"""
        self.do(test, output)

if __name__ == '__main__':
    unittest.main()
