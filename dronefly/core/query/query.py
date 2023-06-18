"""Naturalist information system query module."""
from attrs import define
from dataclasses import dataclass, field
import datetime as dt
import re
from typing import List, Optional, Union

from dronefly.core.formatters.generic import format_taxon_name, format_user_name
from dronefly.core.models.controlled_terms import ControlledTermSelector
from dronefly.core.parsers.constants import VALID_OBS_OPTS
from pyinaturalist.models import Place, Project, Taxon, User


@define
class TaxonQuery:
    """A taxon query composed of terms and/or phrases or a code or taxon_id, filtered by ranks."""

    taxon_id: Optional[int] = None
    terms: Optional[List[str]] = None
    phrases: Optional[List[str]] = None
    ranks: Optional[List[str]] = None
    code: Optional[str] = None
    _query: Optional[str] = None

    def _add_term(self, item):
        if item:
            if isinstance(item, list):
                formatted_item = " ".join(item)
            else:
                formatted_item = str(item)
            self._query += " " + formatted_item if self._query else formatted_item

    def __str__(self):
        self._query = ""
        self._add_term(self.taxon_id)
        self._add_term(self.terms)
        # TODO: support mixture of terms and phrases better
        # - currently all phrases will be rendered unquoted as terms,
        #   so we lose information that was present in the input
        # self._add_term(self.phrases)
        self._add_term(self.ranks)
        self._add_term(self.code)
        return self._query


@define
class Query:
    """Naturalist information system query.

    A naturalist information system query is generally composed of one or more
    "who", "what", "when", & "where" clauses. This class provides both a single
    representation of those parts that can be applied to looking things up on
    different information systems and also a common grammar and syntax for users
    to learn to make requests across all systems.

    - the "who" is the person or persons related to the data
    - the "what" is primarily taxa or records related to one or more taxa
    - the "when" is the date/times or date/time periods relating to the data
    - the "where" is the place associated with the data
    - some additional options controlling retrieval and presentation of the
      data may also be a part of the query

    While this query class was initially written to cater to the kinds of
    requests directly supported through the iNaturalist API, it is not
    intended to be limited to making requests from that site. Many sites
    support subsets of what iNat API can do, and so the applicable parts
    of the query & grammar can be used to fetch material from those sites.

    Options governing "who":

    - "by", "not by", "id by" identify people related to the data
    - "by" is the author of the data (e.g. observer)
    - other "who" options indicate different roles of the people relating
      to the requested data

    Options governing "what":

    - "of" matches taxon names or id numbers
    - the taxon query can further be qualified by:
        - double-quoted phrases to express exact phrase match for some or
          all of the name
    - "rank" returns only taxa matching the specified rank or ranks
        - can be combined with "in" to return child taxa of taxon,
          with or without "of" to match specific names
    - "in" specifies the ancestor taxon of child taxa matching the
      "of" and/or "in" options
    - "with" are controlled terms that select only data with particular
      attributes
    - A "per" option influences which entities or groupings of entities
      are requested, where that is not otherwise imposed by the kind of
      query performed.

    Options governing "where":

    - "from" identifies a place associated with the data

    Options governing "when":

    - "when" features:
        - "on", "since", and "until" are always inclusive of the date given
        - the assumed date is the date associated with the record itself, and
          not the date it was added to the system
        - the "added" qualifier can be combined with these three option keywords
          to request the date the record was added instead

    Options that don't neatly fit into the above:

    - "project" is a fairly iNaturalist-specific concept
    - A generic "opt" option is provided to pass through miscellaneous
      options to the information system APIs not neatly falling into these
      categories, like "order" and "order by".
        - Because these are often highly dependent on the specific information
          systems involved, these are not treated as an integral part of our
          who, what, when, and where concepts.
    """

    main: Optional[TaxonQuery] = None
    ancestor: Optional[TaxonQuery] = None
    user: Optional[str] = None
    place: Optional[str] = None
    controlled_term: Optional[str] = None
    unobserved_by: Optional[str] = None
    except_by: Optional[str] = None
    id_by: Optional[str] = None
    per: Optional[str] = None
    project: Optional[str] = None
    options: Optional[List] = None
    obs_d1: Optional[List] = None
    obs_d2: Optional[List] = None
    obs_on: Optional[List] = None
    added_d1: Optional[List] = None
    added_d2: Optional[List] = None
    added_on: Optional[List] = None
    _query: Optional[str] = None

    def _add_clause(self, fmt, item):
        if item:
            if isinstance(item, list):
                formatted_item = fmt.format(" ".join(item))
            else:
                formatted_item = fmt.format(item)
            self._query += " " + formatted_item if self._query else formatted_item

    def __str__(self):
        self._query = ""
        if self.main:
            self._add_clause("{}", str(self.main))
        if self.ancestor:
            self._add_clause("in {}", str(self.ancestor))
        self._add_clause("from {}", self.place)
        self._add_clause("in prj {}", self.project)
        self._add_clause("by {}", self.user)
        self._add_clause("id by {}", self.id_by)
        self._add_clause("not by {}", self.unobserved_by)
        self._add_clause("except by {}", self.except_by)
        self._add_clause("with {}", self.controlled_term)
        self._add_clause("per {}", self.per)
        self._add_clause("opt {}", self.options)
        self._add_clause("since {}", self.obs_d1)
        self._add_clause("until {}", self.obs_d2)
        self._add_clause("on {}", self.obs_on)
        self._add_clause("added since {}", self.added_d1)
        self._add_clause("added until {}", self.added_d2)
        self._add_clause("added on {}", self.added_on)
        return self._query


EMPTY_QUERY = Query()


class _Params(dict):
    def set_from(self, obj: object, attr_name: str, param_name: str = None):
        """Helper for simple one-to-one attribute to param assignments."""
        if obj:
            key = param_name or attr_name
            value = getattr(obj, attr_name)
            self[key] = value


@dataclass
class DateSelector:
    """A date selector object."""

    # pylint: disable=invalid-name

    d1: Optional[Union[dt.datetime, str]]
    d2: Optional[Union[dt.datetime, str]]
    on: Optional[Union[dt.datetime, str]]


def has_value(arg):
    """Return true if arg is present and is not the `any` special keyword.

    Use `any` in a query where a prior non-empty clause is present,
    and that will negate that clause.
    """
    if not arg:
        return False
    if isinstance(arg, list):
        return arg[0] and arg[0].lower() != "any"
    elif isinstance(arg, TaxonQuery):
        return (
            (arg.terms and arg.terms[0].lower() != "any")
            or arg.code
            or arg.phrases
            or arg.ranks
            or arg.taxon_id
        )
    elif isinstance(arg, dt.datetime):
        return True
    else:
        return arg.lower() != "any"


def _get_options(query_options: list):
    options = {}
    # Accept a limited selection of options:
    # - all of these to date apply only to observations, though others could
    #   be added later
    # - all options and values are lowercased
    for (key, *val) in map(lambda opt: opt.lower().split("="), query_options):
        val = val[0] if val else "true"
        # - conservatively, only alphanumeric, comma, dash or
        #   underscore characters accepted in values so far
        # - TODO: proper validation per field type
        if key in VALID_OBS_OPTS and re.match(r"^[a-z0-9,_-]*$", val):
            options[key] = val
    return options


def get_base_query_args(query):
    args = {}
    args["options"] = _get_options(query.options) if has_value(query.options) else None
    _observed = {}
    _observed["on"] = query.obs_on if has_value(query.obs_on) else None
    _observed["d1"] = query.obs_d1 if has_value(query.obs_d1) else None
    _observed["d2"] = query.obs_d2 if has_value(query.obs_d2) else None
    args["observed"] = DateSelector(**_observed)
    _added = {}
    _added["on"] = query.added_on if has_value(query.added_on) else None
    _added["d1"] = query.added_d1 if has_value(query.added_d1) else None
    _added["d2"] = query.added_d2 if has_value(query.added_d2) else None
    args["added"] = DateSelector(**_added)
    return args


@dataclass
class QueryResponse:
    """A generic query response object.

    - The parsed QueryResponse contains zero or more objects that are already
      each queried against the API and, optionally some additional options to
      apply to secondary entity queries. It is used in these main contexts:
      - Accessing the details of the primary entity object.
      - One or more queries for secondary entities related to the primary entity
        (e.g. observations).
    - For example, the command `,taxon rg bees by ben` transforms the query as follows:
      - `bees` is queried and parsed into a `Taxon` object for `/taxa/630955-Anthophila`
      - `ben`, in the context of a Discord server where this user is registered
        and is the best match, is parsed into a `User` object for `/people/benarmstrong`
        (which very likely can be fetched from cache)
      - `rg` is a macro for `"opt": {"quality_grade": "research"}`
      - The primary entity displayed by the `,taxon` command is `Anthophila`.
      - The secondary entities are observations & species counts of
        `Anthophila` for `benarmstrong` that are `research grade`, shown as a
        subdisplay.
    """

    taxon: Optional[Taxon] = None
    user: Optional[User] = None
    place: Optional[Place] = None
    unobserved_by: Optional[User] = None
    except_by: Optional[User] = None
    id_by: Optional[User] = None
    project: Optional[Project] = None
    options: Optional[dict] = None
    controlled_term: Optional[ControlledTermSelector] = None
    observed: Optional[DateSelector] = None
    added: Optional[DateSelector] = None
    adjectives: Optional[List[str]] = field(init=False)

    def __post_init__(self):
        adjectives = []
        if self.options:
            quality_grade = (self.options.get("quality_grade") or "").split(",")
            verifiable = self.options.get("verifiable")
            if "any" not in quality_grade:
                research = "research" in quality_grade
                needsid = "needs_id" in quality_grade
            # If specified, will override any quality_grade set already:
            if verifiable:
                if verifiable in ["true", ""]:
                    research = True
                    needsid = True
            if verifiable == "false":
                adjectives.append("*not Verifiable*")
            elif research and needsid:
                adjectives.append("*Verifiable*")
            else:
                if research:
                    adjectives.append("*Research Grade*")
                if needsid:
                    adjectives.append("*Needs ID*")
        self.adjectives = adjectives

    def obs_args(self):
        """Arguments for an observations query."""

        kwargs = _Params({"verifiable": "true"})
        kwargs.set_from(self.taxon, "id", "taxon_id")
        kwargs.set_from(self.user, "id", "user_id")
        kwargs.set_from(self.project, "id", "project_id")
        kwargs.set_from(self.place, "id", "place_id")
        kwargs.set_from(self.id_by, "id", "ident_user_id")
        kwargs.set_from(self.unobserved_by, "id", "unobserved_by_user_id")
        kwargs.set_from(self.except_by, "id", "not_user_id")
        if self.unobserved_by:
            kwargs["lrank"] = "species"
        if self.controlled_term:
            kwargs["term_id"] = self.controlled_term.term.id
            kwargs["term_value_id"] = self.controlled_term.value.id
        # In three cases, we need to allow verifiable=any:
        # 1. when a project is given, let the project rules sort it out, otherwise
        #    we interfere with searching for observations in projects that allow
        #    unverifiable observations
        # 2. when a user is given, which is like pressing "View All" on a taxon
        #    page, we want to match that feature on the website, i.e. users will
        #    be confused if they asked for their observations and none were given
        #    even though they know they have some
        # 3. same with 'id by' and for the same reason as =any for user
        #
        # - 'not by' is not the same. It's the target species a user will
        #   be looking for and it is undesirable to include unverifiable observations.
        # - if these defaults don't work for corner cases, they can be
        #   overridden in the query with: opt verifiable=<value> (i.e.
        #   self.options overrides are applied below)
        if (
            kwargs.get("project_id")
            or kwargs.get("user_id")
            or kwargs.get("ident_user_id")
        ):
            kwargs["verifiable"] = "any"
        if self.options:
            kwargs = {**kwargs, **self.options}
        if self.observed:
            if self.observed.on:
                kwargs["observed_on"] = str(self.observed.on.date())
            else:
                if self.observed.d1:
                    kwargs["d1"] = str(self.observed.d1.date())
                if self.observed.d2:
                    kwargs["d2"] = str(self.observed.d2.date())
        if self.added:
            if self.added.on:
                kwargs["created_on"] = str(self.added.on.date())
            else:
                if self.added.d1:
                    kwargs["created_d1"] = self.added.d1.isoformat()
                if self.added.d2:
                    kwargs["created_d2"] = self.added.d2.isoformat()
        return kwargs

    def obs_query_description(self, with_adjectives: bool = True):
        """Description of an observations query."""

        def _format_date(date: str):
            return date.strftime("%b %-d, %Y")

        def _format_time(time: str):
            return time.strftime("%b %-d, %Y %h:%m %p")

        message = ""
        of_taxa_description = ""
        without_taxa_description = ""
        if self.taxon:
            taxon = self.taxon
            of_taxa_description = format_taxon_name(taxon, with_term=True)
        if self.options:
            without_taxon_id = self.options.get("without_taxon_id")
            iconic_taxa = self.options.get("iconic_taxa")
            if iconic_taxa == "unknown":
                of_taxa_description = "Unknown"
            else:
                taxon_ids = self.options.get("taxon_ids")
                # Note: if taxon_ids is given with "of" clause (taxon_id), then
                # taxon_ids is simply ignored, so we don't handle that case here.
                if taxon_ids and not self.taxon:
                    # TODO: support generally; hardwired cases here are for herps,
                    # lichenish, and seaslugs
                    of_taxa_description = {
                        "20978,26036": "Amphibia, Reptilia (Herps)",
                        ("152028,54743,152030,175541,127378,117881,117869,175246"): (
                            "Lecanoromycetes, Arthoniomycetes, etc. (Lichenized Fungi)"
                        ),
                        (
                            "130687,775798,775804,49784,500752,47113,"
                            "775801,775833,775805,495793,47801,801507"
                        ): (
                            "Nudibranchia, Aplysiida, etc. (Nudibranchs, Sea Hares, "
                            "other marine slugs)"
                        ),
                        "47178,47273,797045,85497": (
                            "Actinopterygii, Agnatha, Elasmobranchii, Sarcopterygii "
                            "(Extant Fish)"
                        ),
                    }.get(taxon_ids) or "taxon #" + taxon_ids.replace(",", ", ")
                # Note: "without" for each of these taxa are intentionally
                # omitted from the "lichenish" description to keep it from
                # being needlessly wordy.
                if without_taxon_id and without_taxon_id not in [
                    "372831,1040687,1040689,352459"
                ]:
                    # TODO: support generally; hardwired cases here are for
                    # waspsonly, mothsonly, lichenish, etc.
                    without_taxa_description = {
                        "47336,630955": "Formicidae, Anthophila",
                        "47224": "Papilionoidea",
                        "47125": "Angiospermae",
                        "211194": "Tracheophyta",
                        "355675": "Vertebrata",
                    }.get(without_taxon_id) or "taxon #" + without_taxon_id.replace(
                        ",", ", "
                    )

        _taxa_description = []
        if of_taxa_description:
            _of = ["of"]
            if with_adjectives and self.adjectives:
                _of.append(", ".join(self.adjectives))
            _of.append(of_taxa_description)
            _taxa_description.append(" ".join(_of))
        if without_taxa_description:
            _without = []
            # If we only have "without" =>
            #   "of [adjectives] taxa without [taxa]":
            if not of_taxa_description and with_adjectives:
                _without.append("of")
                if with_adjectives and self.adjectives:
                    _without.append(", ".join(self.adjectives))
                _without.append("taxa")
            _without.append("without")
            _without.append(without_taxa_description)
            _taxa_description.append(" ".join(_without))
        if with_adjectives and not _taxa_description:
            _of = ["of"]
            if with_adjectives and self.adjectives:
                _of.append(", ".join(self.adjectives))
            _of.append("taxa")
            _taxa_description.append(" ".join(_of))
        message += " ".join(_taxa_description)
        if self.project:
            message += " in " + self.project.title
        elif self.options:
            project_id = self.options.get("project_id")
            if project_id:
                message += " in project #" + project_id.replace(",", ", ")
        if self.place:
            message += " from " + self.place.display_name
        elif self.options:
            place_id = self.options.get("place_id")
            if place_id:
                message += " from place #" + place_id.replace(",", ", ")
        if self.user:
            message += " by " + format_user_name(self.user)
        elif self.options:
            user_id = self.options.get("user_id")
            if user_id:
                message += " by user #" + user_id.replace(",", ", ")
        if self.unobserved_by:
            message += " unobserved by " + format_user_name(self.unobserved_by)
        if self.id_by:
            message += " identified by " + format_user_name(self.id_by)
        if self.except_by:
            message += " except by " + format_user_name(self.except_by)
        if self.observed and self.observed.on or self.observed.d1 or self.observed.d2:
            message += " observed "
            if self.observed.on:
                message += f" on {_format_date(self.observed.on)}"
            else:
                if self.observed.d1:
                    message += f" on or after {_format_date(self.observed.d1)}"
                if self.observed.d2:
                    if self.observed.d1:
                        message += " and "
                    message += f" on or before {_format_date(self.observed.d2)}"
        if self.added and self.added.on or self.added.d1 or self.added.d2:
            message += " added "
            if self.added.on:
                message += f" on {_format_date(self.observed.on)}"
            else:
                if self.added.d1:
                    message += f" on or after {_format_time(self.added.d1)}"
                if self.added.d2:
                    if self.added.d1:
                        message += " and "
                    message += f" on or before {_format_time(self.added.d2)}"
        if self.controlled_term:
            (term, term_value) = self.controlled_term
            desc = f" with {term.label}"
            desc += f" {term_value.label}"
            message += desc
        kwargs = self.obs_args()
        hrank = kwargs.get("hrank")
        lrank = kwargs.get("lrank")
        if lrank or hrank:
            with_or_and = "with" if not self.controlled_term else "and"
            if lrank and hrank:
                message += " {} rank from {} through {}".format(
                    with_or_and, lrank, hrank
                )
            else:
                higher_or_lower = "higher" if lrank else "lower"
                message += " {} rank {} or {}".format(
                    with_or_and, hrank or lrank, higher_or_lower
                )
        return re.sub(r"^ ", "", message)
