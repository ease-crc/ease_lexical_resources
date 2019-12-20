import os, os.path
import sys

import ast

import megalex
from megalex import safelyAccessFirstString, safelyAccessStrings

import datetime

if 3 > len(sys.argv):
    print("Must supply at least two parameters! Usage: \n\tbackend_KPML.py infile outfile\n")
    sys.exit(1)

outfilePath = sys.argv[2]
infilePath = sys.argv[1]

def lemma2ClassName(lemma):
    name = ""
    first = True
    for item in lemma:
        if first:
            first = False
        else:
            name += "-"
        name += item
    return name.replace(" ", "-")

def possessiveForm(spelling):
    if 's' == spelling[-1]:
        return spelling + "'"
    return spelling + "'s"

def properNounMorphs(entry):
    morphs = []
    name = lemma2ClassName(entry[0])
    singulars = safelyAccessStrings(entry[1], ('singular',))
    plurals = safelyAccessStrings(entry[1], ('plural',))
    for singular in singulars:
        morphs.append("<entry pos=\"NP\" word=\"%s\" class=\"%s\" macros=\"@num.sg\"/>" % (singular, name))
        morphs.append("<entry pos=\"NP.possessive\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.sg @case.gen\"/>" % (possessiveForm(singular), singular, name))
    for plural in plurals:
        if singulars:
            morphs.append("<entry pos=\"NP\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.pl\"/>" % (plural, singulars[0], name))
            morphs.append("<entry pos=\"NP.possessive\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.pl @case.gen\"/>" % (possessiveForm(plural), singulars[0], name))
        else:
            morphs.append("<entry pos=\"NP\" word=\"%s\" class=\"%s\" macros=\"@num.pl\"/>" % (plural, name))
            morphs.append("<entry pos=\"NP.possessive\" word=\"%s\" class=\"%s\" macros=\"@num.pl @case.gen\"/>" % (possessiveForm(plural), name))
    return morphs

def countableNounMorphs(entry):
    morphs = []
    name = lemma2ClassName(entry[0])
    singulars = safelyAccessStrings(entry[1], ('singular',))
    plurals = safelyAccessStrings(entry[1], ('plural',))
    for singular in singulars:
        morphs.append("<entry pos=\"N\" word=\"%s\" class=\"%s\" macros=\"@num.sg @pers.3rd\"/>" % (singular, name))
        morphs.append("<entry pos=\"N.possessive\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.sg @pers.3rd @case.gen\"/>" % (possessiveForm(singular), singular, name))
    for plural in plurals:
        if singulars:
            morphs.append("<entry pos=\"N\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.pl @pers.3rd\"/>" % (plural, singulars[0], name))
            morphs.append("<entry pos=\"N.possessive\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.pl @pers.3rd @case.gen\"/>" % (possessiveForm(plural), singulars[0], name))
        else:
            morphs.append("<entry pos=\"N\" word=\"%s\" class=\"%s\" macros=\"@num.pl @pers.3rd\"/>" % (plural, name))
            morphs.append("<entry pos=\"N.possessive\" word=\"%s\" class=\"%s\" macros=\"@num.pl @pers.3rd @case.gen\"/>" % (possessiveForm(plural), name))
    return morphs

def uncountableNounMorphs(entry):
    morphs = []
    name = lemma2ClassName(entry[0])
    singulars = safelyAccessStrings(entry[1], ('ietsial',))
    plurals = safelyAccessStrings(entry[1], ('plural',))
    for singular in singulars:
        morphs.append("<entry pos=\"N\" word=\"%s\" class=\"%s\" macros=\"@num.sg @pers.3rd\"/>" % (singular, name))
        morphs.append("<entry pos=\"N.possessive\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.sg @pers.3rd @case.gen\"/>" % (possessiveForm(singular), singular, name))
    for plural in plurals:
        if singulars:
            morphs.append("<entry pos=\"N\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.pl @pers.3rd\"/>" % (plural, singulars[0], name))
            morphs.append("<entry pos=\"N.possessive\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@num.pl @pers.3rd @case.gen\"/>" % (possessiveForm(plural), singulars[0], name))
        else:
            morphs.append("<entry pos=\"N\" word=\"%s\" class=\"%s\" macros=\"@num.pl @pers.3rd\"/>" % (plural, name))
            morphs.append("<entry pos=\"N.possessive\" word=\"%s\" class=\"%s\" macros=\"@num.pl @pers.3rd @case.gen\"/>" % (possessiveForm(plural), name))
    return morphs

def measureUnitMorphs(entry):
    morphs = []
    name = lemma2ClassName(entry[0])
    singulars = safelyAccessStrings(entry[1], ('singular',))
    plurals = safelyAccessStrings(entry[1], ('plural',))
    for singular in singulars:
        morphs.append("<entry pos=\"N.unit\" word=\"%s\" class=\"%s\" />" % (singular, name))
        morphs.append("<entry pos=\"N.possessive\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@case.gen\"/>" % (possessiveForm(singular), singular, name))
    for plural in plurals:
        if singulars:
            morphs.append("<entry pos=\"N.unit\" word=\"%s\" stem=\"%s\" class=\"%s\" />" % (plural, singulars[0], name))
            morphs.append("<entry pos=\"N.possessive\" word=\"%s\" stem=\"%s\" class=\"%s\" macros=\"@case.gen\"/>" % (possessiveForm(plural), singulars[0], name))
        else:
            morphs.append("<entry pos=\"N.unit\" word=\"%s\" class=\"%s\" />" % (plural, name))
            morphs.append("<entry pos=\"N.possessive\" word=\"%s\" class=\"%s\" macros=\"@case.gen\"/>" % (possessiveForm(plural), name))
    return morphs

def noun2LEX(entry):
    if "PRP" == entry[0][2]:
        return properNounMorphs(entry)
    if "CT" == entry[0][2]:
        return countableNounMorphs(entry)
    if "NCT" == entry[0][2]:
        return uncountableNounMorphs(entry)
    if "MCT" == entry[0][2]:
        return measureUnitMorphs(entry)

lines = open(infilePath).read().splitlines()
pretxt = open("./backend_CCG_pre.txt").read()
postxt = open("./backend_CCG_post.txt").read()
entries = []
for line in lines:
    line = line.strip()
    entries.append(ast.literal_eval(line))

with open(outfilePath, "w") as outfile:
    outfile.write('%s\n' % pretxt)
    for entry in entries:
        # TODO: for now only output nouns
        if "NOUN" == entry[0][1]:
            morphs = noun2LEX(entry)
            for morph in morphs:
                outfile.write("%s\n" % (morph,))
    outfile.write('%s\n' % postxt)

