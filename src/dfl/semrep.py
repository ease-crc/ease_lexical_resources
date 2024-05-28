import os
import json
import ast
import re
import inflection

import urllib.request
import urllib.parse
from rdflib import Graph

import platform

import dfl.wnlinks as wn
import dfl.dlquery as dl

blackHole = ">/dev/null 2>&1"
if "Windows" == platform.system():
    blackHole = " > NUL"

basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")
lemmaFilePath = os.path.join(basePath, "resources/LemmaMap.res")
wordnetMapFilePath = os.path.join(basePath, "resources/mapping_wordnet.json")
hasPartFilePath = os.path.join(basePath, "resources/DFLHasPart.res")
isMadeOfFilePath = os.path.join(basePath, "resources/DFLConsistsOf.res")
wordnetDefsFilePath = os.path.join(basePath, "resources/WordNetDefinitions.res")

wn31Defs = {}
for l in open(wordnetDefsFilePath).read().splitlines():
    l = ast.literal_eval(l)
    for e in l[1]:
        wn31Defs[e[0]] = e[1]

keyFRED = ''
keyWikiData = ''
fred_uri = "http://wit.istc.cnr.it/stlab-tools/fred"

queryFREDTopic = """
SELECT DISTINCT ?db WHERE {
    ?topic <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#hasQuality> <http://www.ontologydesignpatterns.org/ont/fred/domain.owl#Topic> .
    ?topic <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?firstClass .
    ?firstClass <http://www.w3.org/2000/01/rdf-schema#subClassOf>* ?lastClass .     
    ?lastClass <http://www.w3.org/2002/07/owl#equivalentClass> ?db.
}
"""

def setFREDKey(newKey):
    global keyFRED
    keyFRED = str(newKey)

def setWikiDataKey(newKey):
    global keyWikiData
    keyWikiData = str(newKey)

wn312wn30 = {}
try:
    wnmaps = json.loads(open(wordnetMapFilePath).read())
    def _adjWNMap(x):
        pad = "0"*(8-len(x)+1)
        return pad + x[1:] + "-" + x[0]
    wn312wn30 = {_adjWNMap(k): _adjWNMap(v) for k, v in wnmaps[0]["synset-mapping"].items()}
except:
    pass

dflHasPart = {}
for l in open(hasPartFilePath).read().splitlines():
    if l.strip():
        conc, part = ast.literal_eval(l)
        conc = "dfl:" + conc
        part = "dfl:" + part
        dflHasPart[conc] = dflHasPart.get(conc, set()).union([part])

dflIsMadeOf = {}
for l in open(isMadeOfFilePath).read().splitlines():
    if l.strip():
        conc, mat = ast.literal_eval(l)
        conc = "dfl:" + conc
        mat = "dfl:" + mat
        dflIsMadeOf[conc] = dflIsMadeOf.get(conc, set()).union([mat])

dl.buildCache()

wd_artificialPhysicalObject = "Q8205328"
wd_wordnet31SynsetId = "P8814"
wd_hasParts = "P527"
wd_isMadeOf = "P186"

dfl2lemmas = [ast.literal_eval(l) for l in open(lemmaFilePath).read().splitlines() if l.strip()]
lemmaMap = {}
for e in dfl2lemmas:
    conc, ls = e
    for l in ls:
        lemmaMap[l] = lemmaMap.get(l,set()).union([conc])

def normalizeName(name):
    return inflection.singularize(inflection.camelize(name).lower().replace('_',' ').strip())

def getDFLCandidatesFromLemma(name, superclassFilters):
    def _dflReport(conc, superclassFilters):
        if (superclassFilters is not None) and (0 < len(superclassFilters)):
            if not superclassFilters.intersection(dl.whatSuperclasses(conc)):
                return []
        cn58 = wn.getConceptNetName(conc)
        wn31 = {x[0]: x[1] for x in wn.getWordNetSynsetsAndDefs(conc)}
        retq = []
        for wn31SS, wn31Df in wn31.items():
            wn30SS = wn312wn30.get(wn31SS)
            retq.append({"SOMA_DFL": "dfl:"+conc, "definition": wn31Df, "WordNet 3.1": wn31SS, "WordNet 3.0": wn30SS, "ConceptNet 5.8": cn58})
        return retq
    superclassFilters = set(superclassFilters)
    cs1 = lemmaMap.get(name)
    if cs1 is None:
        maxFit = 0
        for k, v in lemmaMap.items():
            if name.endswith(k) and (maxFit <= len(k)):
                if (cs1 is None) or (maxFit < len(k)):
                    cs1 = set()
                maxFit = len(k)
                cs1 = cs1.union(v)
    if cs1 is None:
        return []
    retq = []
    for x in cs1:
        retq += _dflReport(x, superclassFilters)
    return retq

def _makeWikiDataURL(wdC):
    wdCAdj = wdC[wdC.rfind("/")+1:]
    return f"https://www.wikidata.org/w/rest.php/wikibase/v0/entities/items/{wdCAdj}/statements"

def _makeFREDURL(name):
    return fred_uri+"?"+urllib.parse.urlencode({'text':"a %s in a room" % name})

def _callAPI(url, acc, apiKey=None):
    headers = {"Accept": acc}
    if apiKey is not None:
        headers["Authorization"] = f"Bearer {apiKey}"
    ans = urllib.request.urlopen(urllib.request.Request(url,headers=headers)).read()
    if "application/json" == acc:
        retq = json.loads(ans.decode("utf-8"))
    elif "text/turtle":
        retq = Graph()
        retq.parse(data=ans,format="text/turtle")
    return retq

def getFREDCandidatesFromLemma(name, superclassFilters):
    def _dbpReport(conc, superclassFilters):
        try:
            js = _callAPI(conc, "application/json")
            cdb = js[conc]
            wd = [x["value"] for x in cdb["http://www.w3.org/2002/07/owl#sameAs"] if "wikidata" in x["value"]]
            retq = []
            for wdC in wd:
                js = _callAPI(_makeWikiDataURL(wdC), "application/json", apiKey=keyWikiData)
                wn31 = [x["value"]["content"] for x in js.get(wd_wordnet31SynsetId, [])]
                wn31 = {x: wn31Defs.get(x) for x in wn31}
                for wn31SS, wn31Df in wn31.items():
                    somaDFLs = wn.getDFLNamesForWordNetID(wn31SS)
                    if somaDFLs is None:
                        continue
                    for somaDFL in somaDFLs:
                        wn30SS = wn312wn30.get(wn31SS)
                        cn58 = wn.getConceptNetName(somaDFL)
                        retq.append({"dbpedia": conc, "wikidata": wdC, "WordNet 3.0": wn30SS, "WordNet 3.1": wn31SS, "definition": wn31Df, "SOMA_DFL": "dfl:"+somaDFL, "ConceptNet 5.8": cn58})
            return retq
        except BaseException as e:
            print(e)
            return [{"dbpedia": conc}]
    try:
        g = _callAPI(_makeFREDURL(name), "text/turtle", apiKey=keyFRED)
        retq = []
        aux = [_dbpReport(str(list(x.values())[0]), superclassFilters) for x in g.query(queryFREDTopic).bindings]
        for x in aux:
            retq += x
        #for s,p,o in g:
        #    if ("dbpedia" in o) and (("http://dbpedia.org/resource/Room" != str(o)) or ("room" == name)):
        #        retq += (_dbpReport(str(o), superclassFilters))
        return retq
    except BaseException as e:
        print(e)
        return None
    
def semanticReport(name, onlyObjects=True, superclassFilters=None):
    def _catchContainers(r, name, superclassFilters):
        if ("SOMA_DFL" not in r) or ("dfl:container.n.wn.artifact" not in dl.whatSuperclasses(r["SOMA_DFL"])):
            return [r]
        aux = getDFLCandidatesFromLemma(name, superclassFilters.get("SOMA_DFL", []))
        retq = []
        for e in aux:
            if ("SOMA_DFL" in r) and (r["SOMA_DFL"] == e.get("SOMA_DFL")):
                retq.append(r)
            else:
                retq.append(e)
        return retq
    name = normalizeName(name)
    if superclassFilters is None:
        superclassFilters = {}
    candidates = getFREDCandidatesFromLemma(name, superclassFilters)
    if (candidates is None) or (0 == len(candidates)):
        candidates = getDFLCandidatesFromLemma(name, superclassFilters.get("SOMA_DFL", []))
    if candidates is None:
        candidates = []
    if onlyObjects:
        candidates = [x for x in candidates if ".v.wn." not in x.get("SOMA_DFL", "")]
    retq = []
    for e in candidates:
        retq += _catchContainers(e, name, superclassFilters)
    return retq

def semanticReportForPhysicalObject(name):
    def _queryWikiDataObjectProps(entity):
        wde = _callAPI(_makeWikiDataURL(entity["wikidata"]), "application/json", apiKey=keyWikiData)
        entity["hasPart"] += [x["value"]["content"] for x in wde.get(wd_hasParts,[])]
        entity["isMadeOf"] += [x["value"]["content"] for x in wde.get(wd_isMadeOf,[])]
        return
    def _queryDFLObjectProps(entity):
        conc = entity["SOMA_DFL"]
        dispositions = dl.whatDispositionsDoesObjectHave(conc)
        instrumentalDispositions = []
        patientDispositions = []
        for d in dispositions:
            if d.endswith(".Instrument"):
                instrumentalDispositions.append(d[:-len(".Instrument")])
            else:
                for suff in [".Patient", ".Patient2", ".Theme", "Theme2"]:
                    if d.endswith(suff):
                        patientDispositions.append(d[:-len(suff)])
        entity["hasPart"] += list(dflHasPart.get(conc, []))
        entity["isMadeOf"] += list(dflIsMadeOf.get(conc, []))
        entity["usedFor"] += instrumentalDispositions
        entity["canBe"] += patientDispositions
    cs = semanticReport(name, )#{"SOMA_DFL": ["dul:PhysicalObject"]})
    for e in cs:
        e["hasPart"] = []
        e["isMadeOf"] = []
        e["usedFor"] = []
        e["canBe"] = []
        objQueryFns = {"SOMA_DFL": _queryDFLObjectProps, "wikidata": _queryWikiDataObjectProps}
        for repo, fn in objQueryFns.items():
            if repo in e:
                fn(e)
    return cs

def semanticReportForScene(classNames):
    sreps = {x:semanticReportForPhysicalObject(x) for x in classNames}
    toolRoles = {}
    patientRoles = {}
    for className, srep in sreps.items():
        for c in srep:
            for t in c["usedFor"]:
                if t not in toolRoles:
                    toolRoles[t] = set()
                toolRoles[t].add((className, c.get("SOMA_DFL")))
            for p in c["canBe"]:
                if p not in patientRoles:
                    patientRoles[p] = set()
                patientRoles[p].add((className, c.get("SOMA_DFL")))
    useMatches = []
    for tr in toolRoles:
        if tr in patientRoles:
            for to in toolRoles[tr]:
                _, somaDFLNameTool = to
                poss = set(dl.whatObjectsCanToolPerformTaskOn(tr, somaDFLNameTool))
                for po in patientRoles[tr]:
                    _, somaDFLNamePatient = po
                    if somaDFLNamePatient in poss:
                        useMatches.append((tr, to, po))
    return sreps, useMatches
