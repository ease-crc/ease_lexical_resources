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

class DFLReasoner:
    def __init__(self): 
        self.prefixesDFL = {
            '': 'http://www.ease-crc.org/ont/SOMA_DFL.owl#',
            'dfl': 'http://www.ease-crc.org/ont/SOMA_DFL.owl#',            
            'owl': 'http://www.w3.org/2002/07/owl#',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'xml': 'http://www.w3.org/XML/1998/namespace',
            'xsd': 'http://www.w3.org/2001/XMLSchema#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'dul': 'http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#',
            'soma': 'http://www.ease-crc.org/ont/SOMA.owl#',
            'USD': 'https://ease-crc.org/ont/USD.owl#',
            'dlquery': 'http://www.ease-crc.org/ont/DLQuery.owl#' 
            }
        self.basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "./")
        self.defaultModuleFilename = os.path.join(self.basePath, "owl/SOMA_DFL_module.owl")
        self.dflOWLFilename = os.path.join(self.basePath, "owl/SOMA_DFL.owl")
        self.dflQueryOWLFilename = os.path.join(self.basePath, "owl/SOMA_DFL_query.owl")
        self.dflResponseFilename = os.path.join(self.basePath, "owl/SOMA_DFL_response.owl")
        self.owlFolder = os.path.join(self.basePath, "owl")
        self.resourcesFolder = os.path.join(self.basePath, "resources")
        self.dflUseMatchFilename = os.path.join(self.resourcesFolder, "DFLUseMatch.res")
        self.dflHasPartFilename = os.path.join(self.resourcesFolder, "DFLHasPart.res")
        self.dflConsistsOfFilename = os.path.join(self.resourcesFolder, "DFLConsistsOf.res")
        self.koncludeBinary = os.path.join(self.basePath, "bin/Konclude")
        if "Windows" == platform.system():
            self.koncludeBinary = os.path.join(self.basePath, "bin/Konclude.exe")
        if not os.path.isfile(self.koncludeBinary):
            self.koncludeBinary = os.environ.get("KONCLUDE_PATH")
        if self.koncludeBinary is None:
            self.koncludeBinary = shutil.which("Konclude") or shutil.which("konclude")
        if self.koncludeBinary is None:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "konclude")
        self.__dispositionSubsumptionCache__ = None
        self.__dispositionSubsumptionCacheFlipped__ = None
        self.__useMatchCache__ = None
        self.partMap = {}
        self.invPartMap = {}
        self.__initPartsAndConstituents()
        self.__loadUseMatchCache()
    def __initPartsAndConstituents(self):
        self.partMap = {}
        self.invPartMap = {}
        for l in open(self.dflHasPartFilename).read().splitlines():
            l = ast.literal_eval(l)
            k, v = self.expandName("dfl:"+l[0]), self.expandName("dfl:"+l[1])
            if k not in self.partMap:
                self.partMap[k] = set()
            self.partMap[k].add(v)
            if v not in self.invPartMap:
                self.invPartMap[v] = set()
            self.invPartMap[v].add(k)
        self.constituentMap = {}
        self.invConstituentMap = {}
        for l in open(self.dflConsistsOfFilename).read().splitlines():
            l = ast.literal_eval(l)
            k, v = self.expandName("dfl:"+l[0]), self.expandName("dfl:"+l[1])
            if k not in self.constituentMap:
                self.constituentMap[k] = set()
            self.constituentMap[k].add(v)
            if v not in self.invConstituentMap:
                self.invConstituentMap[v] = set()
            self.invConstituentMap[v].add(k)
    def __loadUseMatchCache(self):
        self.__useMatchCache__ = [tuple([self.expandName('dfl:'+y) for y in ast.literal_eval(x)]) for x in open(self.dflUseMatchFilename).read().splitlines() if x.strip()]
    def expandName(self, conceptName, prefs=None):
        if None == prefs:
            prefs = self.prefixesDFL
        if ('://' in conceptName) or (':' not in conceptName):
            return conceptName
        prefix = conceptName[:conceptName.find(':')]
        suffix = conceptName[conceptName.find(':') + 1:]
        retq = prefs[prefix] + suffix
        return retq
    def contractName(self, conceptName, prefs=None):
        if None == prefs:
            prefs = self.prefixesDFL
        for p, exp in prefs.items():
            if conceptName.startswith(exp):
                return p + ":" + conceptName[len(exp):]
        return conceptName
    def queryHeader(self):
        retq = ""
        for p, exp in self.prefixesDFL.items():
            retq = retq + ("Prefix(%s:=<%s>)\n" % (p, exp))
        retq = retq + ("Ontology(<http://www.ease-crc.org/ont/DLQuery.owl>\n")
        retq = retq + ("Import(<file://%s>)\n\n" % os.path.abspath(self.dflOWLFilename).replace("\\","/"))
        return retq
    def inferTransitiveClosure(self, c, closedGraph, graph, ignoreConcepts=None):
        if ignoreConcepts is None:
            ignoreConcepts = set()
        todo = set(graph.get(c,[]))
        closedGraph[c] = set([])
        while todo:
            sc = todo.pop()
            if (sc not in closedGraph[c]) and (sc not in ignoreConcepts):
                closedGraph[c].add(sc)
                if sc in graph:
                    todo = todo.union(graph[sc])
        return closedGraph
    def flipGraph(self, graph):
        retq = {}
        for v in graph:
            if v not in retq:
                retq[v] = set([])
            for u in graph[v]:
                if u not in retq:
                    retq[u] = set([])
                retq[u].add(v)
        return retq
    def parseResponse(self, filename):
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
    def runQuery(self, query):
        query = self.queryHeader() + query + "\n)\n"
        with open(self.dflQueryOWLFilename, "w") as outfile:
            outfile.write(query)
        os.system("cd %s && \"%s\" classification -i \"%s\" -o \"%s\" %s" % (self.owlFolder, self.koncludeBinary, self.dflQueryOWLFilename, self.dflResponseFilename, blackHole))
        return self.parseResponse(self.dflResponseFilename)
    def initializeOntology(self, ontologyFile=None, useMatchFile=None, partsFile=None, constituentsFile=None):
        if ontologyFile is None:
            ontologyFile = self.defaultModuleFilename
        if useMatchFile is None:
            useMatchFile = self.dflUseMatchFilename
        if partsFile is None:
            partsFile = self.dflHasPartFilename
        if constituentsFile is None:
            constituentsFile = self.dflConsistsOfFilename
        self.setOntologyFiles(ontologyFile, useMatchFile, partsFile, constituentsFile)
        self.buildCache()
    def setOntologyFiles(self, ontologyFile, useMatchFile, partsFile, constituentsFile):
        self.dflOWLFilename = os.path.abspath(ontologyFile)
        self.dflUseMatchFilename = os.path.abspath(useMatchFile)
        self.dflHasPartFilename = os.path.abspath(partsFile)
        self.dflConsistsOfFilename = os.path.abspath(constituentsFile)
        self.__dispositionSubsumptionCache__ = None
        self.__dispositionSubsumptionCacheFlipped__ = None
        self.__initPartsAndConstituents()
        self.__loadUseMatchCache()
    def __getQueryName(self, conceptName):
        return conceptName + ".QUERY"
    def __isQueryConcept(self, conceptName):
        #return conceptName.startswith('http://www.ease-crc.org/ont/DLQuery.owl#') and conceptName.endswith('.QUERY')
        return conceptName.endswith('.QUERY')
    def __filterApproximates(self, conceptName):
        conceptName = self.expandName(conceptName)
        if (conceptName.startswith("http://www.ease-crc.org/ont/SOMA_DFL.owl#Approximate")):
            return None
        return conceptName
    def buildCache(self):
        superclasses = self.runQuery("")
        subclasses = self.flipGraph(superclasses)
        dispositionConcept = self.expandName("soma:Disposition")
        dispositionTClosure = self.inferTransitiveClosure(dispositionConcept, {}, subclasses)[dispositionConcept]
        query = ""
        for c in dispositionTClosure:
            c = self.expandName(c)
            query = query + ("EquivalentClasses(<%s> ObjectSomeValuesFrom(dul:hasQuality <%s>))\n" % (self.__getQueryName(c), c))
        self.__dispositionSubsumptionCache__ = self.runQuery(query)
        self.__dispositionSubsumptionCacheFlipped__ = self.flipGraph(self.__dispositionSubsumptionCache__)
    def whatsImpossible(self, usecache=True):
        retq = set()
        nothing = self.expandName("owl:Nothing")
        if usecache and self.__dispositionSubsumptionCache__:
            superclasses = self.__dispositionSubsumptionCache__
        else:
            superclasses = self.runQuery("")
        return sorted([y for y in [self.contractName(x) for x in superclasses.keys() if nothing in superclasses[x]] if self.__filterApproximates(y)])
    ## Loosely speaking: what is this?
    def whatSuperclasses(self, concept, usecache=True):
        concept = self.expandName(concept)
        inferredSuperclasses = set([])
        if usecache and self.__dispositionSubsumptionCache__ and (concept in self.__dispositionSubsumptionCache__):
            inferredSuperclasses = self.inferTransitiveClosure(concept, {}, self.__dispositionSubsumptionCache__)[concept]
        elif (not usecache) or (not self.__dispositionSubsumptionCache__):
            superclasses = self.runQuery("")
            if concept in superclasses:
                inferredSuperclasses = self.inferTransitiveClosure(concept, {}, superclasses)[concept]
        return sorted([y for y in list(set([self.contractName(x) for x in inferredSuperclasses if (not self.__isQueryConcept(x))])) if self.__filterApproximates(y)])
    ## Loosely speaking: what kinds of this are there?
    def whatSubclasses(self, concept, usecache=True):
        concept = self.expandName(concept)
        inferredSubclasses = set([])
        if usecache and self.__dispositionSubsumptionCacheFlipped__ and (concept in self.__dispositionSubsumptionCacheFlipped__):
            inferredSubclasses = self.inferTransitiveClosure(concept, {}, self.__dispositionSubsumptionCacheFlipped__)[concept]
        elif (not usecache) or (not self.__dispositionSubsumptionCacheFlipped__):
            subclasses = self.flipGraph(self.runQuery(""))
            if concept in subclasses:
                inferredSubclasses = self.inferTransitiveClosure(concept, {}, subclasses)[concept]
        return sorted([y for y in list(set([self.contractName(x) for x in inferredSubclasses if (not self.__isQueryConcept(x))])) if self.__filterApproximates(y)])
    def isSubclassOf(self, subclass, superclass, usecache=True):
        subclass = self.expandName(subclass)
        subclasses = [self.expandName(x) for x in self.whatSubclasses(superclass, usecache=usecache)]
        return subclass in subclasses
    def whatsEquivalent(self, concept, usecache=True):
        sups=self.whatSuperclasses(concept, usecache=usecache)
        subs=self.whatSubclasses(concept, usecache=usecache)
        return sorted(list(set(sups).intersection(subs)))
    ## Loosely speaking: what hasPart relationships are known for this object?
    def whatPartTypesDoesObjectHave(self, concept, usecache=True):
        superclasses = self.whatSuperclasses(concept, usecache=usecache)
        partTypes = set(itertools.chain.from_iterable([self.partMap.get(self.expandName(x), []) for x in superclasses]))
        return sorted(list(partTypes))
    def whatHasPartType(self, concept, usecache=True):
        subclasses = self.whatSubclasses(concept, usecache=usecache)
        objectTypes = set(itertools.chain.from_iterable([self.invPartMap.get(self.expandName(x), []) for x in subclasses]))
        return sorted(list(objectTypes))
    def whatConstituentsDoesObjectHave(self, concept, usecache=True):
        superclasses = self.whatSuperclasses(concept, usecache=usecache)
        constituentTypes = set(itertools.chain.from_iterable([self.constituentMap.get(self.expandName(x), []) for x in superclasses]))
        return sorted(list(constituentTypes))
    def whatHasConstituent(self, concept, usecache=True):
        subclasses = self.whatSubclasses(concept, usecache=usecache)
        objectTypes = set(itertools.chain.from_iterable([self.invConstituentMap.get(self.expandName(x), []) for x in subclasses]))
        return sorted(list(objectTypes))
    ## Loosely speaking: what can do this action?
    def whatHasDisposition(self, conceptDisposition, usecache=True):
        retq = []
        inferredSubclasses = set([])
        conceptDisposition = self.expandName(conceptDisposition)
        queryDisposition = self.__getQueryName(conceptDisposition)
        aux = self.expandName(queryDisposition)
        if usecache and self.__dispositionSubsumptionCacheFlipped__ and (aux in self.__dispositionSubsumptionCacheFlipped__):
            inferredSubclasses = self.inferTransitiveClosure(aux, {}, self.__dispositionSubsumptionCacheFlipped__)[aux]
        elif (not usecache) or (not self.__dispositionSubsumptionCacheFlipped__):
            subclasses = self.flipGraph(self.runQuery("EquivalentClasses(<%s> ObjectSomeValuesFrom(dul:hasQuality <%s>))\n" % (queryDisposition, conceptDisposition)))
            if aux in subclasses:
                inferredSubclasses = self.inferTransitiveClosure(aux, {}, subclasses)[aux]
        return sorted([y for y in list(set([self.contractName(x) for x in inferredSubclasses if (not self.__isQueryConcept(x))])) if self.__filterApproximates(y)])
    ## Loosely speaking: what can you do with this object?
    def whatDispositionsDoesObjectHave(self, conceptObject, usecache=True):
        conceptObject = self.expandName(conceptObject)
        retq = []
        inferredSuperclasses = set([])
        bl = ["http://www.w3.org/2002/07/owl#Thing", "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#Entity", "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#Quality", "http://www.ease-crc.org/ont/SOMA.owl#Extrinsic", "http://www.ease-crc.org/ont/SOMA.owl#Disposition", "http://www.ease-crc.org/ont/SOMA.owl#PhysicalQuality", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Actor2", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Agent", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Asset", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Beneficiary", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Cause", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Experiencer", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Instrument", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Location", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Material", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Patient2", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Stimulus", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme1", "http://www.ease-crc.org/ont/SOMA_DFL.owl#disposition.Theme2"]
        if usecache and self.__dispositionSubsumptionCache__ and (conceptObject in self.__dispositionSubsumptionCache__):
            inferredSuperclasses = [x.rstrip('.QUERY') for x in self.inferTransitiveClosure(conceptObject, {}, self.__dispositionSubsumptionCache__)[conceptObject] if self.__isQueryConcept(x)]
            retq = [y for y in [self.contractName(x) for x in inferredSuperclasses] if self.expandName(y) not in bl]
        elif (not usecache) or (not self.__dispositionSubsumptionCache__):
            superclasses = self.runQuery("")
            if conceptObject in superclasses:
                inferredSuperclasses = self.inferTransitiveClosure(conceptObject, {}, superclasses)[conceptObject]
            relevantConcepts = inferredSuperclasses.union(set([conceptObject]))
            lines = [x for x in open(self.dflOWLFilename).read().splitlines() if x.strip()]
            aux = []
            for l in lines:
                m = re.search("^SubClassOf\\((?P<object>[a-zA-Z0-9\\-_:,./#\\<\\>\\+\\*]+) ObjectSomeValuesFrom\\(dul:hasQuality (?P<disposition>[a-zA-Z0-9\\-_:,./#\\<\\>\\+\\*]+)\\)\\)$", l)
                if m:
                    conceptObjectMatch = m.group('object')
                    conceptDisposition = m.group('disposition')
                    if (self.expandName(conceptObjectMatch) in relevantConcepts):
                        aux.append(self.expandName(conceptDisposition))
            superclasses[conceptObject] = set(aux)
            inferredSuperclasses = self.inferTransitiveClosure(conceptObject, {}, superclasses, ignoreConcepts=bl)[conceptObject]
            retq = sorted(list(set([self.contractName(x) for x in inferredSuperclasses if (not self.__isQueryConcept(x))])))
            #todo = set(aux)
            #done = set()
            #while todo:
            #    x = todo.pop()
            #    if (x not in done) and (x not in bl):
            #        done.add(x)
            #        retq.append(self.contractName(x))
            #        if x in superclasses:
            #            todo = todo.union(set(superclasses[x]))
        return sorted([y for y in list(set(retq)) if self.__filterApproximates(y)])
    ## Loosely speaking: can this object do this action?
    # TODO: find a way to cache this. The "True" branch is cacheable, but proving an item cannot be used in some given way requires a new subsumption query
    def doesObjectHaveDisposition(self, conceptObject, conceptDisposition):
        conceptObject = self.expandName(conceptObject)
        conceptDisposition = self.expandName(conceptDisposition)
        superclasses = self.runQuery("EquivalentClasses(dlquery:Query ObjectIntersectionOf(<%s> ObjectSomeValuesFrom(dul:hasQuality <%s>)))\n" % (conceptObject, conceptDisposition))
        auxQueryName = self.expandName("dlquery:Query")
        auxNothingName = self.expandName("owl:Nothing")
        if auxQueryName in superclasses:
            inferredSuperclasses = self.inferTransitiveClosure(auxQueryName, {}, superclasses)[auxQueryName]
            if auxNothingName in inferredSuperclasses:
                return False
        if conceptObject in superclasses:
            inferredSuperclasses = self.inferTransitiveClosure(conceptObject, {}, superclasses)[conceptObject]
            if auxQueryName in inferredSuperclasses:
                return True
        return None # Can't prove either way
    ## Loosely speaking: what can you use to do this action to this particular object?
    def whatToolsCanPerformTaskOnObject(self, conceptTask, conceptPatient, usecache=True):
        retq = set([])
        inferredSubclassesTask = set([])
        inferredSuperclassesPatient = set([])
        conceptTask = self.expandName(conceptTask)
        conceptPatient = self.expandName(conceptPatient)
        inferredSubclassesTask = self.whatSubclasses(conceptTask) + ([conceptTask])
        inferredSuperclassesPatient = self.whatSuperclasses(conceptPatient) + ([conceptPatient])
        inferredSubclassesTask = set([self.expandName(x) for x in inferredSubclassesTask])
        inferredSuperclassesPatient = set([self.expandName(x) for x in inferredSuperclassesPatient])
        for t in self.__useMatchCache__:
            if self.expandName(t[0]) in inferredSubclassesTask:
                if self.expandName(t[2]) in inferredSuperclassesPatient:
                    conceptInstrument = self.expandName(t[1])
                    retq = retq.union(self.inferTransitiveClosure(conceptInstrument, {}, self.__dispositionSubsumptionCacheFlipped__)[conceptInstrument])
                    retq.add(conceptInstrument)
        return sorted([y for y in [self.contractName(x) for x in retq] if self.__filterApproximates(y)])
    ## Loosely speaking: what can you do this action to, while using this particular tool?
    def whatObjectsCanToolPerformTaskOn(self, conceptTask, conceptInstrument, usecache=True):
        retq = set([])
        inferredSubclassesTask = set([])
        inferredSuperclassesInstrument = set([])
        conceptTask = self.expandName(conceptTask)
        conceptInstrument = self.expandName(conceptInstrument)
        #if usecache and self.__dispositionSubsumptionCacheFlipped__ and (conceptTask in self.__dispositionSubsumptionCacheFlipped__) and self.__dispositionSubsumptionCache__ and (conceptInstrument in self.__dispositionSubsumptionCache__):
        #    inferredSubclassesTask = self.inferTransitiveClosure(conceptTask, {}, self.__dispositionSubsumptionCacheFlipped__)[conceptTask]
        #    inferredSuperclassesInstrument = self.inferTransitiveClosure(conceptInstrument, {}, self.__dispositionSubsumptionCache__)[conceptInstrument]
        #elif (not usecache) or (not self.__dispositionSubsumptionCacheFlipped__) or (not self.__dispositionSubsumptionCache__):
        #    superclasses = self.runQuery("")
        #    subclasses = self.flipGraph(superclasses)
        #    if conceptTask in subclasses:
        #        inferredSubclassesTask = self.inferTransitiveClosure(conceptTask, {}, subclasses)[conceptTask]
        #    if conceptInstrument in superclasses:
        #        inferredSuperclassesInstrument = self.inferTransitiveClosure(conceptInstrument, {}, superclasses)[conceptInstrument]
        inferredSubclassesTask = self.whatSubclasses(conceptTask) + ([conceptTask])
        inferredSuperclassesInstrument = self.whatSuperclasses(conceptPatient) + ([conceptInstrument])
        inferredSubclassesTask = set([self.expandName(x) for x in inferredSubclassesTask])
        inferredSuperclassesInstrument = set([self.expandName(x) for x in inferredSuperclassesInstrument])
        for t in self.__useMatchCache__:
            if self.expandName(t[0]) in inferredSubclassesTask:
                if self.expandName(t[1]) in inferredSuperclassesInstrument:
                    conceptPatient = self.expandName(t[2])
                    retq = retq.union(self.inferTransitiveClosure(conceptPatient, {}, self.__dispositionSubsumptionCacheFlipped__)[conceptPatient])
                    retq.add(conceptPatient)
        return sorted([y for y in [self.contractName(x) for x in retq] if self.__filterApproximates(y)])

defaultReasoner = DFLReasoner()

def expandName(conceptName, prefs=None):
    return defaultReasoner.expandName(conceptName, prefs=prefs)

def contractName(conceptName, prefs=None):
    return defaultReasoner.contractName(conceptName, prefs=prefs)

def initializeOntology(ontologyFile=None, useMatchFile=None, partsFile=None, constituentsFile=None):
    return defaultReasoner.initializeOntology(ontologyFile=ontologyFile, useMatchFile=useMatchFile, partsFile=partsFile, constituentsFile=constituentsFile)
    
def setOntologyFiles(ontologyFile, useMatchFile, partsFile, constituentsFile):
    return defaultReasoner.setOntologyFiles(ontologyFile, useMatchFile, partsFile, constituentsFile)

def buildCache():
    return defaultReasoner.buildCache()

def whatsImpossible(usecache=True):
    return defaultReasoner.whatsImpossible(usecache=usecache)
    
## Loosely speaking: what is this?
def whatSuperclasses(concept, usecache=True):
    return defaultReasoner.whatSuperclasses(concept, usecache=usecache)

## Loosely speaking: what kinds of this are there?
def whatSubclasses(concept, usecache=True):
    return defaultReasoner.whatSubclasses(concept, usecache=usecache)

def isSubclassOf(subclass, superclass, usecache=True):
    return defaultReasoner.isSubclassOf(subclass, superclass, usecache=usecache)

def whatsEquivalent(concept, usecache=True):
    return defaultReasoner.whatsEquivalent(concept, usecache=True)

## Loosely speaking: what hasPart relationships are known for this object?
def whatPartTypesDoesObjectHave(concept, usecache=True):
    return defaultReasoner.whatPartTypesDoesObjectHave(concept, usecache=usecache)

def whatHasPartType(concept, usecache=True):
    return defaultReasoner.whatHasPartType(concept, usecache=usecache)

def whatConstituentsDoesObjectHave(concept, usecache=True):
    return defaultReasoner.whatConstituentsDoesObjectHave(concept, usecache=usecache)

def whatHasConstituent(concept, usecache=True):
    return defaultReasoner.whatHasConstituent(concept, usecache=usecache)

## Loosely speaking: what can do this action?
def whatHasDisposition(conceptDisposition, usecache=True):
    return defaultReasoner.whatHasDisposition(conceptDisposition, usecache=usecache)

## Loosely speaking: what can you do with this object?
def whatDispositionsDoesObjectHave(conceptObject, usecache=True):
    return defaultReasoner.whatDispositionsDoesObjectHave(conceptObject, usecache=usecache)

## Loosely speaking: can this object do this action?
def doesObjectHaveDisposition(conceptObject, conceptDisposition):
    return defaultReasoner.doesObjectHaveDisposition(conceptObject, conceptDisposition)

## Loosely speaking: what can you use to do this action to this particular object?
def whatToolsCanPerformTaskOnObject(conceptTask, conceptPatient, usecache=True):
    return defaultReasoner.whatToolsCanPerformTaskOnObject(conceptTask, conceptPatient, usecache=usecache)

## Loosely speaking: what can you do this action to, while using this particular tool?
def whatObjectsCanToolPerformTaskOn(conceptTask, conceptInstrument, usecache=True):
    return defaultReasoner.whatObjectsCanToolPerformTaskOn(conceptTask, conceptInstrument, usecache=usecache)

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

