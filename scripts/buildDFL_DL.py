import os
import ast
import sys
import progressbar
import platform
import shutil

blackHole = ">/dev/null 2>&1"
if "Windows" == platform.system():
    blackHole = " > NUL"

pbar = None
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

# How to map roles from one verb to another, ordered by preference
"""
roleMap = {
    'Actor': ['Actor', 'Agent', 'Experiencer', 'Actor1', 'Actor2', 'Cause', 'Stimulus'],
    'Actor1': ['Actor1', 'Actor', 'Agent', 'Experiencer', 'Actor2', 'Cause', 'Stimulus'],
    'Actor2': ['Actor2', 'Actor', 'Agent', 'Experiencer', 'Actor1', 'Cause', 'Stimulus'],
    'Agent': ['Agent', 'Actor', 'Experiencer', 'Actor1', 'Actor2', 'Cause', 'Stimulus'],
    'Asset': ['Asset', 'Material', 'Theme', 'Theme1', 'Theme2', 'Patient', 'Patient1', 'Patient2'],
    'Attribute': ['Attribute'],
    'Beneficiary': ['Beneficiary'],
    'Cause': ['Cause', 'Agent', 'Actor', 'Stimulus', 'Actor1', 'Actor2'],
    'Experiencer': ['Experiencer', 'Agent', 'Actor', 'Actor1', 'Actor2'],
    'Instrument': ['Instrument', 'Theme', 'Theme1', 'Theme2'],
    'Location': ['Location'],
    'Material': ['Material', 'Theme', 'Theme1', 'Theme2', 'Asset'],
    'Patient': ['Patient', 'Patient1', 'Patient2', 'Material', 'Theme', 'Theme1', 'Theme2', 'Asset'],
    'Patient1': ['Patient1', 'Patient', 'Patient2', 'Material', 'Theme1', 'Theme', 'Theme2', 'Asset'],
    'Patient2': ['Patient2', 'Patient', 'Patient1', 'Material', 'Theme2', 'Theme', 'Theme1', 'Asset'],
    'Stimulus': ['Stimulus', 'Cause', 'Agent', 'Actor', 'Actor1', 'Actor2'],
    'Theme': ['Theme', 'Theme1', 'Theme2', 'Patient', 'Patient1', 'Patient2', 'Instrument', 'Material', 'Asset'],
    'Theme1': ['Theme1', 'Theme', 'Theme2', 'Patient1', 'Patient', 'Patient2', 'Instrument', 'Material', 'Asset'],
    'Theme2': ['Theme2', 'Theme', 'Theme1', 'Patient2', 'Patient', 'Patient1', 'Instrument', 'Material', 'Asset'],
}
"""
roleMap = {
    'Actor': ['Actor', 'Agent', 'Experiencer', 'Actor1', 'Actor2', 'Cause', 'Stimulus'],
    'Actor1': ['Actor1', 'Actor', 'Agent', 'Experiencer', 'Actor2', 'Cause', 'Stimulus'],
    'Actor2': ['Actor2', 'Actor', 'Agent', 'Experiencer', 'Actor1', 'Cause', 'Stimulus'],
    'Agent': ['Agent', 'Actor', 'Experiencer', 'Actor1', 'Actor2', 'Cause', 'Stimulus'],
    'Beneficiary': ['Beneficiary'],
    'Cause': ['Cause', 'Agent', 'Actor', 'Stimulus', 'Actor1', 'Actor2'],
    'Experiencer': ['Experiencer', 'Agent', 'Actor', 'Actor1', 'Actor2'],
    'Instrument': ['Instrument', 'Theme', 'Theme1', 'Theme2'],
    'Location': ['Location'],
    'Material': ['Patient'],
    'Patient': ['Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2'],
    'Patient1': ['Patient1', 'Patient', 'Patient2', 'Theme1', 'Theme', 'Theme2'],
    'Patient2': ['Patient2', 'Patient', 'Patient1', 'Theme2', 'Theme', 'Theme1'],
    'Stimulus': ['Stimulus', 'Cause', 'Agent', 'Actor', 'Actor1', 'Actor2'],
    'Theme': ['Theme', 'Theme1', 'Theme2', 'Patient', 'Patient1', 'Patient2', 'Instrument'],
    'Theme1': ['Theme1', 'Theme', 'Theme2', 'Patient1', 'Patient', 'Patient2', 'Instrument'],
    'Theme2': ['Theme2', 'Theme', 'Theme1', 'Patient2', 'Patient', 'Patient1', 'Instrument'],
}

# Define paths for accessing the various important files.
basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
objectTaxonomyFilename = os.path.join(basePath, "resources/ObjectTaxonomy.res")
partonomyFilename = os.path.join(basePath, "resources/DFLHasPart.res")
consistsOfFilename = os.path.join(basePath, "resources/DFLConsistsOf.res")
verbTaxonomyFilename = os.path.join(basePath, "resources/VerbTaxonomy.res")
capableOfFilename = os.path.join(basePath, "resources/DFLCapableOf.res")
usedForFilename = os.path.join(basePath, "resources/DFLUsedFor.res")
useMatchFilename = os.path.join(basePath, "resources/DFLUseMatch.res")
vnthemrolesFilename = os.path.join(basePath, "resources/vnthemroles.res")
vntriplesFilename = os.path.join(basePath, "resources/DFLHasVNVC.res")
somaAlignmentsFilename = os.path.join(basePath, "resources/SOMAAlignments.res")
seedIniFilename = os.path.join(basePath, "resources/SOMA_DFL_seed_ini.res")
seedFilename = os.path.join(basePath, "owl/SOMA_DFL_seed.owl")
dflOWLFilename = os.path.join(basePath, "owl/SOMA_DFL.owl")
dflQueryOWLFilename = os.path.join(basePath, "owl/SOMA_DFL_query.owl")
dflResponseFilename = os.path.join(basePath, "owl/SOMA_DFL_response.owl")
owlFolder = os.path.join(basePath, "owl")
koncludeBinary = os.path.join(basePath, "bin/Konclude")

# Read the resources (object and verb taxonomy; disposition triples)
def loadObjectTaxonomy(objectTaxonomyFilename):
    isas = [ast.literal_eval(x) for x in open(objectTaxonomyFilename).read().splitlines() if x.strip()]
    concs = set([])
    for t in isas:
        concs.add(t[0])
        concs.add(t[1])
    subclasses = {}
    superclasses = {}
    tops = set()
    for t in isas:
        if t[0] not in superclasses:
            superclasses[t[0]] = set([])
        superclasses[t[0]].add(t[1])
    subclasses = {}
    for t in isas:
        if t[1] not in subclasses:
            subclasses[t[1]] = set([])
        subclasses[t[1]].add(t[0])
    for c in concs:
        if c not in superclasses:
            tops.add(c)
    return concs, isas, superclasses, subclasses, tops

def getVerbData(verbTaxonomyFilename, vntriplesFilename, vnthemrolesFilename):
    def tuplify(x):
        #{'': [('+', 'animate')], 'op': 'and'}
        if isinstance(x,dict):
            if ('op' in x) and ('or' == x['op']):
                x = tuple(['U'] + [tuplify(y) for y in x['']])
            else:
                x = tuple(['^'] + [tuplify(y) for y in x['']])
            if 2 == len(x):
                x = x[1]
        return x
    vnTriples = [ast.literal_eval(x) for x in open(vntriplesFilename).read().splitlines() if x.strip()]
    themroles = [ast.literal_eval(x) for x in open(vnthemrolesFilename).read().splitlines() if x.strip()]
    themroles = {x[0]: {k: tuplify(v) for k,v in x[1].items()} for x in themroles}
    vnMap = {}
    for t in vnTriples:
        if t[0] not in vnMap:
            vnMap[t[0]] = set([])
        vnMap[t[0]].add(t[1])
    visas = [ast.literal_eval(x) for x in open(verbTaxonomyFilename).read().splitlines() if x.strip()]
    visas = [x for x in visas if (x[0] in vnMap) and (x[1] in vnMap)]
    vsuperclasses = {}
    for t in visas:
        if t[0] not in vsuperclasses:
            vsuperclasses[t[0]] = set([])
        if t[1] not in vsuperclasses:
            vsuperclasses[t[1]] = set([])
        vsuperclasses[t[0]].add(t[1])
    rolesList = {}
    for v in vnMap.keys():
        aux = []
        for vn in vnMap[v]:
            aux = aux + list(themroles[vn].keys())
        aux = set(aux)
        rolesList[v] = aux
        if v not in vsuperclasses:
            vsuperclasses[v] = set([])
    return visas, vsuperclasses, vnTriples, vnMap, themroles, rolesList

def getPropTriples(capableOfFilename, usedForFilename, useMatchFilename, concs, vnMap):
    cotriples = [ast.literal_eval(x) for x in open(capableOfFilename).read().splitlines() if x.strip()]
    uftriples = [ast.literal_eval(x) for x in open(usedForFilename).read().splitlines() if x.strip()]
    umtriples = [ast.literal_eval(x) for x in open(useMatchFilename).read().splitlines() if x.strip()]
    for t in umtriples:
        cotriples.append((t[2], t[0]))
        uftriples.append((t[1], t[0]))
    cotriples = list(set(cotriples))
    uftriples = list(set(uftriples))
    cotriples = [x for x in cotriples if (x[0] in concs) and (x[1] in vnMap)]
    uftriples = [x for x in uftriples if (x[0] in concs) and (x[1] in vnMap)]
    return cotriples, uftriples, umtriples
    
def writeEquivalenceAxiom(d):
    a, b = ast.literal_eval(d)
    return "EquivalentClasses(%s %s)" % (a, b)

seedIniLines = [x for x in open(seedIniFilename).read().splitlines()][:-1]
seedIniLines = seedIniLines + [writeEquivalenceAxiom(x) for x in open(somaAlignmentsFilename).read().splitlines() if x.strip()]
concs, isas, superclasses, subclasses, tops = loadObjectTaxonomy(objectTaxonomyFilename)
visas, vsuperclasses, vnTriples, vnMap, themroles, rolesList = getVerbData(verbTaxonomyFilename, vntriplesFilename, vnthemrolesFilename)
# TODO: at some point, generate code in the OWL from the useMatch triples. 
#     Currently, for efficiency reasons, a simpler procedure queries the useMatch file directly and augments the results using sub/superclasses of concepts as found by OWL reasoning.
#     This avoids the need for an OWL reasoner for the use match queries themselves, at least with the current structure of the ontology.
cotriples, uftriples, _ = getPropTriples(capableOfFilename, usedForFilename, useMatchFilename, concs, vnMap)

verbs = set([])
for t in cotriples + uftriples:
    verbs.add(t[1])
aux = set([])
for v in verbs:
    if v in vsuperclasses:
        for sv in vsuperclasses[v]:
            aux.add(sv)
verbs = verbs.union(aux)

def dnfRoleDesc(roleDesc):
    def isAtom(r):
        return isinstance(r,tuple) and (r[0] in ['-','+'])
    def isConjunction(r):
        return isinstance(r,tuple) and ('^' == r[0])
    def isDisjunction(r):
        return isinstance(r,tuple) and ('U' == r[0])
    def sortedSet(r):
        return sorted(list(set(r)))
    if (not isAtom(roleDesc)):
        roleDesc = tuple([roleDesc[0]]+sortedSet(roleDesc[1:]))
        if (2 == len(roleDesc)):
            roleDesc = roleDesc[1]
        else:
            data = [dnfRoleDesc(x) for x in roleDesc[1:]]
            if isConjunction(roleDesc):
                auxSimple = []
                auxComplex = []
                for e in data:
                    if isDisjunction(e):
                        auxComplex.append(list(e[1:]))
                    elif isConjunction(e):
                        auxSimple = auxSimple + list(e[1:])
                    else:
                        auxSimple.append(e)
                if not auxComplex:
                    roleDesc = tuple(['^']+sortedSet(auxSimple))
                else:
                    aux = []
                    for x in itertools.product(*auxComplex):
                        y = []
                        for e in x:
                            if isConjunction(e):
                                y = y + list(e[1:])
                            else:
                                y.append(e)
                        aux.append(tuple(['^']+sortedSet(y+auxSimple)))
                    roleDesc = tuple(['U']+sortedSet(aux))
            else: #isDisjunction(roleDesc)
                aux = []
                for e in data:
                    if isDisjunction(e):
                        aux = aux + list(e[1:])
                    else:
                        aux.append(e)
                roleDesc = tuple(['U']+sortedSet(aux))
    return roleDesc

def postProcRoleDesc(rd):
    ##    ('refl', '+'): ignore
    ##    -region: ignore
    if not rd:
        return ()
    if rd[0] not in ['U','^']:
        if rd in [('-','region'), ('+','refl')]:
            return ()
    else:
        aux = [y for y in [postProcRoleDesc(x) for x in rd[1:]] if y]
        if 1 < len(aux):
            rd = tuple([rd[0]]+aux)
        elif 1 == len(aux):
            rd = aux[0]
        else:
            rd = ()
    return rd

def getDLString(roleDesc, complementMap=None):
    if not roleDesc:
        return ""
    if '-' == roleDesc[0]:
        if complementMap and (roleDesc in complementMap):
            return ":"+complementMap[roleDesc]
        return ("ObjectComplementOf(:%s)" % roleDesc[1])
    elif roleDesc[0] in ['U', '^']:
        if 'U' == roleDesc[0]:
            retq = "ObjectUnionOf("
        else:
            retq = "ObjectIntersectionOf("
        for e in roleDesc[1:]:
            retq = retq + getDLString(e, complementMap=complementMap) + ' '
        return retq[:-1] + ")"
    return ':' + roleDesc[1]

def getVerb2RolesMap(vnMap, themroles):
    def getComplements(rd):
        retq = set([])
        if not rd:
            return set([])
        if rd[0] in ['U','^']:
            for e in rd[1:]:
                retq = retq.union(getComplements(e))
        else:
            if '-' == rd[0]:
                retq = set([rd])
        return retq
    retq = {}
    v2RD = {}
    selrestrs = set([])
    complements = set([])
    for v in vnMap:
        retq[v] = set([])
        for vnc in vnMap[v]:
            retq[v] = retq[v].union(list(themroles[vnc].keys()))
        v2RD[v] = {}
        for r in retq[v]:
            aux = ['U']
            for vnc in vnMap[v]:
                if r in themroles[vnc]:
                    aux.append(themroles[vnc][r])
            v2RD[v][r] = postProcRoleDesc(dnfRoleDesc(tuple(aux)))  
    for v in v2RD:
        for r in v2RD[v]:
            if v2RD[v][r]:
                selrestrs.add(v2RD[v][r])
                complements = complements.union(getComplements(v2RD[v][r]))
    return retq, v2RD, selrestrs, complements

verb2RolesMap,verb2RoleDescs,selrestrs,complements = getVerb2RolesMap(vnMap, themroles)

# Code to run and interpret DL queries
#### TODO: this is a copy-paste of dlquery.py. Should avoid this.

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

def inferTransitiveClosure(c, closedGraph, graph, ignoreConcepts=set([])):
    todo = set(graph[c])
    closedGraph[c] = set([])
    while todo:
        sc = todo.pop()
        if (sc not in closedGraph[c]) and (sc not in ignoreConcepts):
            closedGraph[c].add(sc)
            if sc in graph:
                todo = todo.union(graph[sc])
    return closedGraph


# Prepare approximation concepts for selection restriction disj./complements.

#-1) identify toplevel object concepts in seed_ini
#0) identify all verb role selrestrs.
#1) for all selrestrs. of form not A, create Y and assert Y and A subclassof Nothing
#2) for every selrestr. of form not A and its associated Y, and every toplevel object concept X, ask:
#    X subclassof not A? {Yes: assert X subclassof Y}
#3) for all selrestrs. of form A or B or ... --> create Z and assert A or B or ... subclassof Z
#4) for every selrestr. of form A or B or ... with attached Z and every toplevel object concept X, ask:
#    X and (A or B or ...) subclassof Nothing? {Yes: assert X and Z subclassof Nothing}

complementMap = {}
disjunctionMap = {}

for k,c in enumerate(sorted(list(complements))):
    complementMap[c] = ("ApproximateComplement_%d" % k)
for k,d in enumerate(sorted([x for x in selrestrs if 'U' == x[0]])):
    disjunctionMap[d] = ("ApproximateDisjunction_%d" % k)

for c in sorted(list(complementMap.keys())):
    seedIniLines.append("SubClassOf(ObjectIntersectionOf(:%s :%s) owl:Nothing)" % (c[1], complementMap[c]))
for d in sorted(list(disjunctionMap.keys())):
    for e in d[1:]:
        seedIniLines.append("SubClassOf(%s :%s)" % (getDLString(e, complementMap=complementMap), disjunctionMap[d]))

with open(seedFilename,"w") as outfile:
    for l in seedIniLines:
        _ = outfile.write("%s\n" % l)
    _ = outfile.write(")\n")

os.system('cd %s && %s classification -i %s -o %s' % (owlFolder, koncludeBinary, seedFilename, dflResponseFilename))

superclassesQ = parseResponse(dflResponseFilename)
topObjectConcepts = []
dflPrefix = 'http://www.ease-crc.org/ont/SOMA_DFL.owl#'
queryPrefix = 'http://www.ease-crc.org/ont/DLQuery.owl#'
queryMap = {}
for c in superclassesQ:
    if c.startswith(dflPrefix):
        superclassesClosure = inferTransitiveClosure(c, {}, superclassesQ)[c]
        if 'http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#PhysicalObject' in superclassesClosure:
            topObjectConcepts.append(c[len(dflPrefix):])

complementNames = sorted([complementMap[x] for x in complementMap])
print("Building approximation of complements and disjunctions for role selection restrictions ...")
for k,x in enumerate(sorted(list(topObjectConcepts))):
    show_progress(k, 1, len(topObjectConcepts))
    queryMap = {}
    with open(dflQueryOWLFilename,"w") as outfile:
        for l in seedIniLines:
            _ = outfile.write("%s\n" % l)
        for y in complementMap:
            _ = outfile.write("EquivalentClasses(%s :%s)\n" % (getDLString(y), complementMap[y]))
        for z in disjunctionMap:
            _ = outfile.write("EquivalentClasses(%s :%s)\n" % (getDLString(z), disjunctionMap[z]))
        for z in disjunctionMap:
            zz = disjunctionMap[z]
            z = getDLString(z)
            _ = outfile.write("EquivalentClasses(ObjectIntersectionOf(:%s %s) :%s.%s)\n" % (x, z, x, zz))
            queryMap["%s.%s"%(x,zz)] = (x,zz)
        _ = outfile.write(")\n")
    os.system('cd %s && %s classification -i %s -o %s %s' % (owlFolder, koncludeBinary, dflQueryOWLFilename, dflResponseFilename, blackHole))
    superclassesQ = parseResponse(dflResponseFilename)
    for c in sorted(list(superclassesQ.keys())):
        if c.startswith(dflPrefix):
            superclassesClosure = inferTransitiveClosure(c, {}, superclassesQ)[c]
            c = c[len(dflPrefix):]
            if (c in queryMap) and ('http://www.w3.org/2002/07/owl#Nothing' in superclassesClosure):
                seedIniLines.append('SubClassOf(ObjectIntersectionOf(:%s :%s) owl:Nothing)' % (queryMap[c][0], queryMap[c][1]))
            elif x == c:
                for y in complementNames:
                    if dflPrefix+y in superclassesClosure:
                        seedIniLines.append('SubClassOf(:%s :%s)' % (c, y))

show_progress(len(topObjectConcepts), 1, len(topObjectConcepts))
print("Done!")

with open(seedFilename,"w") as outfile:
    for l in seedIniLines:
        _ = outfile.write("%s\n" % l)
    _ = outfile.write(")\n")

#sys.exit(0)

# Topologically sort object taxonomy and run the build process
def getToposorts(superclasses, subclasses, tops):
    adding = True
    level = 0
    toposorts = {}
    toposorts[0] = tops
    topomap = {c: 0 for c in tops}
    while adding:
        adding = False
        nextLevel = level + 1
        for c in toposorts[level]:
            if c not in subclasses:
                continue
            for sc in subclasses[c]:
                addable = True
                for ssc in superclasses[sc]:
                    if (ssc not in topomap) or (level < topomap[ssc]):
                        addable = False
                if addable:
                    adding = True
                    if nextLevel not in toposorts:
                        toposorts[nextLevel] = set([])
                    toposorts[nextLevel].add(sc)
                    topomap[sc] = nextLevel
        level = nextLevel
    return toposorts, topomap

def getToposortedPropTriples(topomap, proptriples):
    retq = {}
    for t in proptriples:
        if topomap[t[0]] not in retq:
            retq[topomap[t[0]]] = set([])
        retq[topomap[t[0]]].add(t)
    return retq

toposorts, topomap = getToposorts(superclasses, subclasses, tops)
toposortedCOTriples = getToposortedPropTriples(topomap, cotriples)
toposortedUFTriples = getToposortedPropTriples(topomap, uftriples)

def verbCode(verb, verb2RoleDescs, complementMap, disjunctionMap):
    retq = []
    subbed = {}
    for k in sorted(verb2RoleDescs[verb].keys()):
        subbed[k] = False
        if k not in roleMap:
            continue
        candidates = roleMap[k]
        for sv in vsuperclasses[verb]:
            for c in candidates:
                if c in verb2RoleDescs[sv]:
                    subbed[k] = True
                    retq.append(("SubClassOf(:%s.%s :%s.%s)" % (verb, k, sv, c)))
                    break
    for k in sorted(verb2RoleDescs[verb].keys()):
        if k in roleMap:
            retq.append(("SubClassOf(:%s.%s :disposition.%s)" % (verb, k, k)))
            retq.append(("SubClassOf(ObjectSomeValuesFrom(dul:isClassifiedBy ObjectIntersectionOf(:%s ObjectSomeValuesFrom(dul:isDefinedBy :%s))) ObjectSomeValuesFrom(dul:hasQuality :%s.%s))" % (k, verb, verb, k)))
            if (k in verb2RoleDescs[verb]) and verb2RoleDescs[verb][k]:
                s = ""
                if verb2RoleDescs[verb][k] in complementMap:
                    s = ":"+complementMap[verb2RoleDescs[verb][k]]
                elif verb2RoleDescs[verb][k] in disjunctionMap:
                    s = ":"+disjunctionMap[verb2RoleDescs[verb][k]]
                else:
                    s = getDLString(verb2RoleDescs[verb][k], complementMap=complementMap)
                retq.append(("SubClassOf(ObjectSomeValuesFrom(dul:hasQuality :%s.%s) %s)" % (verb, k, s)))
    retq.append("")
    return retq

for t in isas:
    seedIniLines.append(("SubClassOf(:%s :%s)" % (t[0], t[1])))

seedIniLines.append("")

parts = [ast.literal_eval(x) for x in open(partonomyFilename).read().splitlines() if x.strip()]
constituents = [ast.literal_eval(x) for x in open(consistsOfFilename).read().splitlines() if x.strip()]
for t in parts:
    seedIniLines.append(("SubClassOf(:%s ObjectSomeValuesFrom(dul:hasPart :%s))" % (t[0], t[1])))
for t in constituents:
    seedIniLines.append(("SubClassOf(:%s ObjectSomeValuesFrom(dul:hasConstituent :%s))" % (t[0], t[1])))

seedIniLines.append("")

for v in sorted(vsuperclasses.keys()):
    if 0 == len(vsuperclasses[v]):
        seedIniLines.append(("SubClassOf(:%s dul:Task)" % (v)))
    else:
        for sv in sorted(list(vsuperclasses[v])):
            seedIniLines.append(("SubClassOf(:%s :%s)" % (v, sv)))

seedIniLines.append("")

print("Adding verb code ...")
for v in sorted(list(verbs)):
    seedIniLines = seedIniLines + verbCode(v, verb2RoleDescs, complementMap, disjunctionMap)

print("Done. Writing the seed owl and will proceed to incrementally add the object taxonomy to it.")

seedIniLines.append(')')

with open(seedFilename,"w") as outfile:
    for l in seedIniLines:
        _ = outfile.write("%s\n" % l)

def getDLQueryForTriple(t, verb2RolesMap, predicate, relevantRoles):
    newQueryConcepts = [t[0], predicate]
    text = ""
    aux = []
    for r in relevantRoles.intersection(verb2RolesMap[t[1]]):
        disposition = "%s.%s" % (t[1], r)
        queryConcept = "QUERY.%s.%s" % (t[0], disposition)
        text = text + "EquivalentClasses(:%s ObjectIntersectionOf(dfl:%s ObjectSomeValuesFrom(dul:hasQuality dfl:%s)))\n" % (queryConcept, t[0], disposition)
        aux.append((queryConcept, r, disposition))
    newQueryConcepts.append(aux)
    return newQueryConcepts, text

#def getDLQueryForCOTriple(t, verb2RolesMap):
#    return getDLQueryForTriple(t, verb2RolesMap, 'CapableOf', {'Actor', 'Actor1', 'Actor2', 'Agent', 'Asset', 'Attribute', 'Cause', 'Experiencer', 'Instrument', 'Location', 'Material', 'Patient', #'Patient1', 'Patient2', 'Stimulus', 'Theme', 'Theme1', 'Theme2'})
def getDLQueryForCOTriple(t, verb2RolesMap):
    #return getDLQueryForTriple(t, verb2RolesMap, 'CapableOf', {'Asset', 'Attribute', 'Instrument', 'Location', 'Material', 'Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2'})
    return getDLQueryForTriple(t, verb2RolesMap, 'CapableOf', {'Instrument', 'Location', 'Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2'})

def getDLQueryForUFTriple(t, verb2RolesMap):
    #return getDLQueryForTriple(t, verb2RolesMap, 'UsedFor', {'Asset', 'Attribute', 'Instrument', 'Location', 'Material', 'Theme', 'Theme1', 'Theme2'})
    return getDLQueryForTriple(t, verb2RolesMap, 'UsedFor', {'Instrument', 'Location', 'Theme', 'Theme1', 'Theme2'})

def interpretResults(concept, predicate, nonemptyQueryResults):
    #rolepriorities = {"UsedFor": ['Material', 'Instrument', 'Asset', 'Attribute', 'Theme', 'Theme1', 'Theme2', 'Location'], "CapableOf": ['Agent', 'Actor', 'Actor1', 'Actor2', 'Experiencer', 'Material', 'Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2', 'Instrument', 'Asset', 'Attribute', 'Stimulus', 'Cause', 'Location']}[predicate]
    #rolepriorities = {"UsedFor": ['Material', 'Instrument', 'Asset', 'Attribute', 'Theme', 'Theme1', 'Theme2', 'Location'], "CapableOf": ['Material', 'Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2', 'Instrument', 'Asset', 'Attribute', 'Location']}[predicate]
    rolepriorities = {"UsedFor": ['Instrument', 'Theme', 'Theme1', 'Theme2', 'Location'], "CapableOf": ['Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2', 'Instrument', 'Location']}[predicate]
    role = None
    for r in rolepriorities:
        if r in nonemptyQueryResults:
            role = r
            break
    retq = ""
    if None != role:
        retq = "SubClassOf(:%s ObjectSomeValuesFrom(dul:hasQuality :%s))\n" % (concept, nonemptyQueryResults[role])
    return retq

def getResultsFromXML(filename):
    nothing = "http://www.w3.org/2002/07/owl#Nothing"
    inEq = False
    aux = []
    nothings = set()
    iriPLen = len("        <Class IRI=\"")
    with open(filename) as file_in:
        for l in file_in:
            if inEq:
                if "    </EquivalentClasses>\n" == l:
                    inEq = False
                    if nothing in aux:
                        for d in aux:
                            if d != nothing:
                                nothings.add(d)
                    aux = []
                else:
                    if l.startswith("        <Class IRI=\""):
                        aux.append(l[iriPLen:-4])
            elif "    <EquivalentClasses>\n" == l:
                    inEq = True
    return set([x.replace('http://www.ease-crc.org/ont/SOMA_DFL_query.owl#', '') for x in nothings])

def procToposortLevel(cotriples, uftriples, verb2RolesMap):
    queries = []
    with open(dflQueryOWLFilename, "w") as outfile:
        outfile.write("Prefix(:=<http://www.ease-crc.org/ont/SOMA_DFL_query.owl#>)\n")
        outfile.write("Prefix(owl:=<http://www.w3.org/2002/07/owl#>)\n")
        outfile.write("Prefix(rdf:=<http://www.w3.org/1999/02/22-rdf-syntax-ns#>)\n")
        outfile.write("Prefix(xml:=<http://www.w3.org/XML/1998/namespace>)\n")
        outfile.write("Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)\n")
        outfile.write("Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)\n")
        outfile.write("Prefix(dul:=<http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>)\n")
        outfile.write("Prefix(soma:=<http://www.ease-crc.org/ont/SOMA.owl#>)\n\n\n")
        outfile.write("Prefix(dfl:=<http://www.ease-crc.org/ont/SOMA_DFL.owl#>)\n\n\n")
        outfile.write("Ontology(<http://www.ease-crc.org/ont/SOMA_DFL_query.owl>\n")
        outfile.write("Import(<file://./SOMA_DFL.owl>)\n\n")
        for t in cotriples:
            newQueryConcepts, text = getDLQueryForCOTriple(t, verb2RolesMap)
            queries.append(newQueryConcepts)
            outfile.write("%s\n" % text)
        for t in uftriples:
            newQueryConcepts, text = getDLQueryForUFTriple(t, verb2RolesMap)
            queries.append(newQueryConcepts)
            outfile.write("%s\n" % text)
        outfile.write(")\n")
    os.system('cd %s && %s classification -i %s -o %s' % (owlFolder, koncludeBinary, dflQueryOWLFilename, dflResponseFilename))
    emptyClasses = getResultsFromXML(dflResponseFilename)
    additionalText = ""
    for nQC in queries:
        concept, predicate, rqs = nQC
        nonemptyQueryResults = {}
        for rq in rqs:
            if rq[0] not in emptyClasses:
                nonemptyQueryResults[rq[1]] = rq[2]
        additionalText = additionalText + interpretResults(concept, predicate, nonemptyQueryResults)
    firstText = open(dflOWLFilename).read()
    with open(dflOWLFilename, "w") as outfile:
        outfile.write(firstText[:firstText.rfind(')')] + "\n" + additionalText + ")\n")

#print(platform.system())
#if 'Linux' == platform.system():
#    os.system('cp %s %s' % (seedFilename, dflOWLFilename))
#elif "Windows" == platform.system():
#    print('copy "%s" "%s"' % (seedFilename, dflOWLFilename))
#    os.system('copy %s %s' % (seedFilename, dflOWLFilename))
shutil.copyfile(seedFilename, dflOWLFilename)

for k in sorted(toposorts.keys()):
    cotriplesAtK = set([])
    if k in toposortedCOTriples:
        cotriplesAtK = toposortedCOTriples[k]
    uftriplesAtK = set([])
    if k in toposortedUFTriples:
        uftriplesAtK = toposortedUFTriples[k]
    procToposortLevel(cotriplesAtK, uftriplesAtK, verb2RolesMap)
