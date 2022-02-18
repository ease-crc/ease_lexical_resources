import ast
import os
import sys

if 3 > len(sys.argv):
    print("Must supply at least two parameters! Usage: \n\tbackend_OWL.py infile outfile\n")
    sys.exit(1)

outfilePath = sys.argv[2]
infilePath = sys.argv[1]

lemmaEntries = [ast.literal_eval(x) for x in open(infilePath).read().splitlines() if x.strip()]

lemmas = {}

def getLemma(x):
    pos = x[0][1]
    if ("NOUN" == pos) and ("MCT" == x[0][2]):
        pos = "N.unit"
    convert = {"NOUN": "N", "VERB": "V", "ADJ": "ADJ", "ADV": "ADV", "N.unit": "N.unit"}
    if ("ADJ" == pos) and ("preposition" in x[1]):
        # the "transitive" adjective-proposition combos seem spurious
        return None
    if pos not in convert:
        return None
    return (x[0][0], convert[pos])
def getPoS(x):
    return x[0][1]
def getMorphs(x):
    wfs = []
    retq = []
    if "VERB" == x[0][1]:
        if ('infinitive',) in x[1]:
            retq.append([x[1][('infinitive',)], {'morphology': 'present'}])
        elif (True not in [y in x[1] for y in [('singular', 'first'), ('singular', 'second'), ('singular', 'third'), ('plural',)]]):
            retq.append([x[0][0], {'morphology': 'present'}])
        if ('singular', 'third') in x[1]:
            retq.append([x[1][('singular', 'third')], {'morphology': '3rd person sg present', 'finiteness': 'finite'}])
        else:
            retq.append([x[0][0] + 's', {'morphology': '3rd person sg present', 'finiteness': 'finite'}])
        if ('singular', 'second') in x[1]:
            retq.append([x[1][('singular', 'second')], {'morphology': '2nd person sg present', 'finiteness': 'finite'}])
        if ('singular', 'first') in x[1]:
            retq.append([x[1][('singular', 'first')], {'morphology': '1st person sg present', 'finiteness': 'finite'}])
        if ('plural',) in x[1]:
            retq.append([x[1][('plural',)], {'morphology': 'pl present', 'finiteness': 'finite'}])
        if ('presentp',) in x[1]:
            retq.append([x[1][('presentp',)], {'morphology': 'present participle', 'finiteness': 'nonfinite'}])
        else:
            retq.append([x[0][0] + 'ing', {'morphology': 'present participle', 'finiteness': 'nonfinite'}])
        if ('past',) in x[1]:
            retq.append([x[1][('past',)], {'morphology': 'past', 'finiteness': 'finite'}])
        elif (True not in [y in x[1] for y in [('past', 'singular', 'first'), ('past', 'singular', 'second'), ('past', 'singular', 'third'), ('past', 'plural', 'second')]]):
            retq.append([x[0][0] + 'ed', {'morphology': 'past', 'finiteness': 'finite'}])
        if ('past', 'singular', 'first') in x[1]:
            retq.append([x[1][('past', 'singular', 'first')], {'morphology': '1st person sg past', 'finiteness': 'finite'}])
        if ('past', 'singular', 'second') in x[1]:
            retq.append([x[1][('past', 'singular', 'second')], {'morphology': '2nd person sg past', 'finiteness': 'finite'}])
        if ('past', 'singular', 'third') in x[1]:
            retq.append([x[1][('past', 'singular', 'third')], {'morphology': '3rd person sg past', 'finiteness': 'finite'}])
        if ('past', 'singular', 'first') in x[1]:
            retq.append([x[1][('past', 'singular', 'first')], {'morphology': '1st person sg past', 'finiteness': 'finite'}])
        if ('past', 'plural', 'second') in x[1]:
            retq.append([x[1][('past', 'plural', 'second')], {'morphology': 'pl past', 'finiteness': 'finite'}])
        if ('past', 'subjunctive') in x[1]:
            retq.append([x[1][('past', 'subjunctive')], {'morphology': 'past subjunctive', 'finiteness': 'finite'}])
        if ('pastp',) in x[1]:
            retq.append([x[1][('pastp',)], {'morphology': 'past participle', 'finiteness': 'finite'}])
        elif ('past',) in x[1]:
            retq.append([x[1][('past',)], {'morphology': 'past participle', 'finiteness': 'finite'}])
        return retq
    if "NOUN" == x[0][1]:
        if "CT" == x[0][2]:
            wfs = [(('plural',), ((('numerus', 'pl'),), x[0][0]+'s')), (('singular',), ((('numerus', 'sg'),), x[0][0]))]
        if "PRP" == x[0][2]:
            wfs = [(('plural',), ((('numerus', 'pl'),), x[0][0]+'s')), (('singular',), ((('numerus', 'sg'),), x[0][0]))]
        if "NCT" == x[0][2]:
            wfs = [(('ietsial',), ((('numerus', 'sg'),), x[0][0]))]
        if "MCT" == x[0][2]:
            wfs = [(('plural',), ((('numerus', 'pl'),), x[0][0])), (('singular',), ((('numerus', 'sg'),), x[0][0]))]
    if "ADV" == x[0][1]:
        wfs = [('positive', ((), x[0][0]))]
    if "ADJ" == x[0][1]:
        wfs = [('positive', ((), x[0][0]))]
    for wf in wfs:
        fr = wf[1][1]
        prps = {}
        if wf[0] in x[1]:
            fr = x[1][wf[0]]
        for prp in wf[1][0]:
            prps[prp[0]] = prp[1]
        retq.append([fr, prps])
    return retq

def getWordForms(morphs):
    retq = []
    for m in morphs:
        if isinstance(m[0], str):
            retq.append(m)
        else:
            for s in m[0]:
                retq.append([s, m[1]])
    return retq

def getKey(x, k):
    if k in x:
        return x[k]
    return None

for l in lemmaEntries:
    lemma = getLemma(l)
    if not lemma:
        continue
    if lemma not in lemmas:
        lemmas[lemma] = []
    wfs = getWordForms(getMorphs(l))
    for wf in wfs:
        if wf not in lemmas[lemma]:
            lemmas[lemma].append(wf)

cN = 0
label2C = {}
l2WF = {}
wf2L = {}
 
with open(outfilePath, "w") as outfile:
    outfile.write("Prefix(:=<http://www.ease-crc.org/ont/megalex.owl#>)\n")
    outfile.write("Prefix(owl:=<http://www.w3.org/2002/07/owl#>)\n")
    outfile.write("Prefix(rdf:=<http://www.w3.org/1999/02/22-rdf-syntax-ns#>)\n")
    outfile.write("Prefix(xml:=<http://www.w3.org/XML/1998/namespace>)\n")
    outfile.write("Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)\n")
    outfile.write("Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)\n")
    outfile.write("Ontology(<http://www.ease-crc.org/ont/megalex.owl>\n")
    outfile.write('Declaration( Class( :Lemma))\n')
    outfile.write('Declaration( Class( :EnglishWord))\n')
    for l in sorted(lemmas.keys()):
        lName = "%s.%s" % (l[0], l[1])
        if lName in label2C:
            cName = label2C[lName]
        else:
            cName = "C%d" % cN
            label2C[lName] = cName
            cN = cN + 1
            outfile.write('Declaration( NamedIndividual(:%s))\n' % cName)
            outfile.write('ClassAssertion( :Lemma :%s)\n' % cName)
            outfile.write('AnnotationAssertion( rdfs:label :%s "%s")\n' % (cName, lName))
            outfile.write('DataPropertyAssertion( :partOfSpeech :%s "%s")\n' % (cName, l[1]))
        wordForms = lemmas[l]
        for w in sorted(wordForms, key=lambda x: x[0]):
            mr = ''
            if getKey(w[1], 'morphology'):
                mr = getKey(w[1], 'morphology')
            wlName = "%s:%s(%s)" % (lName, w[0], mr)
            if wlName in label2C:
                wName = label2C[wlName]
            else:
                wName = "C%d" % cN
                label2C[wlName] = wName
                cN = cN + 1
                outfile.write('Declaration( NamedIndividual(:%s))\n' % wName)
                outfile.write('ClassAssertion( :EnglishWord :%s)\n' % wName)
                outfile.write('AnnotationAssertion( rdfs:label :%s "%s")\n' % (wName, wlName))
                outfile.write('DataPropertyAssertion( :ortographicForm :%s "%s"^^xsd:string)\n' % (wName, w[0]))
                numerus = getKey(w[1], 'numerus')
                if numerus:
                    outfile.write('DataPropertyAssertion( :numerus :%s "%s"^^xsd:string)\n' % (wName, numerus))
                finite = getKey(w[1], 'finiteness')
                if finite:
                    outfile.write('DataPropertyAssertion( :finiteness :%s "%s"^^xsd:string)\n' % (wName, finite))
                morphology = getKey(w[1], 'morphology')
                if morphology:
                    outfile.write('DataPropertyAssertion( :morphology :%s "%s"^^xsd:string)\n' % (wName, morphology))
            if (cName, wName) not in l2WF:
                outfile.write('ObjectPropertyAssertion( :hasWordForm :%s :%s)\n' % (cName, wName))
                l2WF[(cName, wName)] = True
            if (wName, cName) not in wf2L:
                outfile.write('ObjectPropertyAssertion( :isWordFormOf :%s :%s)\n' % (wName, cName))
                wf2L[(wName, cName)] = True
    outfile.write(")\n")

