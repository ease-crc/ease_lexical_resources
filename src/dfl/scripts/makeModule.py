import errno
import os
import ast
import sys
import progressbar
import platform
import shutil

import argparse
import yaml

cpath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(cpath,'../src'))

import dfl.dlquery as dl

blackHole = ">/dev/null 2>&1"
if "Windows" == platform.system():
    blackHole = " > NUL"
    
basePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
objectTaxonomyFile = os.path.join(basePath, "resources/ObjectTaxonomy.res")
hasPartFile = os.path.join(basePath, "resources/DFLHasPart.res")
consistsOfFile = os.path.join(basePath, "resources/DFLConsistsOf.res")
seedIniFile = os.path.join(basePath, "resources/SOMA_DFL_seed_ini.res")
somaAlignmentsFile = os.path.join(basePath, "resources/SOMAAlignments.res")
definitionsFile = os.path.join(basePath, "resources/WordNetDefinitions.res")
moduleFile = os.path.join(basePath, "owl/SOMA_DFL_module.owl")

prefixesDFL = {
            '': 'http://www.ease-crc.org/ont/SOMA_DFL.owl#',
            'dfl': 'http://www.ease-crc.org/ont/SOMA_DFL.owl#',            
            'owl': 'http://www.w3.org/2002/07/owl#',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'xml': 'http://www.w3.org/XML/1998/namespace',
            'xsd': 'http://www.w3.org/2001/XMLSchema#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'dul': 'http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#',
            'soma': 'http://www.ease-crc.org/ont/SOMA.owl#',
            'dlquery': 'http://www.ease-crc.org/ont/DLQuery.owl#' 
            }
def expandName(conceptName):
    prefs = prefixesDFL
    if ('://' in conceptName) or (':' not in conceptName):
        return conceptName
    prefix = conceptName[:conceptName.find(':')]
    suffix = conceptName[conceptName.find(':') + 1:]
    retq = prefs[prefix] + suffix
    return retq
def contractName(conceptName):
    prefs = prefixesDFL
    for p, exp in prefs.items():
        if conceptName.startswith(exp):
            return p + ":" + conceptName[len(exp):]
    return conceptName

def filterStatements(filename, concs):
    retq = [ast.literal_eval(x) for x in open(filename).read().splitlines()]
    retq = [("dfl:"+x[0], "dfl:"+x[1]) for x in retq]
    retq = [x for x in retq if (expandName(x[0]) in concs) and (expandName(x[1]) in concs)]
    return retq

def writeEquivalenceAxiom(d):
    a, b = ast.literal_eval(d)
    return "EquivalentClasses(%s %s)" % (a, b)

def main():
    parser = argparse.ArgumentParser(prog='makeModule', description='Extract a fragment of SOMA_DFL that hopefully contains only objects and properties related to your particular application.', epilog='')
    parser.add_argument('-s', '--moduleSpecification', default="", help='Path to a yaml file containing a specification for what should be extracted.')
    arguments = parser.parse_args()
    if "" == arguments.moduleSpecification:
        arguments.moduleSpecification = os.path.join(basePath, "scripts/procthorModuleSpecification.yaml")

    with open(arguments.moduleSpecification, 'r') as stream:
        specification = yaml.safe_load(stream)
    targetConcepts = specification["targetConcepts"]
    #targetConcepts = ['dfl:edible_fruit.n.wn.food', 'dfl:vegetable.n.wn.food', 'dfl:tableware.n.wn.artifact', 'dfl:furniture.n.wn.artifact', 'appliance.n.wn.artifact..durables']
    dl.buildCache()
    concs = set()
    for t in targetConcepts:
        subconcs = dl.whatSubclasses(t)
        concs = concs.union(subconcs)
        for s in subconcs:
            concs = concs.union(dl.whatSuperclasses(s))
    expConcs = set([expandName(x) for x in concs])
    taxonomy = filterStatements(objectTaxonomyFile, expConcs)
    parthood = filterStatements(hasPartFile, expConcs)
    consists = filterStatements(consistsOfFile, expConcs)
    seedIniLines = [x for x in open(seedIniFile).read().splitlines()][:-1]
    seedIniLines = seedIniLines + [writeEquivalenceAxiom(x) for x in open(somaAlignmentsFile).read().splitlines() if x.strip()]
    definitionsRaw = [ast.literal_eval(x) for x in open(definitionsFile).read().splitlines()]
    definitions = {}
    for d in definitionsRaw:
        c, defs = d
        if "http://www.ease-crc.org/ont/SOMA_DFL.owl#"+c in expConcs:
            definitions["dfl:"+c] = [x[1] for x in defs]
    dispositions = {}
    for c in concs:
        dispositions[c] = dl.whatDispositionsDoesObjectHave(c)
    specificDispositions = {}
    for c in concs:
        supDs = set()
        eqs = dl.whatsEquivalent(c)
        for s in dl.whatSuperclasses(c):
            if s not in eqs:
                supDs = supDs.union(dl.whatDispositionsDoesObjectHave(s))
                #if ":table.n.wn.artifact..furniture" == c:
                #    print(s, dl.whatDispositionsDoesObjectHave(s))
        specificDispositions[c] = set(dispositions[c]).difference(supDs)
    
    allDispositions = set().union(*[x for x in specificDispositions.values()])
    
    #table = "http://www.ease-crc.org/ont/SOMA_DFL.owl#table.n.wn.artifact..furniture"
    #print(dl.whatDispositionsDoesObjectHave("soma:Table"))
    #print(dl.whatDispositionsDoesObjectHave(table))
    #print(specificDispositions[":table.n.wn.artifact..furniture"])
    
    with open(moduleFile,"w") as outfile:
        for l in seedIniLines:
            _ = outfile.write("%s\n" % l)
        _ = outfile.write("\n")
        for c in sorted(definitions.keys()):
            for d in definitions[c]:
                _ = outfile.write("AnnotationAssertion(rdfs:comment %s \"%s\"^^xsd:string)\n" % (c, d.replace("\"", "\\\"")))
        _ = outfile.write("\n")
        for d in sorted(list(allDispositions)):
            _ = outfile.write("SubClassOf(%s soma:Disposition)\n" % d)
        _ = outfile.write("\n")
        for t in sorted(list(taxonomy)):
            _ = outfile.write("SubClassOf(%s %s)\n" % (t[0], t[1]))
        _ = outfile.write("\n")
        for p in sorted(list(parthood)):
            _ = outfile.write("SubClassOf(%s ObjectSomeValuesFrom(dul:hasPart %s))\n" % (p[0], p[1]))
        _ = outfile.write("\n")
        for p in sorted(list(consists)):
            _ = outfile.write("SubClassOf(%s ObjectSomeValuesFrom(dul:hasConstituent %s))\n" % (p[0], p[1]))
        _ = outfile.write("\n")
        for c in sorted(list(specificDispositions.keys())):
            for d in sorted(list(specificDispositions[c])):
                _ = outfile.write("SubClassOf(%s ObjectSomeValuesFrom(dul:hasQuality %s))\n" % (c, d))
        _ = outfile.write("\n")
        _ = outfile.write(")\n")

if "__main__" == __name__:
    main()
