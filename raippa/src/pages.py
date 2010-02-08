# -*- coding: utf-8 -*-

import time, re
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.action.AttachFile import add_attachment
from MoinMoin.user import User as MoinUser
from graphingwiki.editing import get_revisions, get_metas, get_keys, set_metas 
from raippa import removelink, addlink, running_pagename, pages_in_category
from raippa import rename_page, delete_page, delete_attachment, attachment_list
from raippa import raippacategories as rc
from raippa.flow import Flow

class RaippaException(Exception):
    def __init__(self, value):
        self.value = value
        self.args = value
    def __str__(self):
        return repr(self.value)

class DeadLinkException(RaippaException):
    pass

class TooManyKeysException(RaippaException):
    pass

class TooManyLinksException(RaippaException):
    pass

class TooManyValuesException(RaippaException):
    pass

class MissingMetaException(RaippaException):
    pass

class PageDoesNotExistException(RaippaException):
    pass

class SaveException(RaippaException):
    pass

class Answer:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename

    def question(self):
        pagedata = self.request.graphdata.getpage(self.pagename)
        pages = pagedata.get('in', dict()).get('answer', list())

        questions = list()

        for page in pages:
            keys = ["gwikicategory", "question"]
            qmetas = get_metas(self.request, page, keys, checkAccess=False)
            
            if rc['questionoptions'] in qmetas.get('gwikicategory', list()):
                for questionpage in qmetas.get("question", list()):
                    questions.append(removelink(questionpage))

        if len(questions) == 1:
            return Question(self.request, questions[0])
        elif len(questions) > 1:
            raise TooManyValuesException(u'Too many pages linking in to %s.' % self.pagename)
        else:
            return None

    def answer(self):
        answertype = self.question().options().get('answertype', 'text')

        if answertype != 'file':
            metas = get_metas(self.request, self.pagename, ['answer'], checkAccess=False)
            answers = metas.get('answer', list())

            answer = None

            if len(answers) == 1:
                answer = answers[0]
            elif len(answers) > 1:
                raise TooManyValuesException(u'Page %s has too many "answer" -metas.' % self.pagename)
            else:
                raise MissingMetaException(u'''Page %s doesn't have "answer" -meta.''' % self.pagename)
        else:
            keys = ['testname', 'parameters', 'input', 'output']
            metas = get_metas(self.request, self.pagename, keys, checkAccess=False)

            answer = ["", "", "", "", list(), list()]

            for key in keys:
                values = metas.get(key, list())
                value = ""

                if len(values) == 1:
                    value = removelink(values[0])
                elif len(values) > 1:
                    raise TooManyValuesException(u'Page %s has too many "%s" -metas.' % (key, self.pagename))

                if key == "testname":
                    if not value:
                        raise MissingMetaException(u'''Page %s doesn't have "testname" -meta.''' % self.pagename)
                    answer[0] = value

                elif key == "parameters":
                    answer[1] = value

                elif key == "input":
                    if value and Page(self.request, value).exists():
                        raw_input = Page(self.request, value).get_raw_body()
                        regexp = re.compile('{{{\s?(.*?)\s?}}}', re.DOTALL)
                        match = regexp.search(raw_input)

                        if match:
                            answer[2] = match.groups()[0]

                        answer[4] = attachment_list(self.request, value)

                elif key == "output":
                    if value and Page(self.request, value).exists():
                        raw_output = Page(self.request, value).get_raw_body()
                        regexp = re.compile('{{{\s?(.*?)\s?}}}', re.DOTALL)
                        match = regexp.search(raw_output)

                        if match:
                            answer[3] = match.groups()[0]

                        answer[5] = attachment_list(self.request, value)

        return answer

    def options(self):
        metas = get_metas(self.request, self.pagename, ['option'], checkAccess=False)
        return metas.get('option', list())

    def value(self):
        metas = get_metas(self.request, self.pagename, ['value'], display=True, checkAccess=False)
        values = metas.get('value', list())

        value = None

        if len(values) == 1:
            value = values[0]
        elif len(values) > 1:
            raise TooManyValuesException(u'Page %s has too many "value" -metas.' % self.pagename)
        else:
            raise MissingMetaException(u'''Page %s doesn't have "value" -meta.''' % self.pagename)

        return value

    def tips(self):
        metas = get_metas(self.request, self.pagename, ['tip'], checkAccess=False)
        tips = metas.get('tip', list())

        return tips

    def comment(self):
        metas = get_metas(self.request, self.pagename, ['comment'], checkAccess=False)
        comments = metas.get('comment', list())
        if len(comments) == 1:
            return comments[0]
        elif len(comments) > 1:
            raise TooManyValuesException(u'Page %s has too many "comment" -metas.' % self.pagename)
        else:
            return None


class Question:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename
        self.optionspage = u'%s/options' % pagename

    def title(self):
        raw_content = Page(self.request, self.pagename).get_raw_body()
        title = unicode()

        for line in raw_content.split("\n"):
            if line.startswith("== ") and line.endswith(" =="):
                title = line[3:-3]

        return title

    def answers(self):
        answers = list()

        if not Page(self.request, self.optionspage).exists():
            return answers

        metas = get_metas(self.request, self.optionspage, ['answer'], checkAccess=False)
        answerpages = metas.get('answer', list())

        for answerpage in answerpages:
            answerpage = removelink(answerpage)
            if not Page(self.request, answerpage).exists():
                raise DeadLinkException(u"Page %s linked in %s doesn't exist." % (answerpage, self.optionspage))

            answers.append(answerpage)
        
        answers.sort() 
        return answers

    def check_answers(self, user_answers, user, usedtime=None, save_history=False):
        success_dict = {"right":list(), "wrong":list()}
        save_dict = dict() 
        overallvalue = str()

        questiontype = self.options().get('answertype', None)
        if not questiontype:
            raise MissingMetaException(u"Question %s doesn't have answertype option." % self.pagename)

        if questiontype in ['checkbox', 'radio', 'text']:
            answerpages = self.answers()
            save_dict = {"right":list(), "wrong":list()}
            overallvalue = "success"

            for answerpage in answerpages:
                answer = Answer(self.request, answerpage)

                answer_options = answer.options()
                if questiontype == 'text' and 'regexp' in answer_options:
                    regexp = re.compile(answer.answer(), re.DOTALL)

                    if answer.value() == "right":        
                        done = list()
                        for user_answer in user_answers:
                            re_output = regexp.match(user_answer)
                            if re_output:
                                success_dict["right"].append(answerpage)
                                save_dict["right"].append(user_answer)
                                done.append(user_answer)

                        if not done:
                            success_dict["wrong"].append(answerpage)
                        else:
                            for done_answer in done:
                                user_answers.remove(done_answer)

                    else:                                
                        for user_answer in user_answers:
                            re_output = regexp.match(user_answer)
                            if re_output:
                                success_dict["wrong"].append(answerpage)
                                save_dict["wrong"].append(user_answer)
                                overallvalue = "failure"
                            else:
                                success_dict["right"].append(answerpage)
                else:
                    if answer.value() == "right":
                        if answer.answer() not in user_answers:
                            success_dict["wrong"].append(answerpage)
                            if questiontype == 'checkbox':
                                overallvalue = "failure"
                        else:
                            user_answers.remove(answer.answer())
                            success_dict["right"].append(answerpage)
                            save_dict["right"].append(answer.answer())
                    else:
                        if answer.answer() in user_answers:
                            success_dict["wrong"].append(answerpage)
                            save_dict["wrong"].append(answer.answer())
                            overallvalue = "failure"
                        else:
                            success_dict["right"].append(answerpage)

            if len(answerpages) > 0 and len(user_answers) > 0:
                overallvalue = "failure"
                for user_answer in user_answers:
                    save_dict["wrong"].append(user_answer)

        elif questiontype == 'file':
            for filename, content in user_answers:
                overallvalue = "pending"
                save_dict[filename] = content
        else:
            raise ValueError, "Incorrect answertype." 

        if save_history:
            success, msg = user.save_answers(self, overallvalue, save_dict, usedtime)
            if not success:
                raise SaveException, msg

        return overallvalue, success_dict 

    def save(self, answer_data, options):
        old_answers = self.answers()
        answertype = options.get("answertype", [u""])[0]

        remove = {self.optionspage: get_keys(self.request, self.optionspage)}

        add = {self.optionspage: {"answer": list(),
                                  "question": [addlink(self.pagename)],
                                  "gwikicategory": [rc['questionoptions']]}}
        for key in options:
            add[self.optionspage][key] = options[key]

        for index, key in enumerate(sorted(answer_data.keys())):
            pagename = "%s/%s/%.3i" % (self.pagename, "answer", index)

            add[self.optionspage]["answer"].append(addlink(pagename))

            if pagename in old_answers:
                old_answers.remove(pagename)
                remove[pagename] = get_keys(self.request, pagename)

            if answertype != 'file':
                answer = answer_data[key]

                if not answer.get("answer", list()):
                    raise ValueError, "Missing answer."

                if not answer.get("value", list()):
                    raise ValueError, "Missing value."

                add[pagename] = {"question": [addlink(self.pagename)],
                                 "gwikicategory": [rc['answer']]}

                for key in answer:
                    add[pagename][key] = answer[key]

            else:
                answer = answer_data[key]

                if not answer[0]:
                    raise ValueError, "Missing test name."

                add[pagename] = {"question": [addlink(self.pagename)],
                                 "testname": [answer[0]],
                                 "parameters": [answer[1]],
                                 "gwikicategory": [rc['answer']]}

                if answer[2] or answer[4]:
                    inputpage = pagename+"/input"
                    add[pagename]["input"] = [addlink(inputpage)]

                    filelinks = unicode()
                    for filename in answer[4].keys():
                        content = answer[4][filename]
                        if content != None:
                            f, s = add_attachment(self.request, inputpage, filename, content, 1)
                        filelinks += " file:: [[attachment:%s]]\n" % filename

                    for filename in attachment_list(self.request, inputpage):
                        if filename not in answer[4].keys():
                            delete_attachment(self.request, inputpage, filename)

                    pagecontent = u'''
{{{
%s
}}}
----
 answer:: %s
%s
----
%s''' % (answer[2], addlink(pagename), filelinks, rc['testinput'])

                    page = PageEditor(self.request, inputpage)
                    msg = page.saveText(pagecontent, page.get_real_rev())

                else:
                    if Page(self.request, pagename+"/input").exists():
                        rsuccess, rmsg = delete_page(self.request, pagename+"/input")
        
                        if not rsuccess:
                            return rsuccess, rmsg

                if answer[3] or answer[5]:
                    outputpage = pagename+"/output"
                    add[pagename]["output"] = [addlink(outputpage)]

                    filelinks = unicode()
                    for filename in answer[5]:
                        content = answer[5][filename]
                        if content != None:
                            f, s = add_attachment(self.request, outputpage, filename, content, 1)
                        filelinks += " file:: [[attachment:%s]]" % filename

                    for filename in attachment_list(self.request, outputpage):
                        if filename not in answer[5].keys():
                            delete_attachment(self.request, outputpage, filename)

                    pagecontent = u'''
{{{
%s
}}}
----
 answer:: %s
%s
----
%s''' % (answer[3], addlink(pagename), filelinks, rc['testoutput'])

                    page = PageEditor(self.request, outputpage)
                    msg = page.saveText(pagecontent, page.get_real_rev())

                else:
                    if Page(self.request, pagename+"/output").exists():
                        rsuccess, rmsg = delete_page(self.request, pagename+"/output")

                        if not rsuccess:
                            return rsuccess, rmsg

        success, msg = set_metas(self.request, remove, dict(), add)

        if success:
            for old_answer in old_answers:
                rm_success, rm_msg = PageEditor(self.request, old_answer).deletePage()
                if not rm_success:
                    return False, rm_msg

        return success, msg

    def rename(self, newname, comment=""):
        title = self.title()

        #rename question in the flow
        task = self.task()
        if task and Page(self.request, task.flowpage).exists():
            keys = get_keys(self.request, task.flowpage)
                    
            if self.pagename in keys:
                metas = get_metas(self.request, task.flowpage, keys, checkAccess=False)
                remove = {task.flowpage: [self.pagename]}
                add = {task.flowpage: {newname: metas[self.pagename]}}
                
                success, msg = set_metas(self.request, remove, dict(), add)
                
                if not success:
                    return success, msg

        #rename histories
        for historypage in self.histories():
            newhistoryname = historypage.replace(self.pagename, newname, 1)

            success, msg = rename_page(self.request, historypage, newhistoryname, comment)
            if not success:
                return success, msg

        #rename page
        success, msg = rename_page(self.request, self.pagename, newname)
        return success, u'Question "%s" was successfully renamed!' % title

    def delete(self, comment=u""):
        title = self.title()

        #remove question from the flow
        task = self.task()
        if task and Page(self.request, task.flowpage).exists():
            previous = list()
            next = list()

            keys = get_keys(self.request, task.flowpage)
            metas = get_metas(self.request, task.flowpage, keys, checkAccess=False)
            new_metas = dict()

            for key in metas:
                values = list()
                for value in metas[key]:
                    value = removelink(value)
                    
                    if value == self.pagename:
                        previous.append(key)
                    else:
                        values.append(value)

                if self.pagename == key:
                    next.extend(values)
                else:
                    new_metas[key] = list()
                    for value in values:
                        new_metas[key].append(addlink(value))

            for previous_question in previous:
                if previous_question not in new_metas:
                    new_metas[previous_question] = list()

                for next_question in next:
                     if next_question not in new_metas[previous_question]:
                         new_metas[previous_question].append(addlink(next_question)) 
   
            remove = {task.flowpage: metas}
            add = {task.flowpage: new_metas}
            success, msg = set_metas(self.request, remove, dict(), add)

            if not success:
                return success, msg

        #remove historypages
        for historypage in self.histories():
            success, msg = delete_page(self.request, historypage, comment)

            if not success:
                return success, msg

        #remove questionpage
        success, msg = delete_page(self.request, self.pagename, comment)
        if not success:
            return success, msg

        return True, u'Question "%s" was successfully deleted!' % title

    def options(self):
        options = dict()

        if not Page(self.request, self.optionspage).exists():
            return options

        optionkeys = ['answertype', 'redo', 'option']
        metas = get_metas(self.request, self.optionspage, optionkeys, checkAccess=False)

        answertypes = metas.get('answertype', list())
        if len(answertypes) == 1:
            options['answertype'] = answertypes[0]
        elif len(answertypes) > 1:
            raise TooManyValuesException(u'Question %s has too many answertypes.' % self.pagename)
        elif len(answertypes) < 1:
            raise MissingMetaException(u"Question %s is missing a answertype." % self.pagename) 

        redos = metas.get('redo', list())
        if len(redos) == 1:
            if redos[0] == "True":
                options['redo'] = True
            else:
                options['redo'] = False
        elif len(redos) > 1:
            raise TooManyValuesException(u'Question %s has too many redos.' % self.pagename)
            
        for key in metas.get('option', list()):
            options[key] = True

        return options

    def histories(self):
        histories = list()

        page = self.request.graphdata.getpage(self.pagename)
        pagelist = page.get('in', dict()).get("question", list())

        for historypage in pagelist:
            metas = get_metas(self.request, historypage, ["gwikicategory"], checkAccess=False)

            categories = metas.get("gwikicategory", list())

            if rc['history'] in categories:
                histories.append(historypage)

        return histories

    def students(self, user=None):
        done, doing, totals = self.stats(user)
        for student in done:
            done[student] = done[student][0]
        for student in doing:
            doing[student] = doing[student][0]

        return done, doing

    def stats(self, user=None, totals=True):
        done = dict()
        doing = dict()

        if user:
            histories = user.histories(self.pagename)
        else:
            histories = self.histories()

        task = self.task()
        if task:
            tasktype = task.options().get('type', 'basic')
        else:
            tasktype = 'basic'

        if totals:
            total_used = int()
            total_revs = int()
            revisions = Question(self.request, self.pagename).history_revisions(histories)
                    
            for historypage in revisions:
                if not revisions.get(historypage, dict()):
                    continue

                user_used = int()
                for rev_number in revisions[historypage]:
                    user_used += revisions[historypage][rev_number][5]

                total_used += user_used
                user_revs = len(revisions[historypage].keys())
                total_revs += user_revs

                for student in revisions[historypage][rev_number][0]:
                    if tasktype in ['questionary', 'exam']:
                        done[student] = (user_revs, user_used)
                    else:
                        if revisions[historypage][rev_number][1] == "success":
                            done[student] = (user_revs, user_used)
                        else:
                            doing[student] = (user_revs, user_used)

            return done, doing, (total_revs, total_used)
        else:
            for historypage in histories:
                keys = ['user', 'overallvalue']
                metas = get_metas(self.request, historypage, keys, checkAccess=False)
                for student in metas.get('user', list()):
                    student = removelink(student)
                    umeta = get_metas(self.request, student, ["gwikicategory"], checkAccess=False)
                    if rc['student'] not in umeta.get('gwikicategory', list()):
                        continue

                    if tasktype in ['questionary', 'exam']:
                        done[student] = tuple()
                    else:
                        if "success" in metas.get('overallvalue', list()):
                            done[student] = tuple()
                        else:
                            doing[student] = tuple()

            return done, doing, tuple()

    def history_revisions(self, histories=None):
        if not histories:
            histories = self.histories()

        revisions = dict()
        #TODO only users revisions. not bot,teacher,etc.
        #check rev 1627

        for historypage in histories:
            revisions[historypage] = dict()
            pages, keys = get_revisions(self.request, Page(self.request, historypage))

            keys = ['user',
                    'overallvalue', 'right', 'wrong',
                    'time', 'usedtime',
                    'gwikicategory', 'gwikirevision', 'file']

            for page in pages:
                metas = get_metas(self.request, page, keys, checkAccess=False)

                revision = int(metas.get('gwikirevision', list())[0])

                users = list()
                for user in metas.get('user', list()):
                    user = removelink(user)
                    umetas = get_metas(self.request, user, 'gwikicategory', checkAccess=False)
                    if rc['student'] in umetas.get('gwikicategory', list()):
                        users.append(user)

                right = metas.get('right', list())
                wrong = metas.get('wrong', list())
                files_raw = metas.get('file', list())
                files = list()
                if files_raw and files_raw[0]:
                    for file in files_raw:
                        files.append(removelink(file).replace("attachment:", ""))

                overall = metas.get('overallvalue', list())
                if len(overall) < 1 or len(overall) > 1:
                    continue
                else:
                    overall = overall[0]

                answer_time = metas.get('time', list())
                if len(answer_time) < 1 or len(answer_time) > 1:
                    continue
                else:
                    try:
                        time.strptime(answer_time[0], "%Y-%m-%d %H:%M:%S")
                        answer_time = answer_time[0]
                    except:
                        continue
            
                used = metas.get('usedtime', list())
                if len(used) < 1 or len(used) > 1:
                    continue
                else:
                    try:
                        used = int(float(used[0]))
                    except:
                        continue
            
                revisions[historypage][revision] = [users, overall, right, wrong, answer_time, used, files]

        return revisions

    def used_time(self, user=None):
        if user:
            histories = user.histories(self.pagename)
        else:
            histories = self.histories()

        revisions = Question(self.request, self.pagename).history_revisions(histories)
        total_time = int()
        total_revs = int()
        
        for historypage in revisions:
            if not revisions.get(historypage, dict()):
                continue

            user_total = int()
            for rev_number in revisions[historypage].keys():
                user_total += revisions[historypage][rev_number][5]

            total_time += user_total
            total_revs += len(revisions[historypage].keys())

        return total_time, total_revs

    def task(self):
        pagedict = self.request.graphdata.getpage(self.pagename).get('in', dict())

        tasks = list()

        for key, pages in pagedict.iteritems():
            if key not in ['_notype', 'question']:
                for page in pages:
                    keys = ["gwikicategory", "task"]
                    metas = get_metas(self.request, page, keys, checkAccess=False)
                    if rc['taskflow'] in metas.get('gwikicategory', list()):
                        for taskpage in metas.get('task', list()):
                            tasks.append(removelink(page[:-5]))

        if len(tasks) == 1:
            return Task(self.request, tasks[0])
        elif len(tasks) > 1:
            raise TooManyLinksException(u"Question %s linked in: %s" % (self.pagename, ", ".join(tasks)))

        return None


class Task:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename
        self.optionspage = u'%s/options' % pagename
        self.flowpage = u'%s/flow' % pagename
        if Page(request, self.flowpage).exists():
            self.flow = Flow(request, self.flowpage)
        else:
            self.flow = None

    def deadline(self):
        metas = get_metas(self.request, self.optionspage, ['deadline'], checkAccess=False)
        overall = None
        deadlines = dict()
        for value in metas.get('deadline', list()):
            try:
                kek = time.strptime(value, "%Y-%m-%d")
                if not overall:
                    overall = value 
                else:
                    raise TooManyKeysException, "Task %s has too many overal deadlines." % self.pagename
            except ValueError:
                value = removelink(value)
                if Page(self.request, value).exists():
                    keys = get_keys(self.request, value)
                    dmetas = get_metas(self.request, value, keys, checkAccess=False)
                    for key in dmetas:
                        umeta = get_metas(self.request, key, ["gwikicategory"], checkAccess=False)
                        if rc['student'] in umeta.get('gwikicategory', list()):
                            users_deadlines = list()
                            for deadline in dmetas.get(key, list()):
                                try:
                                    time.strptime(deadline, "%Y-%m-%d")
                                    users_deadlines.append(deadline)
                                except:
                                    pass

                            if len(users_deadlines) > 1:
                                raise TooManyKeysException, "Page %s has too many deadlines for user %s." % (value, key)
                            elif len(users_deadlines) == 1:
                                deadlines[key] = users_deadlines[0]

        return overall, deadlines

    def options(self):
        options = dict()

        if not Page(self.request, self.optionspage).exists():
            return options

        optionkeys = ['type', 'prerequisite', 'option']
        metas = get_metas(self.request, self.optionspage, optionkeys, checkAccess=False)

        prerequisites = metas.get('prerequisite', list())
        if len(prerequisites) > 0:
            options['prerequisite'] = list()
            for prerequisite in prerequisites:
                options['prerequisite'].append(removelink(prerequisite))

        types = metas.get('types', list())
        if len(types) == 1:
            options['type'] = types[0] 
        elif len(types) > 1:
            raise TooManyValuesException(u'Task %s has too many types.' % self.pagename) 
        else:
            options['type'] = u'basic'

        for option in metas.get('option', list()):
            options[option] = True

        return options

    def questionlist(self):
        if not self.flow:
            return list()

        questionlist = list()
        next = 'first'

        while next != None:
            nextlist = self.flow.next_from_point(next)
            if len(nextlist) > 1:
                raise TooManyKeysException(u"Flow %s has too many metas with key %s." % (self.flowpage, next))
            elif len(nextlist) < 1:
                next = None
            else:
                next = nextlist[0]

                if next and next in questionlist:
                    raise TooManyValuesException("Flow %s has key %s linked in multiple times." % self.flowpage)       
                elif not Page(self.request, next).exists():
                    raise DeadLinkException(u"Page %s linked in %s doesn't exist." % (next, self.flowpage))

                questionlist.append(next)

        return questionlist

    def students(self, user=None):
        done, doing, totals = self.stats(user)
        return done, doing

    def stats(self, user=None, totals=True):
        questions = self.questionlist()

        if not questions:
            return dict(), dict(), tuple()

        done = dict()
        doing = dict()

        if totals:
            total_used = int()
            total_revs = int()

            for question in questions:
                done[question] = dict()
                doing[question] = dict()
                stats = Question(self.request, question).stats(user, True)
                done_question, doing_question, question_totals = stats 

                if question_totals:
                    user_revs = question_totals[0]
                    user_used = question_totals[1]
                    total_revs += question_totals[0]
                    total_used += question_totals[1]
                else:
                    user_revs = int()
                    user_used = int()

                for student in done_question:
                    done[question][student] = done_question[student]
            
                for student in doing_question:
                    doing[question][student] = doing_question[student] 
        
            return done, doing, (total_revs, total_used)
        else:
            for question in questions:
                done[question] = dict()
                doing[question] = dict()
                stats = Question(self.request, question).stats(user, False)
                done_question, doing_question, question_totals = stats
                    
                for student in done_question:
                    done[question][student] = tuple()

                for student in doing_question:
                    doing[question][student] = tuple()

            return done, doing, tuple()

    def used_time(self, user=None):
        flow = self.questionlist()
        total_time = int()
        total_count = int()

        for questionpage in flow:
            used_time, try_count = Question(self.request, questionpage).used_time(user) 
            total_time += used_time
            total_count += try_count

        return total_time, total_count

    def title(self):
        raw_content = Page(self.request, self.pagename).get_raw_body()
        title = unicode()

        for line in raw_content.split("\n"):
            if line.startswith("== ") and line.endswith(" =="):
                title = line[3:-3]

        return title

    def rename(self, newname, comment=u""):
        title = self.title()
        newname = newname[:240]

        #rename task in the flow
        course = Course(self.request, self.request.cfg.raippa_config)
        if course and Page(self.request, course.flowpage).exists():
            keys = get_keys(self.request, course.flowpage)

            if self.pagename in keys:
                metas = get_metas(self.request, course.flowpage, keys, checkAccess=False)

                remove = {course.flowpage: [self.pagename]}
                add = {course.flowpage: {newname: metas[self.pagename]}}

                success, msg = set_metas(self.request, remove, dict(), add)

                if not success:
                    return success, msg

        success, msg = rename_page(self.request, self.pagename, newname, comment)

        if not success:
            return success, msg

        return True, u'Task "%s" was successfully renamed!' % title

    def delete(self, comment=u"", delete_questions=False):
        title = self.title()

        #move prerequisites
        prerequisites = self.options().get('prerequisite', list())

        pagedata = self.request.graphdata.getpage(self.pagename)
        pages = pagedata.get('in', dict()).get('prerequisite', list())

        for pagename in pages:
            metas = get_metas(self.request, pagename, ['prerequisite'], checkAccess=False)

            new_prerequisites = list()
            for prerequisite in prerequisites:
                new_prerequisites.append(addlink(prerequisite))
 
            for prerequisite in metas.get('prerequisite', list()):
                if self.pagename != removelink(prerequisite) and prerequisite not in prerequisites:
                    new_prerequisites.append(prerequisite)

            remove = {pagename: ['prerequisite']}
            add = {pagename: {'prerequisite': new_prerequisites}}

            success, msg = set_metas(self.request, remove, dict(), add)

            if not success:
                return success, msg

        #remove task from the flow
        course = Course(self.request, self.request.cfg.raippa_config)
        if course and Page(self.request, course.flowpage).exists():
            keys = get_keys(self.request, course.flowpage)
            metas = get_metas(self.request, course.flowpage, keys, checkAccess=False)

            new_metas = dict()
            next = metas.get(self.pagename, list())
            
            for point in metas:
                if point != self.pagename:
                    new_metas[point] = list()
                    for nextpoint in metas[point]:
                        parsed_next = nextpoint

                        parts = nextpoint.split()
                        if len(parts) > 1 and not parts[0].startswith("[["):
                            reason = parts[0]
                            parsed_next = " ".join(parts[1:])

                        parsed_next = removelink(parsed_next)
                    
                        if parsed_next == self.pagename:
                            new_metas[point].extend(next)
                        else:
                            new_metas[point].append(nextpoint)

            remove = {course.flowpage: metas.keys()}
            add = {course.flowpage: new_metas}
            success, msg = set_metas(self.request, remove, dict(), add)
            
            if not success:
                return success, msg

        #remove questionpages
        if delete_questions:
            for questionpage in self.questionlist():
                if Page(self.request, questionpage).exists():
                    success, msg = Question(self.request, questionpage).delete(comment)
                
                    if not success:
                        return success, msg

        success, msg = delete_page(self.request, self.pagename, comment)

        if not success:
            return success, msg
                
        return True, u'Task "%s" was successfully deleted!' % title


    def save_flow(self, flow, options):
        save_data = dict()
        save_data[self.optionspage] = dict()
        save_data[self.flowpage] = dict()
        remove = dict()
        remove[self.pagename] = list()
        remove[self.optionspage] = list()
        remove[self.flowpage] = list()
        
        remove[self.flowpage] = self.questionlist()
        remove[self.flowpage].extend(["first"])

        #TODO: create copy of questions that already exists in other tasks
        if flow:
            for key,val in flow.iteritems():
                if len(val) > 1:
                    raise TooManyValuesException("Trying to save too many values to flow node.")
                save_data[self.flowpage][key] = [addlink(val[0])]

            remove[self.flowpage].extend(["task"])
            save_data[self.flowpage]["task"] = [addlink(self.pagename)]
            save_data[self.flowpage]["gwikicategory"] = [rc['taskflow']]

        remove[self.optionspage].extend(["type", "deadline", "task", "option"])
        save_data[self.optionspage]["type"] = options.get("type", [u""])
        save_data[self.optionspage]["deadline"] = options.get("deadline", [u""])
        save_data[self.optionspage]["option"] = options.get("consecutive", [u""])

        save_data[self.optionspage]["task"] =  [addlink(self.pagename)]
        save_data[self.optionspage]["gwikicategory"] =  [rc['taskoptions']]

        success, msg =  set_metas(self.request, remove, dict(), save_data)

        return success, msg

class Course:

    def __init__(self, request, config):
        self.request = request
        self.config = config

        if not Page(request, config).exists():
            self.graphpage = None
            self.flowpage = None
            self.flow = None
        else:
            keys = ['graph', 'flow'] 
            metas = get_metas(self.request, self.config, keys, checkAccess=False)

            graphs = metas.get('graph', list())
            if len(graphs) == 1:
                self.graphpage = removelink(graphs[0])
            elif len(graphs) < 1:
                self.graphpage = None
            else:
                raise TooManyValuesException("Page %s has too many graph values" % self.config)

            flows = metas.get('flow', list())
            if len(flows) == 1:
                self.flowpage = removelink(flows[0])
                self.flow = Flow(request, self.flowpage)
            elif len(flows) < 1:
                self.flowpage = None
                self.flow = None
            else:
                raise TooManyValuesException("Page %s has too many flow values" % self.config)

    def save_flow(self, flow, prerequirements):
        save_data = dict()
        save_data[self.flowpage] = dict()
        remove = dict()
        remove[self.flowpage] = list()

        #remove old prerequirements from tasks
        tasks = pages_in_category(self.request, "CategoryTask")
        for taskpage in tasks:
            task = Task(self.request, taskpage)
            options = task.options()
            if options.get("prerequisite", []):
                remove[task.optionspage] = ["prerequisite"]

        if flow:
            remove[self.flowpage] = self.flow.fullflow().keys()
            for key,values in flow.iteritems():
                save_data[self.flowpage][key] = list()
                for val in values:
                    save_data[self.flowpage][key].append("success " + addlink(val))

                    task = Task(self.request, val)
                    save_data[task.optionspage] = dict()
                    save_data[task.optionspage]["prerequisite"] = list()
                    save_data[task.optionspage]["gwikicategory"] =  [rc['taskoptions']]
                    for req in prerequirements[val]:
                        save_data[task.optionspage]["prerequisite"].append(addlink(req))

        success, msg =  set_metas(self.request, remove, dict(), save_data)

        return success, msg


    def used_time(self, user=None):
        total_time = int()
        total_tries = int()

        flow = self.flow.fullflow()
        for taskpage in flow:
            if taskpage != "first":
                task = Task(request, taskpage)
                task_time, try_count = task.used_time(user)
                total_time += task_time
                total_tries += try_count 
                
        return total_time, total_tries

