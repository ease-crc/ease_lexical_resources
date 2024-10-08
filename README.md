# ease_lexical_resources
A fusion of various lexical and knowledge resources and scripts to use them for inference, parsing, natural language generation.

Initially, this repository contained a list of information about words compiled from sources such as AGID. Those files are available in the lexical\_resources folder.

Currently, the focus is on a knowledge graph which contains some "commonsense" knowledge.

# What questions can the knowledge graph answer?

We have gathered information from ConceptNet, VerbNet, the CommonSense Knowledge Graph (CSKG), and with a generous dosage of manual curation we are constructing a knowledge graph to answer the following kinds of questions about houshold items:

-- what is this entity (what are its superclasses)?

-- what kinds of such entity exist (what are its subclasses)?

-- what can you do with this item? More specifically, what kinds of tasks can the item participate in and in what role.

-- what items can be used for a given task in a specified role?

-- can this item be used for this task in this role?

So, for example, the graph can answer Description Logic queries that mean questions such as "what is an apple", "what kinds of fruits are there", "what can you do with an apple", "what can be eaten", "can an apple be eaten". See below for how to ask such questions to the graph.

By task, we mean something named by an action verb, not a more detailed description. As such, a question such as "can you cut oranges with a knife?" are NOT in the scope of the knowledge graph yet. However, we are investigating ways to add more knowledge and we expect to expand the kinds of questions that it can tackle, as well as improve coverage for the existing questions.

# How to use the graph?

First, git clone this repository of course :) Then go to the src folder and run

pip install .

pip install --editable .

(Alternatively, use whatever python package installer you have instead of pip.)

Second, you will have to manually download a Konclude executable. Konclude is a Description Logic reasoner and is what we will use to perform inference with the ontology created out of this knowledge graph. You can download Konclude from here:

[https://www.derivo.de/products/konclude/download/](https://www.derivo.de/products/konclude/download/)

This is a binary archive with the precompiled executable, which you will need to decompress and make accessible to the python code responsible for performing reasoning with the ontology. Probably the easiest way to do this is to update your PATH variable to point also to the folder where the Konclude executable is. Alternatively, you can define a new environment variable called KONCLUDE\_PATH which contains the path to the Konclude executable (including the filename).

After this, you're ready to go. You can either run the dlquery.py from the src/dfl folder or import dfl.dlquery into one of your python packages and query away. You could also open the src/dfl/owl/SOMA\_DFL.owl file in a tool like Protege and use that to do queries, however with large ontologies Protege tends to become rather slow.

Have a look at the wiki for examples on how to run queries.

# Query an Ontology? I thought this was a Knowledge Graph?

Some of the knowledge we use comes in the form of ontologies (DUL, SOMA) which made it a natural choice to use ontologies and their associated DL inferencing techniques for now. However, at some point in the not too far future we would like to do inference in a different formal system (defeasible logic). Therefore, we have decided to keep a "knowledge graph" as a kind of neutral representation, and write methods to convert this into axioms/rules in whatever formalism we do reasoning in. If you like, you can think of this a little like the "knowledge graph" being a source code, which is then compiled into a form that can be executed on some platform (whether that platform is DL inferencing or defeasible inferencing remains to be decided).

# Where is all this "knowledge" coming from?

The list is currently ConceptNet 5.8, VerbNet 2.1, WordNet 3.1, CSKG, SOMA, DUL+DnS 4.0. The details of how the knowledge was gathered will be documented in the wiki.

However, a lot of manual work was also needed to adjust the taxonomies and relations coming from ConceptNet/CSKG, both in terms of correcting some suspicious relations, as well as adding items about household items that should have been present but were not there in ConceptNet/CSKG. As such, copying something like the ConceptNet knowledge graph will NOT result in the same graph as SOMA\_DFL.

# How do entities in your "knowledge graph"/"ontology" relate to entities from other knowledge graphs/ontologies?

The name of an entity in our knowledge graph indicates which ConceptNet entity it corresponds to. Further, the ConceptNet entities we are using in our knowledge graph all have mappings to WordNet synsets. Therefore, if our graph makes claims about some entity X, you can compare what another knowledge graph says about X as long as this other knowledge graph uses WordNet synsets or ConceptNet concepts as a way to name entities. Of course, what we are saying about those entities might differ; this comes with the territory when fixing some knowledge items relative to e.g. ConceptNet. , 

In our graph we use ConceptNet-style names rather than WordNet synsets. This is because ConceptNet names tend to be more human-readable than WordNet synset identifiers. The readability comes at a cost however: many ConceptNet concepts map to several synsets, with important implications for the semantics of a concept. E.g., ConceptNet confuses an electric jack and a piece of material used as a stopper under "plug.n.wn.artifact". We often split up such ambiguous ConceptNet concepts so that SOMA\_DFL does not include many ambiguous concepts. For example, 'watercolor.n.wn.artifact' means both "a water-base paint with water-soluble pigments", and "a painting made with watercolors". Instead, we have concepts whose names add a suffix to their ConceptNet names, e.g. 'watercolor.n.wn.artifact..paint' and 'watercolor.n.wn.artifact..painting', with the double dot marking the beginning of our added suffix.

Note that a name of an entity in our knowledge graph is not exactly the same as its ConceptNet name, but the conversion is very straightforward. For example, "plug.n.wn.artifact" from SOMA\_DFL corresponds to "/c/en/plug/n/wn/artifact" in ConceptNet. One complication is that ConceptNet names may contain the ' character, which is not allowed in concept names in OWL Functional notation. Therefore, we replace the ' chatacter with a different sequence. So, for example ConceptNet "/c/en/plumber's\_snake/n/wn/artifact" becomes "plumber\_ZZ\_s_snake.n.wn.artifact" in SOMA\_DFL.
