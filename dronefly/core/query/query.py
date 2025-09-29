"""Naturalist information system query module."""
import datetime as dt
import re
from typing import List, Optional, Union

from attrs import define, field
from pyinaturalist.models import Place, Project, Taxon, User

from ..clients.inat import iNatClient
from ..formatters.generic import format_taxon_name, format_user_name
from ..models import Config, ControlledTermSelector, match_controlled_term
from ..parsers.constants import VALID_OBS_OPTS, VALID_OBS_SORT_BY
from .base import TaxonQuery, Query
from .taxon import match_taxon


EMPTY_QUERY = Query()


class _Params(dict):
    def set_from(self, obj: object, attr_name: str, param_name: str = None):
        """Helper for simple one-to-one attribute to param assignments."""
        if obj:
            key = param_name or attr_name
            value = getattr(obj, attr_name)
            self[key] = value


@define
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
    args["sort_by"] = query.sort_by if has_value(query.sort_by) else None
    args["order"] = query.order if has_value(query.order) else None
    return args


async def match_annotation(client, query_term: str, query_term_value: str):
    controlled_terms = await client.annotations.async_all()
    controlled_term = match_controlled_term(
        controlled_terms, query_term, query_term_value
    )
    return controlled_term


async def match_project(client, config, project_str):
    """Match project abbrev, place id, or first search result for text to search for."""
    project_id = config.project(project_str)
    if not project_id and project_id.isdigit():
        project_id = project_str
    if project_id:
        project = await anext(
            aiter(client.projects.from_ids(int(project_id))),
            None,
        )
    else:
        project = await anext(
            aiter(client.projects.search(q=project_str)),
            None,
        )
    return project


async def match_place(client, config, place_str):
    """Match place abbrev, place id, or first autocomplete result for text to search for."""
    place_id = config.place(place_str)
    if not place_id and place_str.isdigit():
        place_id = place_str
    if place_id:
        place = await anext(
            aiter(client.places.from_ids(place_id)),
            None,
        )
    else:
        place = await anext(
            aiter(client.places.autocomplete(q=place_str)),
            None,
        )
    return place


async def match_user(client, user_str):
    """Match 'me', user id, or user login."""
    if user_str == "me":
        user_id = client.ctx.author.inat_user_id
    if user_str == "any":
        return None
    if not user_id:
        user_id = user_str
    user = await anext(
        aiter(client.users.from_ids(user_id)),
        None,
    )
    return user


async def prepare_query(
    client: iNatClient, config: Config, query: Query, scientific_name=False, locale=None
):
    """Get all requested iNat entities."""
    args = get_base_query_args(query)

    if has_value(query.project):
        args["project"] = await match_project(client, config, query.project)
    else:
        args["project"] = None
    if has_value(query.place):
        args["place"] = await match_place(client, config, query.place)
    else:
        args["place"] = None
    if has_value(query.main):
        _args = {
            "scientific_name": scientific_name,
            "locale": locale,
        }
        if args["place"]:
            _args["preferred_place_id"] = args["place"].id
        args["taxon"] = await match_taxon(client, query, **_args)
    else:
        args["taxon"] = None
    for user_field in ("user", "unobserved_by", "except_by", "id_by"):
        user_attr = getattr(query, user_field)
        if has_value(user_attr):
            args[user_field] = await match_user(client, user_attr)
    if has_value(query.controlled_term):
        args["controlled_term"] = await match_annotation(client, *query.controlled_term)
    return QueryResponse(**args)


async def get_taxon_preferred_establishment_means(ctx, taxon):
    """Get the preferred establishment means for the taxon."""
    try:
        establishment_means = taxon.establishment_means
        place_id = establishment_means.place.id
        if getattr(taxon, "listed_taxa", None) is None:
            taxon = await ctx.client.taxa.populate(taxon, refresh=True)
    except (AttributeError, LookupError):
        return None

    find_means = (means for means in taxon.listed_taxa if means.place.id == place_id)
    return next(find_means, establishment_means)


@define
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
    sort_by: Optional[str] = None
    order: Optional[str] = None
    adjectives: Optional[List[str]] = field(init=False)

    def __attrs_post_init__(self):
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
        if self.sort_by:
            kwargs["order_by"] = VALID_OBS_SORT_BY.get(str(self.sort_by))
        if self.order:
            kwargs["order"] = str(self.order)
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
                        "118903": "Termitoidae",
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
                # For some commands "species and higher" filter is added only to
                # make it match results on the web. Including this in the description
                # would just be confusing.
                if lrank != "species":
                    higher_or_lower = "higher" if lrank else "lower"
                    message += " {} rank {} or {}".format(
                        with_or_and, hrank or lrank, higher_or_lower
                    )
        order_by = kwargs.get("order_by")
        order = kwargs.get("order")
        if order:
            _order = "ascending" if order == "asc" else "descending"
            message += f" in {_order} order"
        if order_by:
            _order_by = str(VALID_OBS_SORT_BY.get(order_by)).replace("_", " ")
            if order:
                message += f" by `#{_order_by}`"
            else:
                message += f" ordered by `{_order_by}`"
        return re.sub(r"^ ", "", message)
