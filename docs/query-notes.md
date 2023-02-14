# Parser and query language

This document will formally describe the query language as it ought to be (not necessarily how it is as of writing). In particular:

- `NaturalParser` currently accepts `of` but nobody uses it and that makes it needlessly complex.  
- The fundamental `Word` unit now excludes both comma `,` and equals `=`, something the current parser does not enforce.
- The `TaxonSelector` accepts a comma-delimited list of one or more taxa, something that is only implemented in `GroupKeyword` expansions.
- The `opt` `Option` is not described yet (and really should be eliminated in favour of making those things first-class entities in the language instead!)
- This description glosses over our substitution of certain pairs of unquoted keywords, e.g. `id by` with `id-by`, etc.
    - i.e. that should be part of a tokenizing pass that is not really explained below

## (In)formal description of query language

Currently expressed informally in English, but should be expressed in formally. There may be errors and omissions below ...

### Tokens

The tokenizer should:

- return double-quote as a separate token
- return any sequence of non-double-quote, non-blank characters as a separate token

## Draft language specification

### TODO

- handle "id", "not", "except", "in", "added" as OPTION_WORDS in the language
    - e.g.
	  `IdByOptionKeyword` is (`id` + `by`) or `idby` or `id-by`, etc.
    - but generalize this instead of a new named entity per? e.g.
      `DOUBLE_OPTION_WORDS = { "id": ["by"], "not": ["by"], "except": ["by"], "in": ["prj"], "added": ["on", "since", "until"] }`
    - etc.

### Tokens

`OPTION_WORDS = ["by", "id-by", "not-by", "except-by", "from", "in-prj", "on", "since", "until", "added-on", "added-since", "added-until", "opt", "rank", "with", "per"]`  

`MACRO_WORDS = ["rg", "nid", "oldest", "newest", "reverse", "my", "home", "faves", "spp", "species", "unseen"]`  

`GROUP_WORDS = ["unknown", "waspsonly", "mothsonly", "herps", "lichenish", "nonflowering", "nonvascular", "inverts", "seaslugs", "allfish"]`  

`KEYWORDS = OPTION_WORDS + MACRO_WORDS + GROUP_WORDS`

A `PlainWord` is:

- one or more non-blank, non-comma, non-equals characters

An `AlphaWord` is:

- one or more alphabetic characters
  
An `AlphaDash` is:

- an alphabetic character OR (`-` + alphabetic character)

An `AlphaDashWord` is:

- an alphabetic character + (zero or more `AlphaDash`)

A `Word` is:

- an `AlphaWord` OR `AlphaDashWord` OR `PlainWord`

An `UnquotedWord` is:

- a `Word` that is not a double-quote `"`

An `Id` is:

- one or more digits  

An `OptionKeyword` is:

- an `AlphaDashWord` in `OPTION_WORDS`

A `MacroKeyord` is:

- an `AlphaDashWord` in `MACRO_WORDS`

A `GroupKeyword` is:

- an `AlphaDashWord` in `GROUP_WORDS`
 
A `NonKeyword` is:

- an (`AlphaDashWord` not in `KEYWORDS`) OR `Word`

An `UnquotedNonkeyword` is:

- a `NonKeyword` that is not a double-quote `"`
  
An `AlphaNonKeyword` is:

- an `AlphaWord` not in `KEYWORDS`

A `FourLetterCode` is:

- an `AlphaNonKeyword` with length 4

### Token groups

A `QuotedWords` is:

- `"` + (one or more `UnquotedWord`) + `"`

An `OptionWords` is:

- one or more (`QuotedWords` OR `UnquotedNonkeyword`)

A `TaxonWords` is:

- a `FourLetterCode` OR `OptionWords`

### Selectors and Options
  
An `InSelector` is:

- `"in"` + `TaxonWords`

A `TaxonSelector` is:

- a comma-delimited list of one or more of:
	+  an `Id` OR  
	+  a `GroupKeyword` OR
	+  a `TaxonWords` + (zero or one `InSelector`)

An `Option` is:

- a `MacroKeyword` OR `GroupKeyword` OR (`OptionKeyword` + `OptionWords`)

A `Query` is:  
  
- (zero or more `MacroKeyword`) + (zero or one `TaxonSelector`) + (zero or more `Option`)
- that is non-empty

## Query object  

Some notes on what the `Query` object should contain from the parsed query language string:

+ original unparsed string
+ parsed
	+ macro(s)
		* list of macros
    + taxon selector(s)
    + place selector(s)
    + controlled term selector(s)
    + project selector(s)
    + user selector(s)
	    * observed by
	    * unobserved by
	    * identified by
    + date selector(s)
	    * observed on since
	    * observed on until
	    * observed on
	    * added on since
	    * added on until
	    * added on
    + per
    + options
	    * sort by
	    * quality grade
	    * has photos
	    * has sounds

## Mapping a URL back to a Query

One thing I've always wanted is the ability to recognize an observation URL pasted into chat, analyze it, and come up with an equivalent query in our query language: 

- id# -> scientific name
	+ disambiguate when more than 1: 'in plantae', 'in animalia'
- place# -> abbreviation or slug with '-' replaced with ' '
- user# -> login
- project# -> abbreviation or slug with '-' replaced with ' '
- etc.

