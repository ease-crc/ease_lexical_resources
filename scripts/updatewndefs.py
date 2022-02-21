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

basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")

objectTaxonomyFilename = os.path.join(basePath,"resources/ObjectTaxonomy.res")
verbTaxonomyFilename = os.path.join(basePath,"resources/VerbTaxonomy.res")
defsFilename = os.path.join(basePath,"resources/WordNetDefinitions.res")

ts = [ast.literal_eval(x) for x in open(objectTaxonomyFilename).read().splitlines() if x.strip()]
ts = ts + [ast.literal_eval(x) for x in open(verbTaxonomyFilename).read().splitlines() if x.strip()]

concs = set([x[0] for x in ts]).union(set([x[1] for x in ts]))

defs = {y[0]:y[1] for y in [ast.literal_eval(x) for x in open(defsFilename).read().splitlines() if x.strip()]}

exceptions = {
    'sennenhund.n.wn.animal': [{'end':{'label': '102110072-n'}}],
    'fold.v.wn.change': [{'end':{'label':'200399044-v'}}, {'end':{'label':'200565772-v'}}],
}

def getCNName(dflName):
    retq = str(dflName)
    if '..' in retq:
        retq = retq[:retq.find('..')]
    retq = retq.replace('_ZZ_',"'")
    retq = "/c/en/" + retq.replace('.','/')
    return str(retq)

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

