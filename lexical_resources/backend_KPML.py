import os, os.path
import sys

import ast

import megalex
from megalex import safelyAccessFirstString

import datetime

if 3 > len(sys.argv):
    print("Must supply at least two parameters! Usage: \n\tbackend_KPML.py infile outfile\n")
    sys.exit(1)

outfilePath = sys.argv[2]
infilePath = sys.argv[1]

def adverb2Features(entry):
    spelling = safelyAccessFirstString(entry[1], 'positive')
    comparative = safelyAccessFirstString(entry[1], 'comparative', None)
    superlative = safelyAccessFirstString(entry[1], 'superlative', None)
    forms = "()"
    features = "(ADVERB"
    if superlative or comparative:        
        forms = "("
        if comparative:
            features += " COMPARATIVEFORM"
            forms += "(COMPARATIVEFORM \"%s\")" % (comparative,)
        if comparative and superlative:
            features += " "
            forms += " "
        if superlative:
            features += " SUPERLATIVEFORM"
            forms += "(SUPERLATIVEFORM \"%s\")" % (superlative,)
        forms += ")"
        features += " IRR)"
    else:
        features += ")"
    return spelling, features, forms

def adjective2Features(entry):
    # TODO: be a bit smarter with features; use R-ST, ER-EST etc. where possible
    spelling = safelyAccessFirstString(entry[1], 'positive')
    comparative = safelyAccessFirstString(entry[1], 'comparative', None)
    superlative = safelyAccessFirstString(entry[1], 'superlative', None)
    forms = "()"
    features = "(ADJECTIVE"
    if superlative or comparative:        
        forms = "("
        if comparative:
            features += " COMPARATIVEFORM"
            forms += "(COMPARATIVEFORM \"%s\")" % (comparative,)
        if comparative and superlative:
            features += " "
            forms += " "
        if superlative:
            features += " SUPERLATIVEFORM"
            forms += "(SUPERLATIVEFORM \"%s\")" % (superlative,)
        forms += ")"
        features += " IRR)"
    else:
        features += ")"
    return spelling, features, forms

def properNoun2Features(entry):
    spelling = ""
    features = "()"
    forms = "()"
    features = "(NOUN PROPER-NOUN COUNTABLE "
    if "THE" == entry[0][3]:
        features += "DETERMINERREQUIRED "
    else:
        features += "NOT-DETERMINERREQUIRED "
    singular = safelyAccessFirstString(entry[1], ('singular',))
    spelling = singular
    plural = safelyAccessFirstString(entry[1], ('plural',), None)
    isS = False
    isES = False
    isIrr = False
    if plural and (singular + 's' == plural):
        isS = True
    if plural and (singular + 'es' == plural):
        isES = True
    if plural and (not isS) and (not isES):
        isIrr = True
    if isIrr:
        features += "PLURALFORM IRR)"
        forms = "((PLURALFORM \"%s\"))" % (plural,) 
    elif isS:
        features += "S)"
    elif isES:
        features += "ES)"
    else:
        features += ")"
    return spelling, features, forms

def commonNoun2Features(entry):
    spelling = ""
    features = "()"
    forms = "()"
    if ("CT" == entry[0][2]) or ("MCT" == entry[0][2]):
        forms = "()"
        singular = safelyAccessFirstString(entry[1], ('singular',))
        spelling = singular
        plural = safelyAccessFirstString(entry[1], ('plural',), None)
        isS = False
        isES = False
        isIrr = False
        if plural and (singular + 's' == plural):
            isS = True
        if plural and (singular + 'es' == plural):
            isES = True
        if plural and (not isS) and (not isES):
            isIrr = True
        features = "(NOUN COMMON-NOUN COUNTABLE "
        if isIrr:
            features += "PLURALFORM IRR)"
            forms = "((PLURALFORM \"%s\"))" % (plural,) 
        elif isS:
            features += "S)"
        elif isES:
            features += "ES)"
        else:
            features += ")"
    elif "NCT" == entry[0][2]:
        forms = "()"
        ietsial = safelyAccessFirstString(entry[1], ('ietsial',))
        # Obs: do we need a feature for plural morphology? KPML's original megalexicon includes this for some mass nouns
        features = "(NOUN COMMON-NOUN UNCOUNTABLE S)"
    return spelling, features, forms

def noun2Features(entry):
    if 'PRP' == entry[0][2]:
        return properNoun2Features(entry)
    return commonNoun2Features(entry)

def preposition2Features(entry):
    spelling = entry[1][('prep',)]
    if isinstance(spelling, list):
        spelling = spelling[0]
    return spelling, "(PREPOSITION)", "()"

def verb2Features(entry):
    # ES-ED S-*ED S-ED S-D *-IRR S-IRR ES-IRR
    # TODO: add present-participle (INGPARTICIPLEFORM) and past-form (PASTFORM)
    spelling = safelyAccessFirstString(entry[1], ('infinitive',))
    if "" == spelling:
        spelling = entry[0][0]
    thirdSingular = safelyAccessFirstString(entry[1], ('singular', 'third'), None)
    pastParticiple = safelyAccessFirstString(entry[1], ('pastp',), None)
    pastForm = safelyAccessFirstString(entry[1], ('past',), None)
    ingForm = safelyAccessFirstString(entry[1], ('presentp',), None)
    if not pastForm:
        pastForm = pastParticiple
    isIngIrr = False
    features = "(VERB "
    forms = "("
    is3S = False
    is3ES = False
    is3Irr = False
    if thirdSingular and (spelling + 's' == thirdSingular):
        is3S = True
    if thirdSingular and (spelling + 'es' == thirdSingular):
        is3ES = True
    if thirdSingular and (not is3S) and (not is3ES):
        is3Irr = True
    if (not is3S) and (not is3ES) and (not is3Irr):
        is3S = True
    isPPED = False
    isPPSED = False
    isPPD = False
    isPPIrr = False
    if pastParticiple and (spelling + 'd' == pastParticiple):
        isPPD = True
        if ingForm and (spelling[:-1] + 'ing' != ingForm):
            isIngIrr = True
    if pastParticiple and (spelling + 'ed' == pastParticiple):
        isPPED = True
        if ingForm and (spelling + 'ing' != ingForm):
            isIngIrr = True
    if pastParticiple and (spelling + spelling[-1] + 'ed' == pastParticiple):
        isPPSED = True
        if ingForm and (spelling + spelling[-1] + 'ing' != ingForm):
            isIngIrr = True
    if pastParticiple and (not isPPD) and (not isPPED) and (not isPPSED):
        isPPIrr = True
        if ingForm:
            isIngIrr = True
    if (not isPPD) and (not isPPED) and (not isPPSED) and (not isPPIrr):
        isPPED = True
        if ingForm and (spelling + 'ing' != ingForm):
            isIngIrr = True

    if ingForm and isIngIrr:
        features += "INGPARTICIPLEFORM "
        forms += "(INGPARTICIPLEFORM \"%s\")" % (ingForm,)    
    if is3Irr:
        features += "THIRDSINGULARFORM "
        forms += "(THIRDSINGULARFORM \"%s\")" % (thirdSingular,)
    if isPPIrr:
        features += "EDPASTFORM PASTFORM"
        forms += "(EDPASTFORM \"%s\") (PASTFORM \"%s\")" % (pastParticiple, pastForm)
    if is3ES and isPPED:
        features += "ES-ED "
    if is3S and isPPSED:
        features += "S-*ED "
    if is3S and isPPED:
        features += "S-ED"
    if is3S and isPPD:
        features += "S-D"
    if is3S and isPPIrr:
        features += "S-IRR"
    if is3ES and isPPIrr:
        features += "ES-IRR"
    if is3Irr:
        features += "*-IRR"
    features += ")"
    forms += ")"
    return spelling, features, forms

def entry2Features(entry):
    if "ADV" == entry[0][1]:
        return adverb2Features(entry)
    if "ADJ" == entry[0][1]:
        return adjective2Features(entry)
    if "NOUN" == entry[0][1]:
        return noun2Features(entry)
    if "PREP" == entry[0][1]:
        return preposition2Features(entry)
    if "VERB" == entry[0][1]:
        return verb2Features(entry)
    return "", "()", "()"

def entry2LEX(entry):
    lexName = "|" + str(entry[0]) + "|"
    spelling, features, forms = entry2Features(entry)
    # TODO: add info, and relevant code to extract it, about KPML properties
    properties = "()"
    return "(LEXICAL-ITEM :NAME %s :SPELLING \"%s\" :SAMPLE-SENTENCE \"\" :FEATURES %s :PROPERTIES %s :EDITOR \"BLANDC\" :DATE \"%s\")" % (lexName, spelling, features, forms, str(datetime.datetime.now()))

lines = open(infilePath).read().splitlines()
entries = []
for line in lines:
    line = line.strip()
    entries.append(ast.literal_eval(line))

with open(outfilePath, "w") as outfile:
    outfile.write('(in-package "KPML")\n\n')
    outfile.write(';;; File creation information:\n') 
    outfile.write(';;; %s at Unknown.\n\n' % (str(datetime.datetime.now()),))
    outfile.write('(in-language :languages :ENGLISH)\n')
    for entry in entries:
        outfile.write("%s\n" % entry2LEX(entry))

