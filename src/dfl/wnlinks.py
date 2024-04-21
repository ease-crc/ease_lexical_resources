import os
import ast

basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")

defsFilename = os.path.join(basePath,"resources/WordNetDefinitions.res")

defs = {y[0]:y[1] for y in [ast.literal_eval(x) for x in open(defsFilename).read().splitlines() if x.strip()]}

wordnet2DFL = {}
for dflName, wndata in defs.items():
    for e in wndata:
        if e[0] not in wordnet2DFL:
            wordnet2DFL[e[0]] = set([])
        wordnet2DFL[e[0]].add(dflName)

def _eagerBeaverComfort(dflName):
    if dflName.startswith('dfl:'):
        dflName = dflName[len('dfl:'):]
    return dflName

def _prettyprintSortedSet(data):
    retq = ""
    for e in sorted(list(data)):
        retq = retq + e + ", "
    return retq[:-2]

def getConceptNetName(dflName, prettyprint=False):
    dflName = _eagerBeaverComfort(dflName)
    if dflName not in defs:
        if prettyprint:
            return "Error: concept name %s is either not found in the DFL or has no external links!" % dflName
        return None
    retq = str(dflName)
    if '..' in retq:
        retq = retq[:retq.find('..')]
    retq = retq.replace('_ZZ_',"'")
    retq = "/c/en/" + retq.replace('.','/')
    if prettyprint:
        retq = "ConceptNet 5.8:\t" + retq + "\n"
    return retq

conceptnet2DFL = {}
for dflName in defs.keys():
    cnName = getConceptNetName(dflName)
    if cnName not in conceptnet2DFL:
        conceptnet2DFL[cnName] = set([])
    conceptnet2DFL[cnName].add(dflName)

def getDFLNamesForConceptNetName(cnName, prettyprint=False):
    if cnName not in conceptnet2DFL:
        if prettyprint:
            return "Error: concept name %s is not found in DFL!" % cnName
        return set([])
    if prettyprint:
        return _prettyprintSortedSet(conceptnet2DFL[cnName])
    return conceptnet2DFL[cnName]

def getWordNetSynsetsAndDefs(dflName, prettyprint=False, prefix=None):
    dflName = _eagerBeaverComfort(dflName)
    if dflName not in defs:
        if prettyprint:
            return "Error: concept name %s is either not found in the DFL or has no external links!" % dflName
        return None
    data = sorted(list(defs[dflName]))
    if prettyprint:
        if None == prefix:
            prefix = "WordNet 3.1:"
        if data:
            retq = prefix + "\t" + str(data[0][0]) + ":\t" + str(data[0][1]) + "\n"
        else:
            retq = prefix + "\n"
        for e in data[1:]:
            retq = retq + (" "*len(prefix)) + "\t" + str(e[0]) + ":\t" + str(e[1]) + "\n"
        return retq
    return data

def getDFLNamesForWordNetID(wnName, prettyprint=False):
    if wnName not in wordnet2DFL:
        if prettyprint:
            return "Error: concept name %s is either not found in the DFL or has no external links!" % wnName
        return None
    data = wordnet2DFL[wnName]
    if prettyprint:
        return _prettyprintSortedSet(wordnet2DFL[wnName])
    return data

outlinkFns = {'ConceptNet 5.8': getConceptNetName, 'WordNet 3.1': getWordNetSynsetsAndDefs}

def whoIsDFLEntity(dflName, showLinks=None):
    retq = ""
    if showLinks is None:
        showLinks = set([])
    if not showLinks:
        showLinks = sorted(outlinkFns.keys())
    else:
        showLinks = sorted(list(showLinks.intersection(set(outlinkFns.keys()))))
    for k in showLinks:
        retq = retq + outlinkFns[k](dflName, prettyprint=True)
    return retq

def getDefinitions(dflName):
    return getWordNetSynsetsAndDefs(dflName, prettyprint=True, prefix=_eagerBeaverComfort(dflName) + ":")

