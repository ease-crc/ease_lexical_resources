import os
import ast
import re
import xml.etree.ElementTree as ET

basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")

dflOWLFilename = os.path.join(basePath, "owl/SOMA_DFL.owl")
dflQueryOWLFilename = os.path.join(basePath, "owl/SOMA_DFL_query.owl")
dflResponseFilename = os.path.join(basePath, "owl/SOMA_DFL_response.owl")
owlFolder = os.path.join(basePath, "owl")
koncludeBinary = os.path.join(basePath, "bin/Konclude")

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
            retq = "<" + exp + retq + ">"
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
    retq = retq + ("Import(<file://./SOMA_DFL.owl>)\n\n")
    return retq

def inferTransitiveClosure(c, closedGraph, graph):
    closedGraph[c] = set([])
    todo = set(graph[c])
    while todo:
        sc = todo.pop()
        if sc not in closedGraph[c]:
            closedGraph[c].add(sc)
            if sc in graph:
                todo = todo.union(graph[sc])
    return closedGraph

def flipGraph(graph):
    retq = {}
    for v in graph:
        for u in graph[v]:
            if u not in retq:
                retq[u] = set([])
            retq[u].add(v)
    return retq

def runQuery(query):
    query = queryHeader() + query + "\n)\n"
    with open(dflQueryOWLFilename, "w") as outfile:
        outfile.write(query)
    os.system("cd %s && %s classification -i %s -o %s >/dev/null 2>&1" % (owlFolder, koncludeBinary, dflQueryOWLFilename, dflResponseFilename))
    xmlParse = ET.parse(dflResponseFilename)
    eqs = xmlParse.findall('{http://www.w3.org/2002/07/owl#}EquivalentClasses')
    subs = xmlParse.findall('{http://www.w3.org/2002/07/owl#}SubClassOf')
    superclasses = {}
    for eq in eqs:
        classes = [x.get('IRI') for x in eq.getchildren()]
        for c in classes:
            if c not in superclasses:
                superclasses[c] = set([])
            for d in classes:
                if c != d:
                    superclasses[c].add(d)
    for sb in subs:
        subclass, superclass = [x.get('IRI') for x in sb.getchildren()]
        if subclass not in superclasses:
            superclasses[subclass] = set([])
        superclasses[subclass].add(superclass)
    return superclasses

## Loosely speaking: what is this?
def whatSuperclasses(concept):
    concept = expandName(concept)
    superclasses = runQuery("")
    concept = concept[1:-1] # Trim <>, Konclude's XML does not include these
    inferredSuperclasses = set([])
    if concept in superclasses:
        inferredSuperclasses = inferTransitiveClosure(concept, {}, superclasses)[concept]
    return sorted(list(set([contractName(x) for x in inferredSuperclasses])))

## Loosely speaking: what kinds of this are there?
def whatSubclasses(concept):
    concept = expandName(concept)
    superclasses = runQuery("")
    subclasses = flipGraph(superclasses)
    concept = concept[1:-1] # Trim <>, Konclude's XML does not include these
    inferredSubclasses = set([])
    if concept in subclasses:
        inferredSubclasses = inferTransitiveClosure(concept, {}, subclasses)[concept]
    return sorted(list(set([contractName(x) for x in inferredSubclasses])))

## Loosely speaking: what can you do with this object?
def whatDispositionsDoesObjectHave(conceptObject):
    conceptObject = expandName(conceptObject)
    superclasses = runQuery("")
    conceptObject = conceptObject[1:-1] # Trim <>, Konclude's XML does not include these
    retq = []
    inferredSuperclasses = set([])
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
            if (expandName(conceptObjectMatch, prefs=prefixesDFL)[1:-1] in relevantConcepts):
                aux.append(expandName(conceptDisposition, prefs=prefixesDFL)[1:-1])
    bl = ["http://www.w3.org/2002/07/owl#Thing", "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#Entity", "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#Quality", "http://www.ease-crc.org/ont/SOMA.owl#Extrinsic", "http://www.ease-crc.org/ont/SOMA.owl#Disposition", "http://www.ease-crc.org/ont/SOMA.owl#PhysicalQuality", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor2", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Agent", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Asset", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Beneficiary", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Cause", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Experiencer", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Instrument", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Location", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Material", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient2", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Stimulus", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme2"]
    todo = set(aux)
    done = set()
    while todo:
        x = todo.pop()
        if (x not in done) and (x not in bl):
            done.add(x)
            retq.append(contractName(x))
            if x in superclasses:
                todo = todo.union(set(superclasses[x]))
    return sorted(list(set(retq)))

## Loosely speaking: what can do this action?
def whatHasDisposition(conceptDisposition):
    conceptDisposition = expandName(conceptDisposition)
    superclasses = runQuery("EquivalentClasses(:Query ObjectSomeValuesFrom(dul:hasQuality %s))\n" % conceptDisposition)
    aux = expandName(':Query')[1:-1] # Trim <>, Konclude's XML does not include these
    subclasses = flipGraph(superclasses)
    inferredSubclasses = []
    if aux in subclasses:
        inferredSubclasses = inferTransitiveClosure(aux, {}, subclasses)[aux]
    retq = []
    for c in superclasses.keys():
        if c in inferredSubclasses:
            retq.append(contractName(c))
    return sorted(retq)

## Loosely speaking: can this object do this action?
def doesObjectHaveDisposition(conceptObject, conceptDisposition):
    conceptObject = expandName(conceptObject)
    conceptDisposition = expandName(conceptDisposition)
    superclasses = runQuery("EquivalentClasses(:Query ObjectIntersectionOf(%s ObjectSomeValuesFrom(dul:hasQuality %s)))\n" % (conceptObject, conceptDisposition))
    auxQueryName = expandName(":Query")[1:-1] # Trim <>, Konclude's XML does not include these
    auxNothingName = expandName("owl:Nothing")[1:-1]
    conceptObject = conceptObject[1:-1]
    if auxQueryName in superclasses:
        inferredSuperclasses = inferTransitiveClosure(auxQueryName, {}, superclasses)[auxQueryName]
        if auxNothingName in inferredSuperclasses:
            return False
    if conceptObject in superclasses:
        inferredSuperclasses = inferTransitiveClosure(conceptObject, {}, superclasses)[conceptObject]
        if auxQueryName in inferredSuperclasses:
            return True
    return None # Can't prove either way

def __runExamples__():
    print("What is an aircraft?")
    print("    ", whatSuperclasses("dfl:aircraft.n.wn.artifact"))
    print("What kinds of aircraft are there?")
    print("    ", whatSubclasses("dfl:aircraft.n.wn.artifact"))
    print("What can an aircraft do?")
    print("    ", whatDispositionsDoesObjectHave("dfl:aircraft.n.wn.artifact"))
    print("What can fly?")
    print("    ", whatHasDisposition("dfl:fly.v.wn.motion.Theme"))
    print("Can an aircraft fly?")
    print("    ", doesObjectHaveDisposition("dfl:aircraft.n.wn.artifact", "dfl:fly.v.wn.motion.Theme"))
    print("Can an aircraft cut?")
    print("    ", doesObjectHaveDisposition("dfl:aircraft.n.wn.artifact", "dfl:cut.v.wn.contact.Instrument"))
    print("What can cut?")
    print("    ", whatHasDisposition("dfl:cut.v.wn.contact.Instrument"))
    print("What can a knife do?")
    print("    ", whatDispositionsDoesObjectHave("dfl:knife.n.wn.artifact"))
    print("What can an apple do?")
    print("    ", whatDispositionsDoesObjectHave("dfl:apple.n.wn.food"))

if __name__ == "__main__":
    __runExamples__()

