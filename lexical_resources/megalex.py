import ast

import json

# TODO: some lexicon entry keys will be tuples. These are to be understood as sets, so need to test for their presence differently.

def safelyAccessFirstString(repo, key, default=""):
    retq = default
    if key in repo:
        retq = repo[key]
        if isinstance(retq, list):
            retq = retq[0]
    return retq

def safelyAccessStrings(repo, key):
    if key in repo:
        retq = repo[key]
        if not isinstance(retq, list):
            retq = [retq]
        return retq
    return []

def loadMegaLexicon(fileName):
    megalexicon = {}
    lexentries = []
    for line in open(fileName).read().splitlines():
        line = line.strip()
        if "" != line:
            lexentries.append(ast.literal_eval(line))
    for lex in lexentries:
        megalexicon[lex[0]] = lex[1]
    return megalexicon

def mergeLexiconEntryForm(accumulatingForm, form, lemma, feature, logFile=None):
    changed = False
    newAccumulatingForm = accumulatingForm
    # Forms are expected to be strings or lists
    if isinstance(accumulatingForm, str):
        if isinstance(form, str):
            if accumulatingForm != form:
                newAccumulatingForm = [accumulatingForm, form]
                changed = True
        else:
            newAccumulatingForm = form
            if accumulatingForm not in newAccumulatingForm:
                newAccumulatingForm = [accumulatingForm] + form
            changed = True
    else:
        if isinstance(form, str):
            if form not in accumulatingForm:
                newAccumulatingForm = accumulatingForm + [form]
                changed = True
        else:
            news = list(set(form) - set(accumulatingForm))
            if news:
                newAccumulatingForm = accumulatingForm + news
    if logFile and changed:
        logFile.write("LOG: EXPANDFEATURE: addition to %s, form/feature %s: %s -> %s\n" % (str(lemma), str(feature), str(accumulatingForm), str(newAccumulatingForm)))
    accumulatingForm = newAccumulatingForm
    return accumulatingForm

def mergeLexiconEntries(accumulatingEntry, entry, lemma, logFile=None):
    for k, v in entry.items():
        if (k not in accumulatingEntry):
            if v:
                accumulatingEntry[k] = v
                if logFile:
                    logFile.write("LOG: ADDFEATURE: addition to %s, form/feature %s\n" % (str(lemma), str(k)))
        else:
            accumulatingEntry[k] = mergeLexiconEntryForm(accumulatingEntry[k], v, lemma, k, logFile)
    return accumulatingEntry

def mergeMegaLexicons(accumulatingLexicon, lexicon, logFile=None):
    for k, v in lexicon.items():
        if k not in accumulatingLexicon:
            # Easy case: there's an entry in lexicon that's not already in accumulatingLexicon, so just add it 
            accumulatingLexicon[k] = v
            if logFile:
                logFile.write("LOG: ADDLEMMA: addition of lemma %s\n" % (str(k)))
        else:
            # The entry in lexicon already exists in accumulatingLexicon, but maybe we can add new info
            accumulatingLexicon[k] = mergeLexiconEntries(accumulatingLexicon[k], v, k, logFile)
    return accumulatingLexicon

def storeMegaLexicon(fileName, megalexicon):
    with open(fileName, "w") as outfile:
        megalist = list(megalexicon.items())
        megalist.sort(key=lambda x: str(x[0]))
        for entry in megalist:
            outfile.write("%s\n" % str((entry[0], entry[1])))

