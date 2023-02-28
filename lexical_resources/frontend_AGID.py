import os, os.path
import sys

import megalex
import datetime

#TODO watch out for malformed predicates with missing brackets: should perhaps report an error.

def parseAGIDLine(line):
    # <word><sp><pos>[?]:<sp><inflected forms>
    # <word>             := [[A-Za-z']]+
    # <sp>               := <literal space>
    # <pos>              := [[VNA]]
    # <inflected forms>  := <inflected form><sp>|<sp>...<sp>|<sp><inflected form>
    # <inflected form>   := <individual entry>,<sp>...,<sp><individual entry>
    # <individual entry> := <word><word tags>[<sp><variant level>][<sp>{<explanation>}]
    # <word tags>        := [~][<][!][?]
    # <explanation>      := [<explanation text>][:<distinguishing number>]
    # <explanation text> := [[A-Za-z'_/]]+
    line = line.strip()
    colon = line.find(':')
    if -1 == colon:
        return None, None, None
    pre = line[:colon]
    post = line[colon + 1:]
    sp = pre.rfind(' ')
    if -1 == sp:
        return None, None, None
    word = pre[:sp]
    pos = pre[sp + 1:]
    post = post.strip()
    ifs = post.split('|')
    forms = []
    for infform in ifs:
        infform = infform.strip()
        indentries = infform.split(',')
        variants = []
        for entry in indentries:
            entry = entry.strip()
            sp = entry.find(' ')
            variant = '0'
            if -1 != sp:
                variant = entry[sp + 1]
                entry = entry[:sp]
            if (entry == entry.rstrip('~<!?')) and (variant in ['0', '1']):
                variants.append(entry)
        forms.append(variants)
    return word, pos, forms

def loadAGIDLexicon(infilePath):
    megalexicon = {}
    lines = open(infilePath).read().splitlines()
    for line in lines:
        word, pos, forms = parseAGIDLine(line)
        # only use AGID for verbs for now
        if ('V' == pos) or ('V?' == pos):
            # a couple verbs in AGID get special treatment, so we'll just patch these manually
            if ('be' == word) or ('wit' == word):
                continue
            else:
            # Most of the time though the sets of verb morphs is standard
                if 4 == len(forms):
                    megalexicon[(word, 'VERB')] = {('past',): forms[0], ('pastp',): forms[1], ('presentp',): forms[2], ('singular', 'third'): forms[3]}
                elif 3 == len(forms):
                    megalexicon[(word, 'VERB')] = {('past',): forms[0], ('pastp',): forms[0], ('presentp',): forms[1], ('singular', 'third'): forms[2]}
    return megalexicon

if 2 > len(sys.argv):
    print("Must supply at least one parameter! Usage: \n\tfrontend_AGID.py outfile [infile1 infile2 ...]\n")
    sys.exit(1)

outfilePath = sys.argv[1]

# Make sure the output file exists, because from this point on we assume to be adding to it
if not os.path.isfile(outfilePath):
    with open(outfilePath, "w") as outfile:
        outfile.write("\n")

# Load whatever we already have in the megalexicon, with the intention to next add to it with what we find in the input files
megalexicon = megalex.loadMegaLexicon(outfilePath)

with open(outfilePath + ".mergelog", "w") as logfile:
    logfile.write("%s\n%s\n" % (str(datetime.datetime.now()), str(sys.argv)))
    # manually patching in a couple special verbs 
    manlexicon = {}
    manlexicon[('be', 'VERB', 'TR')] = {('past', 'singular', 'first'): ['was'], ('past', 'singular', 'third'): ['was'], ('past', 'singular', 'second'): ['were'], ('past', 'plural', 'second'): ['were'], ('past', 'subjunctive'): ['were'], ('pastp'): ['been'], ('presentp',): ['being'], ('singular', 'first'): ['am'], ('singular', 'second'): ['am'], ('singular', 'third'): ['is'], ('plural',): ['are']}
    manlexicon[('be', 'VERB', 'ITR')] = manlexicon[('be', 'VERB', 'TR')]
    manlexicon[('be', 'VERB', 'AUX')] = manlexicon[('be', 'VERB', 'TR')]
    manlexicon[('wit', 'VERB', 'TR')] = {('past',): ['wist'], ('pastp'): ['wist'], ('presentp',): ['witting'], ('singular', 'first'): ['wot'], ('singular', 'second'): ['wit'], ('singular', 'third'): ['wot'], ('plural',): ['wit']}
    manlexicon[('wit', 'VERB', 'ITR')] = manlexicon[('wit', 'VERB', 'TR')]
    megalexicon = megalex.mergeMegaLexicons(megalexicon, manlexicon, logfile)
    for infilePath in sys.argv[2:]:
        if os.path.isfile(infilePath):
            print("Processing %s" % infilePath)
            newlexicon = loadAGIDLexicon(infilePath)
            # Merging AGID is a little weird, as it keeps very little lemma info compared to our own lexicon
            # As a result, the merge proceeds by identifying whether we have an entry in the lexicon that can match to an entry in AGID
            for minlemma, data in newlexicon.items():
                lemma_dt = (minlemma[0], minlemma[1], 'DTR')
                lemma_it = (minlemma[0], minlemma[1], 'ITR')
                lemma_tr = (minlemma[0], minlemma[1], 'TR')
                if lemma_dt in megalexicon:
                    megalexicon = megalex.mergeMegaLexicons(megalexicon, {lemma_dt: data}, logfile)
                if lemma_it in megalexicon:
                    megalexicon = megalex.mergeMegaLexicons(megalexicon, {lemma_it: data}, logfile)
                if lemma_tr in megalexicon:
                    megalexicon = megalex.mergeMegaLexicons(megalexicon, {lemma_tr: data}, logfile)

print("MegaLexicon updated, storing ...")
megalex.storeMegaLexicon(outfilePath, megalexicon)
print("All done.")

