import errno
import os
import ast
import re
import itertools

import platform
import shutil

blackHole = ">/dev/null 2>&1"
if "Windows" == platform.system():
    blackHole = " > NUL"

basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")

dflOWLFilename = os.path.join(basePath, "owl/SOMA_DFL.owl")
dflQueryOWLFilename = os.path.join(basePath, "owl/SOMA_DFL_query.owl")
dflResponseFilename = os.path.join(basePath, "owl/SOMA_DFL_response.owl")
owlFolder = os.path.join(basePath, "owl")
resourcesFolder = os.path.join(basePath, "resources")
dflUseMatchFilename = os.path.join(resourcesFolder, "DFLUseMatch.res")
dflHasPartFilename = os.path.join(resourcesFolder, "DFLHasPart.res")
dflConsistsOfFilename = os.path.join(resourcesFolder, "DFLConsistsOf.res")
koncludeBinary = os.path.join(basePath, "bin/Konclude")
if "Windows" == platform.system():
    koncludeBinary = os.path.join(basePath, "bin/Konclude.exe")
if not os.path.isfile(koncludeBinary):
    koncludeBinary = os.environ.get("KONCLUDE_PATH")
if koncludeBinary is None:
    koncludeBinary = shutil.which("Konclude") or shutil.which("konclude")
if koncludeBinary is None:
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "konclude")

prefixes = [
    ('', 'http://www.ease-crc.org/ont/DLQuery.owl#'), 
    ('owl', 'http://www.w3.org/2002/07/owl#'),
    ('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
    ('xml', 'http://www.w3.org/XML/1998/namespace'),
    ('xsd', 'http://www.w3.org/2001/XMLSchema#'),
    ('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'),
    ('dul', 'http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#'),
    ('soma', 'http://www.ease-crc.org/ont/SOMA.owl#'),
    ('dfl', 'http://www.ease-crc.org/ont/SOMA_DFL.owl#')]

prefixesDFL = [
    ('', 'http://www.ease-crc.org/ont/SOMA_DFL.owl#'), 
    ('owl', 'http://www.w3.org/2002/07/owl#'),
    ('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
    ('xml', 'http://www.w3.org/XML/1998/namespace'),
    ('xsd', 'http://www.w3.org/2001/XMLSchema#'),
    ('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'),
    ('dul', 'http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#'),
    ('soma', 'http://www.ease-crc.org/ont/SOMA.owl#')]

partMap = {}
invPartMap = {}
for l in open(dflHasPartFilename).read().splitlines():
    l = ast.literal_eval(l)
    k, v = "dfl:"+l[0], "dfl:"+l[1]
    if k not in partMap:
        partMap[k] = set()
    partMap[k].add(v)
    if v not in invPartMap:
        invPartMap[v] = set()
    invPartMap[v].add(k)

constituentMap = {}
invConstituentMap = {}
for l in open(dflConsistsOfFilename).read().splitlines():
    l = ast.literal_eval(l)
    k, v = "dfl:"+l[0], "dfl:"+l[1]
    if k not in constituentMap:
        constituentMap[k] = set()
    constituentMap[k].add(v)
    if v not in invConstituentMap:
        invConstituentMap[v] = set()
    invConstituentMap[v].add(k)

def expandName(conceptName, prefs=None):
    if None == prefs:
        prefs = prefixes
    if ('<' == conceptName[0]) or (':' not in conceptName):
        return conceptName
    prefix = conceptName[:conceptName.find(':')]
    suffix = conceptName[conceptName.find(':') + 1:]
    retq = suffix
    for p, exp in prefs:
        if prefix == p:
            retq = exp + retq
    return retq

def contractName(conceptName, prefs=None):
    if None == prefs:
        prefs = prefixes
    if ('<' == conceptName[0]):
        conceptName = conceptName[1:]
    if ('>' == conceptName[-1]):
        conceptName = conceptName[:-1]
    retq = conceptName
    for p, exp in prefs:
        if conceptName.startswith(exp):
            retq = p + ":" + retq[len(exp):]
    return retq        

def queryHeader():
    retq = ""
    for p, exp in prefixes:
        retq = retq + ("Prefix(%s:=<%s>)\n" % (p, exp))
    retq = retq + ("Ontology(<http://www.ease-crc.org/ont/DLQuery.owl>\n")
    retq = retq + ("Import(<file://%s>)\n\n" % os.path.abspath(dflOWLFilename).replace("\\","/"))
    return retq

def inferTransitiveClosure(c, closedGraph, graph, ignoreConcepts=set([])):
    todo = set(graph.get(c,[]))
    closedGraph[c] = set([])
    while todo:
        sc = todo.pop()
        if (sc not in closedGraph[c]) and (sc not in ignoreConcepts):
            closedGraph[c].add(sc)
            if sc in graph:
                todo = todo.union(graph[sc])
    return closedGraph

def flipGraph(graph):
    retq = {}
    for v in graph:
        if v not in retq:
            retq[v] = set([])
        for u in graph[v]:
            if u not in retq:
                retq[u] = set([])
            retq[u].add(v)
    return retq

def _parseHomebrew(filename):
    inEq = False
    inSubcl = False
    superclasses = {}
    aux = []
    iriPLen = len("        <Class IRI=\"")
    with open(filename) as file_in:
        for l in file_in:
            if inEq:
                if "    </EquivalentClasses>\n" == l:
                    inEq = False
                    for c in aux:
                        if c not in superclasses:
                            superclasses[c] = set([])
                        for d in aux:
                            if d != c:
                                superclasses[c].add(d)
                    aux = []
                else:
                    if l.startswith("        <Class IRI=\""):
                        aux.append(l[iriPLen:-4])
            elif inSubcl:
                if "    </SubClassOf>\n" == l:
                    inSubcl = False
                    if 2 <= len(aux):
                        if aux[0] not in superclasses:
                            superclasses[aux[0]] = set([])
                        superclasses[aux[0]].add(aux[1])
                    aux = []
                else:
                    if l.startswith("        <Class IRI=\""):
                        aux.append(l[iriPLen:-4])
            else:
                if "    <SubClassOf>\n" == l:
                    inSubcl = True
                elif "    <EquivalentClasses>\n" == l:
                    inEq = True
    return superclasses

def parseResponse(filename):
    return _parseHomebrew(filename)

def runQuery(query):
    query = queryHeader() + query + "\n)\n"
    with open(dflQueryOWLFilename, "w") as outfile:
        outfile.write(query)
    os.system("cd %s && \"%s\" classification -i \"%s\" -o \"%s\" %s" % (owlFolder, koncludeBinary, dflQueryOWLFilename, dflResponseFilename, blackHole))
    return parseResponse(dflResponseFilename)

__dispositionSubsumptionCache__ = None
__dispositionSubsumptionCacheFlipped__ = None
__useMatchCache__ = None

def setOntologyFiles(ontologyFile, useMatchFile):
    global dflOWLFilename, dflUseMatchFilename
    global __dispositionSubsumptionCache__, __dispositionSubsumptionCacheFlipped__, __useMatchCache__
    dflOWLFilename = os.path.abspath(ontologyFile)
    dflUseMatchFilename = os.path.abspath(useMatchFile)
    __dispositionSubsumptionCache__ = None
    __dispositionSubsumptionCacheFlipped__ = None
    __useMatchCache__ = None

def __loadUseMatchCache():
    global __useMatchCache__
    __useMatchCache__ = [tuple([':'+y for y in ast.literal_eval(x)]) for x in open(dflUseMatchFilename).read().splitlines() if x.strip()]

def __getQueryName(conceptName):
    return conceptName + ".QUERY"

def __isQueryConcept(conceptName):
    return conceptName.startswith('http://www.ease-crc.org/ont/DLQuery.owl#') and conceptName.endswith('.QUERY')

def __filterApproximates(conceptName):
    if conceptName.startswith("dfl:Approximate"):
        return None
    return conceptName

def buildCache():
    global __dispositionSubsumptionCache__
    global __dispositionSubsumptionCacheFlipped__
    superclasses = runQuery("")
    subclasses = flipGraph(superclasses)
    dispositionConcept = expandName("soma:Disposition")
    dispositionTClosure = inferTransitiveClosure(dispositionConcept, {}, subclasses)[dispositionConcept]
    query = ""
    for c in dispositionTClosure:
        c = expandName(c)
        query = query + ("EquivalentClasses(<%s> ObjectSomeValuesFrom(dul:hasQuality <%s>))\n" % (__getQueryName(c), c))
    __dispositionSubsumptionCache__ = runQuery(query)
    __dispositionSubsumptionCacheFlipped__ = flipGraph(__dispositionSubsumptionCache__)

def whatsImpossible(usecache=True):
    retq = set()
    nothing = expandName("owl:Nothing")
    if usecache and __dispositionSubsumptionCache__:
        superclasses = __dispositionSubsumptionCache__
    else:
        superclasses = runQuery("")
    return sorted([y for y in [contractName(x) for x in superclasses.keys() if nothing in superclasses[x]] if __filterApproximates(y)])
    
## Loosely speaking: what is this?
def whatSuperclasses(concept, usecache=True):
    concept = expandName(concept)
    inferredSuperclasses = set([])
    if usecache and __dispositionSubsumptionCache__ and (concept in __dispositionSubsumptionCache__):
        inferredSuperclasses = inferTransitiveClosure(concept, {}, __dispositionSubsumptionCache__)[concept]
    elif (not usecache) or (not __dispositionSubsumptionCache__):
        superclasses = runQuery("")
        if concept in superclasses:
            inferredSuperclasses = inferTransitiveClosure(concept, {}, superclasses)[concept]
    return sorted([y for y in list(set([contractName(x) for x in inferredSuperclasses if (not __isQueryConcept(x))])) if __filterApproximates(y)])

## Loosely speaking: what kinds of this are there?
def whatSubclasses(concept, usecache=True):
    concept = expandName(concept)
    inferredSubclasses = set([])
    if usecache and __dispositionSubsumptionCacheFlipped__ and (concept in __dispositionSubsumptionCacheFlipped__):
        inferredSubclasses = inferTransitiveClosure(concept, {}, __dispositionSubsumptionCacheFlipped__)[concept]
    elif (not usecache) or (not __dispositionSubsumptionCacheFlipped__):
        subclasses = flipGraph(runQuery(""))
        if concept in subclasses:
            inferredSubclasses = inferTransitiveClosure(concept, {}, subclasses)[concept]
    return sorted([y for y in list(set([contractName(x) for x in inferredSubclasses if (not __isQueryConcept(x))])) if __filterApproximates(y)])

def whatsEquivalent(concept, usecache=True):
    sups=whatSuperclasses(concept,usecache)
    subs=whatSubclasses(concept,usecache)
    return sorted(list(set(sups).intersection(subs)))

## Loosely speaking: what hasPart relationships are known for this object?
def whatPartTypesDoesObjectHave(concept, usecache=True):
    superclasses = whatSuperclasses(concept, usecache=usecache)
    partTypes = set(itertools.chain.from_iterable([partMap.get(x,[]) for x in superclasses]))
    return sorted(list(partTypes))

def whatHasPartType(concept, usecache=True):
    subclasses = whatSubclasses(concept, usecache=usecache)
    objectTypes = set(itertools.chain.from_iterable([invPartMap.get(x,[]) for x in subclasses]))
    return sorted(list(objectTypes))

def whatConstituentsDoesObjectHave(concept, usecache=True):
    superclasses = whatSuperclasses(concept, usecache=usecache)
    constituentTypes = set(itertools.chain.from_iterable([constituentMap.get(x,[]) for x in superclasses]))
    return sorted(list(constituentTypes))

def whatHasConstituent(concept, usecache=True):
    subclasses = whatSubclasses(concept, usecache=usecache)
    objectTypes = set(itertools.chain.from_iterable([invConstituentMap.get(x,[]) for x in subclasses]))
    return sorted(list(objectTypes))

## Loosely speaking: what can do this action?
def whatHasDisposition(conceptDisposition, usecache=True):
    retq = []
    inferredSubclasses = set([])
    conceptDisposition = expandName(conceptDisposition)
    queryDisposition = __getQueryName(conceptDisposition)
    aux = expandName(queryDisposition)
    if usecache and __dispositionSubsumptionCacheFlipped__ and (aux in __dispositionSubsumptionCacheFlipped__):
        inferredSubclasses = inferTransitiveClosure(aux, {}, __dispositionSubsumptionCacheFlipped__)[aux]
    elif (not usecache) or (not __dispositionSubsumptionCacheFlipped__):
        subclasses = flipGraph(runQuery("EquivalentClasses(<%s> ObjectSomeValuesFrom(dul:hasQuality <%s>))\n" % (queryDisposition, conceptDisposition)))
        if aux in subclasses:
            inferredSubclasses = inferTransitiveClosure(aux, {}, subclasses)[aux]
    return sorted([y for y in list(set([contractName(x) for x in inferredSubclasses if (not __isQueryConcept(x))])) if __filterApproximates(y)])

## Loosely speaking: what can you do with this object?
def whatDispositionsDoesObjectHave(conceptObject, usecache=True):
    conceptObject = expandName(conceptObject)
    retq = []
    inferredSuperclasses = set([])
    bl = ["http://www.w3.org/2002/07/owl#Thing", "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#Entity", "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#Quality", "http://www.ease-crc.org/ont/SOMA.owl#Extrinsic", "http://www.ease-crc.org/ont/SOMA.owl#Disposition", "http://www.ease-crc.org/ont/SOMA.owl#PhysicalQuality", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor2", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Agent", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Asset", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Beneficiary", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Cause", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Experiencer", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Instrument", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Location", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Material", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient2", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Stimulus", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme2"]
    if usecache and __dispositionSubsumptionCache__ and (conceptObject in __dispositionSubsumptionCache__):
        inferredSuperclasses = [x.rstrip('.QUERY') for x in inferTransitiveClosure(conceptObject, {}, __dispositionSubsumptionCache__)[conceptObject] if __isQueryConcept(x)]
        retq = [y for y in ["dfl"+contractName(x) for x in inferredSuperclasses] if expandName(y) not in bl]
    elif (not usecache) or (not __dispositionSubsumptionCache__):
        superclasses = runQuery("")
        if conceptObject in superclasses:
            inferredSuperclasses = inferTransitiveClosure(conceptObject, {}, superclasses)[conceptObject]
        relevantConcepts = inferredSuperclasses.union(set([conceptObject]))
        lines = [x for x in open(dflOWLFilename).read().splitlines() if x.strip()]
        aux = []
        for l in lines:
            m = re.search("^SubClassOf\((?P<object>[a-zA-Z0-9\-_:,./#\<\>\+\*]+) ObjectSomeValuesFrom\(dul:hasQuality (?P<disposition>[a-zA-Z0-9\-_:,./#\<\>\+\*]+)\)\)$", l)
            if m:
                conceptObjectMatch = m.group('object')
                conceptDisposition = m.group('disposition')
                if (expandName(conceptObjectMatch, prefs=prefixesDFL) in relevantConcepts):
                    aux.append(expandName(conceptDisposition, prefs=prefixesDFL))
        superclasses[conceptObject] = set(aux)
        inferredSuperclasses = inferTransitiveClosure(conceptObject, {}, superclasses, ignoreConcepts=bl)[conceptObject]
        retq = sorted(list(set([contractName(x) for x in inferredSuperclasses if (not __isQueryConcept(x))])))
        #todo = set(aux)
        #done = set()
        #while todo:
        #    x = todo.pop()
        #    if (x not in done) and (x not in bl):
        #        done.add(x)
        #        retq.append(contractName(x))
        #        if x in superclasses:
        #            todo = todo.union(set(superclasses[x]))
    return sorted([y for y in list(set(retq)) if __filterApproximates(y)])

## Loosely speaking: can this object do this action?
# TODO: find a way to cache this. The "True" branch is cacheable, but proving an item cannot be used in some given way requires a new subsumption query
def doesObjectHaveDisposition(conceptObject, conceptDisposition):
    conceptObject = expandName(conceptObject)
    conceptDisposition = expandName(conceptDisposition)
    superclasses = runQuery("EquivalentClasses(:Query ObjectIntersectionOf(<%s> ObjectSomeValuesFrom(dul:hasQuality <%s>)))\n" % (conceptObject, conceptDisposition))
    auxQueryName = expandName(":Query")
    auxNothingName = expandName("owl:Nothing")
    if auxQueryName in superclasses:
        inferredSuperclasses = inferTransitiveClosure(auxQueryName, {}, superclasses)[auxQueryName]
        if auxNothingName in inferredSuperclasses:
            return False
    if conceptObject in superclasses:
        inferredSuperclasses = inferTransitiveClosure(conceptObject, {}, superclasses)[conceptObject]
        if auxQueryName in inferredSuperclasses:
            return True
    return None # Can't prove either way

## Loosely speaking: what can you use to do this action to this particular object?
def whatToolsCanPerformTaskOnObject(conceptTask, conceptPatient, usecache=True):
    if not __useMatchCache__:
        __loadUseMatchCache()
    retq = set([])
    inferredSubclassesTask = set([])
    inferredSuperclassesPatient = set([])
    conceptTask = expandName(conceptTask)
    conceptPatient = expandName(conceptPatient)
    if usecache and __dispositionSubsumptionCacheFlipped__ and (conceptTask in __dispositionSubsumptionCacheFlipped__) and __dispositionSubsumptionCache__ and (conceptPatient in __dispositionSubsumptionCache__):
        inferredSubclassesTask = inferTransitiveClosure(conceptTask, {}, __dispositionSubsumptionCacheFlipped__)[conceptTask]
        inferredSuperclassesPatient = inferTransitiveClosure(conceptPatient, {}, __dispositionSubsumptionCache__)[conceptPatient]
    elif (not usecache) or (not __dispositionSubsumptionCacheFlipped__) or (not __dispositionSubsumptionCache__):
        superclasses = runQuery("")
        subclasses = flipGraph(superclasses)
        if conceptTask in subclasses:
            inferredSubclassesTask = inferTransitiveClosure(conceptTask, {}, subclasses)[conceptTask]
        if conceptPatient in superclasses:
            inferredSuperclassesPatient = inferTransitiveClosure(conceptPatient, {}, superclasses)[conceptPatient]
    inferredSubclassesTask.add(conceptTask)
    inferredSuperclassesPatient.add(conceptPatient)
    for t in __useMatchCache__:
        if expandName(t[0], prefs=prefixesDFL) in inferredSubclassesTask:
            if expandName(t[2], prefs=prefixesDFL) in inferredSuperclassesPatient:
                conceptInstrument = expandName(t[1], prefs=prefixesDFL)
                retq = retq.union(inferTransitiveClosure(conceptInstrument, {}, __dispositionSubsumptionCacheFlipped__)[conceptInstrument])
                retq.add(conceptInstrument)
    return sorted([y for y in [contractName(x) for x in retq] if __filterApproximates(y)])

## Loosely speaking: what can you do this action to, while using this particular tool?
def whatObjectsCanToolPerformTaskOn(conceptTask, conceptInstrument, usecache=True):
    if not __useMatchCache__:
        __loadUseMatchCache()
    retq = set([])
    inferredSubclassesTask = set([])
    inferredSuperclassesInstrument = set([])
    conceptTask = expandName(conceptTask) # Trim <>, Konclude's XML does not include these
    conceptInstrument = expandName(conceptInstrument)
    if usecache and __dispositionSubsumptionCacheFlipped__ and (conceptTask in __dispositionSubsumptionCacheFlipped__) and __dispositionSubsumptionCache__ and (conceptInstrument in __dispositionSubsumptionCache__):
        inferredSubclassesTask = inferTransitiveClosure(conceptTask, {}, __dispositionSubsumptionCacheFlipped__)[conceptTask]
        inferredSuperclassesInstrument = inferTransitiveClosure(conceptInstrument, {}, __dispositionSubsumptionCache__)[conceptInstrument]
    elif (not usecache) or (not __dispositionSubsumptionCacheFlipped__) or (not __dispositionSubsumptionCache__):
        superclasses = runQuery("")
        subclasses = flipGraph(superclasses)
        if conceptTask in subclasses:
            inferredSubclassesTask = inferTransitiveClosure(conceptTask, {}, subclasses)[conceptTask]
        if conceptInstrument in superclasses:
            inferredSuperclassesInstrument = inferTransitiveClosure(conceptInstrument, {}, superclasses)[conceptInstrument]
    inferredSubclassesTask.add(conceptTask)
    inferredSuperclassesInstrument.add(conceptInstrument)
    for t in __useMatchCache__:
        if expandName(t[0], prefs=prefixesDFL) in inferredSubclassesTask:
            if expandName(t[1], prefs=prefixesDFL) in inferredSuperclassesInstrument:
                conceptPatient = expandName(t[2], prefs=prefixesDFL)
                retq = retq.union(inferTransitiveClosure(conceptPatient, {}, __dispositionSubsumptionCacheFlipped__)[conceptPatient])
                retq.add(conceptPatient)
    return sorted([y for y in [contractName(x) for x in retq] if __filterApproximates(y)])

def __runExamples__():
    print("Building cache ...")
    buildCache()
    print("... Done!")
    print("What is an aircraft?")
    print("    ", whatSuperclasses("dfl:aircraft.n.wn.artifact"))
    print("What kinds of aircraft are there?")
    print("    ", whatSubclasses("dfl:aircraft.n.wn.artifact"))
    print("What can an aircraft do?")
    print("    ", whatDispositionsDoesObjectHave("dfl:aircraft.n.wn.artifact"))
    print("What can be used to fly?")
    print("    ", whatHasDisposition("dfl:fly.v.wn.motion..assisted.Instrument"))
    print("Can an aircraft be used to fly?")
    print("    ", doesObjectHaveDisposition("dfl:aircraft.n.wn.artifact", "dfl:fly.v.wn.motion..assisted.Instrument"))
    print("Can an aircraft cut?")
    print("    ", doesObjectHaveDisposition("dfl:aircraft.n.wn.artifact", "dfl:cut.v.wn.contact..separate.Instrument"))
    print("What can cut?")
    print("    ", whatHasDisposition("dfl:cut.v.wn.contact..separate.Instrument"))
    print("What can a knife do?")
    print("    ", whatDispositionsDoesObjectHave('dfl:knife.n.wn.artifact..tool'))
    print("What can an apple do?")
    print("    ", whatDispositionsDoesObjectHave("dfl:apple.n.wn.food"))
    print("What can you cut an apple with?")
    print("    ", whatToolsCanPerformTaskOnObject('dfl:cut.v.wn.contact..separate', 'dfl:apple.n.wn.food'))
    print("What can you cut with a table knife?")
    print("    ", whatObjectsCanToolPerformTaskOn('dfl:cut.v.wn.contact..separate', 'dfl:table_knife.n.wn.artifact'))

if __name__ == "__main__":
    __runExamples__()

