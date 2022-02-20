import os
import ast
import sys

import xml.etree.ElementTree as ET

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

basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")

objectTaxonomyFilename = os.path.join(basePath,"resources/ObjectTaxonomy.res")
verbTaxonomyFilename = os.path.join(basePath,"resources/VerbTaxonomy.res")
capableOfFilename = os.path.join(basePath,"resources/DFLCapableOf.res")
usedForFilename = os.path.join(basePath,"resources/DFLUsedFor.res")
vnthemrolesFilename = os.path.join(basePath,"resources/vnthemroles.res")
vntriplesFilename = os.path.join(basePath,"resources/DFLHasVNVC.res")
seedIniFilename = os.path.join(basePath, "resources/SOMA_DFL_seed_ini.res")
seedFilename = os.path.join(basePath, "owl/SOMA_DFL_seed.owl")
dflOWLFilename = os.path.join(basePath, "owl/SOMA_DFL.owl")
dflQueryOWLFilename = os.path.join(basePath, "owl/SOMA_DFL_query.owl")
dflResponseFilename = os.path.join(basePath, "owl/SOMA_DFL_response.owl")
owlFolder = os.path.join(basePath, "owl")
koncludeBinary = os.path.join(basePath, "bin/Konclude")

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
    vnTriples = [ast.literal_eval(x) for x in open(vntriplesFilename).read().splitlines() if x.strip()]
    themroles = [ast.literal_eval(x) for x in open(vnthemrolesFilename).read().splitlines() if x.strip()]
    themroles = {x[0]: x[1] for x in themroles}
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

def getPropTriples(capableOfFilename, usedForFilename, concs, vnMap):
    cotriples = [ast.literal_eval(x) for x in open(capableOfFilename).read().splitlines() if x.strip()]
    uftriples = [ast.literal_eval(x) for x in open(usedForFilename).read().splitlines() if x.strip()]
    cotriples = [x for x in cotriples if (x[0] in concs) and (x[1] in vnMap)]
    uftriples = [x for x in uftriples if (x[0] in concs) and (x[1] in vnMap)]
    return cotriples, uftriples

seedIniLines = [x for x in open(seedIniFilename).read().splitlines()][:-1]
concs, isas, superclasses, subclasses, tops = loadObjectTaxonomy(objectTaxonomyFilename)
visas, vsuperclasses, vnTriples, vnMap, themroles, rolesList = getVerbData(verbTaxonomyFilename, vntriplesFilename, vnthemrolesFilename)
cotriples, uftriples = getPropTriples(capableOfFilename, usedForFilename, concs, vnMap)

verbs = set([])
for t in cotriples + uftriples:
    verbs.add(t[1])
aux = set([])
for v in verbs:
    if v in vsuperclasses:
        for sv in vsuperclasses[v]:
            aux.add(sv)
verbs = verbs.union(aux)

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

def getVerb2RolesMap(vnMap, themroles):
    retq = {}
    for v in vnMap:
        retq[v] = set([])
        for vnc in vnMap[v]:
            for r in themroles[vnc]:
                retq[v].add(r)
    return retq

def getToposortedPropTriples(topomap, proptriples):
    retq = {}
    for t in proptriples:
        if topomap[t[0]] not in retq:
            retq[topomap[t[0]]] = set([])
        retq[topomap[t[0]]].add(t)
    return retq

toposorts, topomap = getToposorts(superclasses, subclasses, tops)
verb2RolesMap = getVerb2RolesMap(vnMap, themroles)
toposortedCOTriples = getToposortedPropTriples(topomap, cotriples)
toposortedUFTriples = getToposortedPropTriples(topomap, uftriples)

def getDLStr(roleDesc, verb, roles):
    ##    ('refl', '+'): must also be Agent, Actor, or Experiencer [in order]
    ##    -region: ignore
    retq = ""
    if isinstance(roleDesc, dict):
        aux = []
        for e in roleDesc['']:
            aux.append(getDLStr(e, verb, roles))
        aux = sorted(list(set(aux)))
        if 'owl:Thing' in aux:
            if ('op' in roleDesc) and ('or' == roleDesc['op']):
                aux = ['owl:Thing']
            elif 1 < len(aux):
                aux.remove('owl:Thing')
        if 1 < len(aux):
            if ('op' in roleDesc) and ('or' == roleDesc['op']):
                retq = "ObjectUnionOf(" + (" ".join(aux)) + ")"
            else:
                retq = "ObjectIntersectionOf(" + (" ".join(aux)) + ")"
        else:
            retq = aux[0]
    else:
        if ('-', 'region') == roleDesc:
            retq = "owl:Thing"
        elif '-' == roleDesc[0]:
            retq = "ObjectComplementOf(:%s)" % roleDesc[1]
        elif ('+', 'refl') == roleDesc:
            if 'Agent' in roles:
                retq = "ObjectSomeValuesFrom(dul:hasQuality :%s.Agent)" % verb
            elif 'Actor' in roles:
                retq = "ObjectSomeValuesFrom(dul:hasQuality :%s.Actor)" % verb
            elif 'Actor1' in roles:
                retq = "ObjectSomeValuesFrom(dul:hasQuality :%s.Actor1)" % verb
            elif 'Actor2' in roles:
                retq = "ObjectSomeValuesFrom(dul:hasQuality :%s.Actor2)" % verb
            elif 'Experiencer' in roles:
                retq = "ObjectSomeValuesFrom(dul:hasQuality :%s.Experiencer)" % verb
        else:
            retq = ":%s" % roleDesc[1]
    return retq

def verbCode(verb, vnMap, themroles, rolesList):
    retq = []
    roles = {}
    for v in vnMap[verb]:
        for t in themroles[v].keys():
            if t not in roles:
                roles[t] = {'': [], 'op': 'or'}
            if (not isinstance(themroles[v][t], dict)) or ([] != themroles[v][t]['']): 
                roles[t][''].append(themroles[v][t])
    notsimple = True
    while notsimple:
        notsimple = False
        for k in roles.keys():
            aux = []
            for e in roles[k]['']:
                if (isinstance(e, dict) and ('op' in e) and ('or' == e['op'])):
                    aux = aux + e['']
                    notsimple = True
                else:
                    aux.append(e)
            roles[k][''] = aux
    subbed = {}
    for k in sorted(roles.keys()):
        subbed[k] = False
        if k not in roleMap:
            continue
        candidates = roleMap[k]
        for sv in vsuperclasses[verb]:
            for c in candidates:
                if c in rolesList[sv]:
                    subbed[k] = True
                    retq.append(("SubClassOf(:%s.%s :%s.%s)" % (verb, k, sv, c)))
                    break
    for k in sorted(roles.keys()):
        retq.append(("SubClassOf(:%s.%s :disposition.%s)" % (verb, k, k)))
        retq.append(("SubClassOf(ObjectSomeValuesFrom(dul:isClassifiedBy ObjectIntersectionOf(:%s ObjectSomeValuesFrom(dul:isDefinedBy :%s))) ObjectSomeValuesFrom(dul:hasQuality :%s.%s))" % (k, verb, verb, k)))
        if [] != roles[k]['']:
            retq.append(("SubClassOf(ObjectSomeValuesFrom(dul:hasQuality :%s.%s) %s)" % (verb, k, getDLStr(roles[k], verb, roles))))
    retq.append("")
    return retq

for t in isas:
    seedIniLines.append(("SubClassOf(:%s :%s)" % (t[0], t[1])))

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
    seedIniLines = seedIniLines + verbCode(v, vnMap, themroles, rolesList)

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
    return getDLQueryForTriple(t, verb2RolesMap, 'CapableOf', {'Asset', 'Attribute', 'Instrument', 'Location', 'Material', 'Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2'})

def getDLQueryForUFTriple(t, verb2RolesMap):
    return getDLQueryForTriple(t, verb2RolesMap, 'UsedFor', {'Asset', 'Attribute', 'Instrument', 'Location', 'Material', 'Theme', 'Theme1', 'Theme2'})

def interpretResults(concept, predicate, nonemptyQueryResults):
    #rolepriorities = {"UsedFor": ['Material', 'Instrument', 'Asset', 'Attribute', 'Theme', 'Theme1', 'Theme2', 'Location'], "CapableOf": ['Agent', 'Actor', 'Actor1', 'Actor2', 'Experiencer', 'Material', 'Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2', 'Instrument', 'Asset', 'Attribute', 'Stimulus', 'Cause', 'Location']}[predicate]
    rolepriorities = {"UsedFor": ['Material', 'Instrument', 'Asset', 'Attribute', 'Theme', 'Theme1', 'Theme2', 'Location'], "CapableOf": ['Material', 'Patient', 'Patient1', 'Patient2', 'Theme', 'Theme1', 'Theme2', 'Instrument', 'Asset', 'Attribute', 'Location']}[predicate]
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
    eqs = ET.parse(filename).findall('{http://www.w3.org/2002/07/owl#}EquivalentClasses')
    nothing = "http://www.w3.org/2002/07/owl#Nothing"
    nothings = set()
    for eq in eqs:
        chs = set([x.get('IRI') for x in eq.getchildren()])
        if nothing in chs:
            nothings = nothings.union(chs)
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

os.system('cp %s %s' % (seedFilename, dflOWLFilename))

for k in sorted(toposorts.keys()):
    cotriplesAtK = set([])
    if k in toposortedCOTriples:
        cotriplesAtK = toposortedCOTriples[k]
    uftriplesAtK = set([])
    if k in toposortedUFTriples:
        uftriplesAtK = toposortedUFTriples[k]
    procToposortLevel(cotriplesAtK, uftriplesAtK, verb2RolesMap)

