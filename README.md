# ease_lexical_resources
A fusion of various lexical resources and scripts to use them for generation and parsing.

# Contents

megalex: a list of words with morphs and hooks to semantic models
verbcls: verb classes describing syntax and semantics of various verb frames; currently this is only VerbNET data
slm.owl: a "semantic lower model"; aka, a taxonomy of entities that lexical entries can refer to

# Sources:

Most word forms taken from AGID (the Automatically Generated Inflection Dictionary) and the ACE Lexicon. A few words added in manually based on an in-house analysis of a corpus of cooking recipes.

The semantic lower model was constructed by querying ConceptNET for superclasses for each of the lemmas in megalex. Not all lemmas have correspondents yet. Some manual work on the resulting taxonomy has been done to clean it up and align it with the Dolce UltraLite foundational ontology (DUL).

Verb semantics is currently exclusively from VerbNET, but will look into combining with Construction Grammar descriptions.

# Outputs

"Backend" scripts convert the megalex (and auxiliary files) into formats more useful for a particular NLP tool.

backend_KPML: generate a KPML lexicon. This has been tested and should work for all entries in megalex.
backend_CCG: generate an OpenCCG morph.xml file. Work in progress; currently only works for nouns, but will look into incorporating the VerbNET data.

# Issues

(Mutual) Coverage issues
* ~500 VerbNET lemmas not in megalex: these are being added by hand
* ~10000 megalex entries that are verbs but not in VerbNET: looking for ways to extend VerbNET coverage here
* ~100000 WordNET lemmas without correspondents in megalex (despite megalex already having ~50000 entries): will look into adding these automatically; at least for the morphology part of megalex, there may be automatic, or almost automatic, solutions. Note however that already the lemmas that are not in megalex tend to be somewhat exotic

Functionality issues
* CCG backend doesn't generate verb entries
* CCG backend needs testing
* megalex format: currently ad-hoc, having something more "standard" wouldn't hurt. At the very least, something to sort python dictionaries and avoid git diff catastrophes is a must.
