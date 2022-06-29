import os
import ast

import requests

import progressbar

pbar=None
def show_progress(block_num, block_size, total_size):
    global pbar
    if pbar is None:
        pbar = progressbar.ProgressBar(maxval=total_size)
        pbar.start()
    downloaded = block_num * block_size
    if downloaded < total_size:
        pbar.update(downloaded)
    else:
        pbar.finish()
        pbar = None

def isWNN(label):
    return label[:-2].isdecimal() and label.endswith('-n')

def getCNName(dflName):
    retq = str(dflName)
    if '..' in retq:
        retq = retq[:retq.find('..')]
    retq = retq.replace('_ZZ_',"'")
    retq = "/c/en/" + retq.replace('.','/')
    return str(retq)

def getDFLName(cnName):
    retq = str(cnName)
    retq = retq.replace("'",'_ZZ_')
    retq = retq[len("/c/en/"):].replace('/','.')
    return retq

def getSubconcepts(dflName):
    try:
        edges = requests.get('http://api.conceptnet.io/query?end=%s&rel=/r/IsA&limit=1000' % getCNName(dflName)).json()['edges']
    except:
        edges = []
    return set([getDFLName(e['start']['@id']) for e in edges])

def getWNURLs(dflName):
    try:
        edges = requests.get('http://api.conceptnet.io/query?start=%s&rel=/r/ExternalURL&limit=1000' % getCNName(dflName)).json()['edges']
    except:
        edges = []
    return set([e['end']['label'][1:] for e in edges if isWNN(e['end']['label'][1:])])

def getWNHypernyms(wnss):
    retq = []
    try:
        wnd = requests.get('http://wordnet-rdf.princeton.edu/json/id/%s' % wnss).json()[0]
        retq = [x['target'] for x in wnd['relations'] if 'hypernym' == x['rel_type']]
    except:
        pass
    return retq

def getWNDef(wnss):
    retq = ""
    try:
        wnd = requests.get('http://wordnet-rdf.princeton.edu/json/id/%s' % wnss).json()[0]
        retq = wnd['definition']
    except:
        pass
    return retq

basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")

objectTaxonomyFilename = os.path.join(basePath,"resources/ObjectTaxonomy.res")
verbTaxonomyFilename = os.path.join(basePath,"resources/VerbTaxonomy.res")
defsFilename = os.path.join(basePath,"resources/WordNetDefinitions.res")
lemmasFilename = os.path.join(basePath,"resources/LemmaMap.res")
dupsFilename = os.path.join(basePath,"scripts/dupwarns.log")

## Step 1: update taxonomy
print("Update taxonomy ...")
ots = [ast.literal_eval(x) for x in open(objectTaxonomyFilename).read().splitlines() if x.strip()]
defs = {y[0]:y[1] for y in [ast.literal_eval(x) for x in open(defsFilename).read().splitlines() if x.strip()]}

superclasses = {}
for t in ots:
    if t[0] not in superclasses:
        superclasses[t[0]] = set([])
    superclasses[t[0]].add(t[1])

tovisit = set([x[0] for x in ots]+[x[1] for x in ots])
visited = set([])

dupwarns = set([])

tovisit = set(['plaything.n.wn.artifact', 'substance.n.wn.substance', 'material.n.wn.substance'])

while tovisit:
    cc = tovisit.pop()
    print('                                                     ', end='\r')
    print(cc, end='\r')
    if cc not in visited:
        visited.add(cc)
        if 1 == len(defs[cc]):
            wnss = defs[cc][0][0]
            cns = cc
            if '..' in cc:
                cns = cc[:cc.find('..')]
            subs = getSubconcepts(cns)
            subWNSS = {x: getWNURLs(x) for x in subs}
            subs = set([])
            for s in subWNSS.keys():
                if s in visited:
                    continue
                if 1 != len(subWNSS[s]):
                    dupwarns.add(s)
                elif wnss in getWNHypernyms(list(subWNSS[s])[0]):
                   subs.add(s)
                   defs[s] = ((list(subWNSS[s])[0], getWNDef(list(subWNSS[s])[0])),)
            for s in subs:
                if s not in superclasses:
                    superclasses[s] = set([])
                superclasses[s].add(cc)
                tovisit.add(s)
            wnss = defs[cc][0][0]
        else:
            dupwarns.add(cc)

with open(dupsFilename, 'w') as outfile:
    for e in sorted(list(dupwarns)):
        _ = outfile.write("%s\n" % str(e))

with open(objectTaxonomyFilename, 'w') as outfile:
    for e in sorted(superclasses.keys()):
        for c in sorted(list(superclasses[e])):
            _ = outfile.write("%s\n" % str((e, c)))

with open(defsFilename, 'w') as outfile:
    for k in sorted(defs.keys()):
        _ = outfile.write("%s\n" % str((k, defs[k])))

## Step 2: gather synsets for concepts:
print("Gather synsets for concepts ...")
ots = [ast.literal_eval(x) for x in open(objectTaxonomyFilename).read().splitlines() if x.strip()]
ts = ots + [ast.literal_eval(x) for x in open(verbTaxonomyFilename).read().splitlines() if x.strip()]

concs = set([x[0] for x in ts]).union(set([x[1] for x in ts]))

defs = {y[0]:y[1] for y in [ast.literal_eval(x) for x in open(defsFilename).read().splitlines() if x.strip()]}

exceptions = {
    'sennenhund.n.wn.animal': [{'end':{'label': '102110072-n'}}],
    'fold.v.wn.change': [{'end':{'label':'200399044-v'}}, {'end':{'label':'200565772-v'}}],
}

for k, c in enumerate(concs):
    if (c in defs) and (defs[c]):
        continue
    if c in exceptions:
        edges = exceptions[c]
    else:
        try:
            edges = requests.get('http://api.conceptnet.io/query?start=%s&rel=/r/ExternalURL&limit=1000' % getCNName(c)).json()['edges']
        except:
            edges = []
    aux = []
    for e in edges:
        wnss = e['end']['label'][1:]
        try:
            wnd = requests.get('http://wordnet-rdf.princeton.edu/json/id/%s' % wnss).json()[0]
            aux.append((wnd['id'], wnd['definition']))
        except:
            pass
    defs[c] = tuple(aux)
    if not defs[c]:
        print(c)
    show_progress(k, 1, len(concs))
show_progress(len(concs), 1, len(concs))

empties = set([])
ambiguous = set([])
for k in defs.keys():
    if 0 == len(defs[k]):
        empties.add(k)
    if 1 < len(defs[k]):
        ambiguous.add(k)

print("Link entries", len(defs))
print("Empty entries", len(empties))
print("Ambiguous entries", len(ambiguous))

with open(defsFilename, 'w') as outfile:
    for k in sorted(defs.keys()):
        _ = outfile.write("%s\n" % str((k, defs[k])))


## Step 3: update lemma map
print("Gather lemmas for concepts ...")
defs = {y[0]:y[1] for y in [ast.literal_eval(x) for x in open(defsFilename).read().splitlines() if x.strip()]}
lemmaMap = {y[0]:set(list(y[1])) for y in [ast.literal_eval(x) for x in open(lemmasFilename).read().splitlines() if x.strip()]}

for k,c in enumerate(defs.keys()):
    if c not in lemmaMap:
        wnsss = [x[0] for x in defs[c]]
        aux = set([])
        for wnss in wnsss:
            try:
                wnd = requests.get('http://wordnet-rdf.princeton.edu/json/id/%s' % wnss).json()[0]
                aux = aux.union([x['lemma'] for x in wnd['lemmas']])
            except:
                pass
        lemmaMap[c] = aux
    show_progress(k, 1, len(defs))
show_progress(len(defs), 1, len(defs))

with open(lemmasFilename, 'w') as outfile:
    for k in sorted(lemmaMap.keys()):
        _ = outfile.write("%s\n" % str((k, tuple(sorted(list(lemmaMap[k]))))))

