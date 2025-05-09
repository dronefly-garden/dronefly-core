"""Generic text formatters.

Anything more complicated than plain text can be rendered in Markdown,
which is then fairly easy to render to other formats as needed.
"""
from __future__ import annotations
import copy
from datetime import datetime as dt
import re
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from dronefly.core.query.query import QueryResponse
    from dronefly.core.menus.taxon_list import TaxonListSource

import html2markdown
import inflect
from pyinaturalist import (
    ConservationStatus,
    EstablishmentMeans,
    JsonResponse,
    ListedTaxon,
    Observation,
    Taxon,
    TaxonSummary,
    User,
)
from pyinaturalist.constants import ROOT_TAXON_ID

from ..constants import (
    TAXON_PRIMARY_RANKS,
    TRINOMIAL_ABBR,
    RANK_LEVELS,
)
from ..models.taxon_list import TaxonListMetadata
from ..utils import included_ranks
from .constants import (
    ICONS,
    WWW_BASE_URL,
)
from dronefly.core.utils import lifelists_url_from_query_response, obs_url_from_v1

MEANS_LABEL_DESC = {
    "endemic": "endemic to",
    "native": "native in",
    "introduced": "introduced to",
}

MEANS_LABEL_EMOJI = {
    "endemic": "\N{SPARKLE}",
    "native": "\N{LARGE GREEN SQUARE}",
    "introduced": "\N{UP-POINTING SMALL RED TRIANGLE}",
}

TAXON_LIST_DELIMITER = [", ", " > "]

# TODO: the seed idea here is to act on & render spoilered commands and displays,
#   e.g. `,obs my ||gory observation taxon||`
#   - images would be fetched, then uploaded with spoilers
# SPOILER_PAT = re.compile(r"\|\|")
# DOUBLE_BAR_LIT = "\\|\\|"

_MARKDOWN_ESCAPE_SUBREGEX = "|".join(
    r"\{0}(?=([\s\S]*((?<!\{0})\{0})))".format(c) for c in ("*", "`", "_", "~", "|")
)
_MARKDOWN_ESCAPE_COMMON = r"^>(?:>>)?\s|\[.+\]\(.+\)"
_MARKDOWN_ESCAPE_REGEX = re.compile(
    rf"(?P<markdown>{_MARKDOWN_ESCAPE_SUBREGEX}|{_MARKDOWN_ESCAPE_COMMON})",
    re.MULTILINE,
)
_URL_REGEX = r"(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])"
_MARKDOWN_STOCK_REGEX = rf"(?P<markdown>[_\\~|\*`]|{_MARKDOWN_ESCAPE_COMMON})"

p = inflect.engine()
p.defnoun("phylum", "phyla")
p.defnoun("subphylum", "subphyla")
p.defnoun("subgenus", "subgenera")


def protect_leading_blanks(text: str = ""):
    return re.sub(r"^( +)", "\N{ZERO WIDTH SPACE}" + r"**\1**", text)


def escape_markdown(
    text: str, *, as_needed: bool = False, ignore_links: bool = True
) -> str:
    r"""A helper function that escapes Discord's markdown.

    Parameters
    -----------
    text: :class:`str`
        The text to escape markdown from.
    as_needed: :class:`bool`
        Whether to escape the markdown characters as needed. This
        means that it does not escape extraneous characters if it's
        not necessary, e.g. ``**hello**`` is escaped into ``\*\*hello**``
        instead of ``\*\*hello\*\*``. Note however that this can open
        you up to some clever syntax abuse. Defaults to ``False``.
    ignore_links: :class:`bool`
        Whether to leave links alone when escaping markdown. For example,
        if a URL in the text contains characters such as ``_`` then it will
        be left alone. This option is not supported with ``as_needed``.
        Defaults to ``True``.

    Returns
    --------
    :class:`str`
        The text with the markdown special characters escaped with a slash.

    Taken from https://github.com/Rapptz/discord.py/blob/master/discord/utils.py
    """

    if not as_needed:

        def replacement(match):
            groupdict = match.groupdict()
            is_url = groupdict.get("url")
            if is_url:
                return is_url
            return "\\" + groupdict["markdown"]

        regex = _MARKDOWN_STOCK_REGEX
        if ignore_links:
            regex = f"(?:{_URL_REGEX}|{regex})"
        return re.sub(regex, replacement, text, 0, re.MULTILINE)
    else:
        text = re.sub(r"\\", r"\\\\", text)
        return _MARKDOWN_ESCAPE_REGEX.sub(r"\\\1", text)


def format_datetime(time, compact=False):
    """Format datetime with compact option that drops less relevant parts."""
    hour = time.strftime("%I").lstrip("0")
    minute = time.strftime("%M")
    am_pm = time.strftime("%p").lower()
    day = time.strftime("%d").lstrip("0")
    mon = time.strftime("%b")
    year = time.strftime("%Y")
    if compact:
        if time.date() == dt.now().date():
            formatted_time = f"{hour}:{minute}{am_pm}"
        elif time.year == dt.now().year:
            formatted_time = f"{day}-{mon}"
        else:
            formatted_time = f"{mon}-{year}"
    else:
        wday = time.strftime("%a")
        formatted_time = f"{wday} {mon} {day}, {year} · {hour}:{minute} {am_pm}"
    return formatted_time


def format_taxon_list_summary(meta: TaxonListMetadata):
    total = f"Total: {meta.taxon_count} {meta.ranks}"
    if meta.rank_totals:
        rank_keys = reversed(
            [rank for rank in RANK_LEVELS.keys() if rank != "stateofmatter"]
        )
        rank_totals_by_rank = [
            meta.rank_totals[rank] for rank in rank_keys if meta.rank_totals.get(rank)
        ]
        response = "\n\n".join(["\n".join(rank_totals_by_rank), total])
    else:
        response = total
    return response


def format_user_name(user: User):
    """Format user's display name with Markdown special characters escaped."""
    if user.name:
        return f"{escape_markdown(user.name)} ({escape_markdown(user.login)})"
    return escape_markdown(user.login)


def format_user_url(user: User):
    """Format user's profile url using their login name instead of user id."""
    return f"{WWW_BASE_URL}/people/{user.login}" if user.login else ""


def format_user_link(user: User):
    """Format user's profile link as Markdown."""
    return f"[{format_user_name(user)}]({format_user_url(user)})"


def format_link(link_text: str, url: str):
    return f"[{link_text}]({url})" if url else link_text


def format_taxon_establishment_means(
    means: Union[EstablishmentMeans, ListedTaxon],
    all_means: bool = False,
    list_title: bool = False,
):
    """Format the estalishment means for a taxon for a given place.

    Parameters:
    -----------
    means: EstablishmentMeans
        The EstablishmentMeans for the taxon at the given place.
    all_means: bool
        Whether or not to include means that normally are not shown (e.g. unknown).
    list_title: bool
        Whether or not to include the list title.

    Returns:
    --------
    str
        A Markdown-formatted string containing the means, if shown, with emoji
        and link to establishment means on the web.
    """
    label = means.establishment_means
    description = MEANS_LABEL_DESC.get(label)
    if description is None:
        if not all_means:
            return None
        full_description = f"Establishment means {label} in {means.place.display_name}"
    else:
        full_description = f"{description} {means.place.display_name}"
    try:
        emoji = MEANS_LABEL_EMOJI[means.establishment_means] + "\u202f"
    except KeyError:
        emoji = ""
    url = f"{WWW_BASE_URL}/listed_taxa/{means.id}"
    if list_title and isinstance(means, ListedTaxon) and means.list.title:
        _means = f"{emoji}{full_description} {format_link(means.list.title, url)}"
    else:
        _means = f"{emoji}{format_link(full_description, url)}"
    return _means


def format_taxon_conservation_status(
    status: ConservationStatus,
    brief: bool = False,
    inflect: bool = False,
):
    """Format the conservation status for a taxon for a given place.

    Parameters:
    -----------
    status: ConservationStatus
        The ConservationStatus for the taxon at the given place.
    brief: bool
        Whether to return brief format for use in brief taxon description
        or full format that also includes the name of the authority.
    inflect: bool
        Whether to inflect first word in status and precede with indefinite
        article for use in a sentence, e.g. "an endangered", "a secure", etc.

    Returns:
    --------
    str
        A Markdown-formatted string containing the conservation status
        with link to the status on the web.
    """
    description = status.display_name

    if brief:
        linked_status = format_link(description, status.url)
        if inflect:
            # inflect statuses with single digits in them correctly
            first_word = re.sub(
                r"[0-9]",
                " {0} ".format(p.number_to_words(r"\1")),
                description,
            ).split()[0]
            article = p.a(first_word).split()[0]
            full_description = " ".join((article, linked_status))
        else:
            full_description = linked_status
    else:
        linked_status = format_link(status.authority, status.url)
        full_description = f"{description} ({linked_status})"

    return full_description


def format_taxon_names(
    taxa: list[Taxon],
    with_term=False,
    names_format="%s",
    max_len=0,
    hierarchy=False,
    lang=None,
):
    """Format names of taxa from matched records.

    Parameters
    ----------
    taxa: list[Taxon]
        A list of Taxon records to format, either as a comma-delimited list or
        in a hierarchy.
        - If hierarchy=True, these must be in highest to lowest rank order.
    with_term: bool, optional
        With non-common / non-name matching term in parentheses in place of common name.
    names_format: str, optional
        Format string for the name. Must contain exactly one %s.
    max_len: int, optional
        The maximum length of the return str, with ', and # more' appended if they
        don't all fit within this length.
    hierarchy: bool, optional
        If specified, formats a hierarchy list of scientific names with
        primary ranks bolded & starting on a new line, and delimited with
        angle-brackets instead of commas.
    lang: str, optional
        If specified, prefer the first name with its locale == lang instead of
        the preferred_common_name.


    Returns
    -------
    str
        A delimited list of formatted taxon names.
    """

    delimiter = TAXON_LIST_DELIMITER[int(hierarchy)]

    names = [
        format_taxon_name(taxon, with_term=with_term, hierarchy=hierarchy, lang=lang)
        for taxon in taxa
    ]

    def fit_names(names):
        names_fit = []
        # Account for space already used by format string (minus 2 for %s)
        available_len = max_len - (len(names_format) - 2)

        def more(count):
            return "and %d more" % count

        def formatted_len(name):
            return sum(len(item) + len(delimiter) for item in names_fit) + len(name)

        def overflow(name):
            return formatted_len(name) > available_len

        for name in names:
            if overflow(name):
                unprocessed = len(names) - len(names_fit)
                while overflow(more(unprocessed)):
                    unprocessed += 1
                    del names_fit[-1]
                names_fit.append(more(unprocessed))
                break
            else:
                names_fit.append(name)
        return names_fit

    if max_len:
        names = fit_names(names)

    return names_format % delimiter.join(names)


def format_taxon_name(
    taxon: Taxon,
    with_term=False,
    hierarchy=False,
    with_rank=True,
    with_common=True,
    lang=None,
):
    """Format taxon name.

    Parameters
    ----------
    taxon: Taxon
        The taxon to format.
    with_term: bool, optional
        When with_common=True, non-common / non-name matching term is put in
        parentheses in place of common name.
    hierarchy: bool, optional
        If specified, produces a list item suitable for inclusion in the hierarchy section
        of a taxon embed. See format_taxon_names() for details.
    with_rank: bool, optional
        If specified and hierarchy=False, includes the rank for ranks higher than species.
    with_common: bool, optional
        If specified, include common name in parentheses after scientific name.
    lang: str, optional
        If specified, prefer the first name with its locale == lang instead of
        the preferred_common_name.

    Returns
    -------
    str
        A name of the form "Rank Scientific name (Common name)" following the
        same basic format as iNaturalist taxon pages on the web, i.e.

        - drop the "Rank" keyword for species level and lower
        - italicize the name (minus any rank abbreviations; see next point) for genus
        level and lower
        - for trinomials (must be subspecies level & have exactly 3 names to qualify),
        insert the appropriate abbreviation, unitalicized, between the 2nd and 3rd
        name (e.g. "Anser anser domesticus" -> "*Anser anser* var. *domesticus*")
    """

    def get_common_name():
        preferred_common_name = None
        if lang and taxon.names:
            name = next(
                iter([name for name in taxon.names if name.get("locale") == lang]), None
            )
            if name:
                preferred_common_name = name.get("name")
        if not preferred_common_name:
            preferred_common_name = taxon.preferred_common_name
        if with_term:
            common = (
                taxon.matched_term
                if taxon.matched_term not in (None, taxon.name, preferred_common_name)
                else preferred_common_name
            )
        else:
            if hierarchy:
                common = None
            else:
                common = preferred_common_name
        return common

    common = get_common_name() if with_common else None
    name = taxon.name

    rank = taxon.rank
    rank_level = RANK_LEVELS[rank]

    # Note: We follow how iNat uses italics taxon names on the website, i.e. we:
    # - don't apply italics to the name when it is rank Genushybrid or Subgenus
    # - do italicize the name for Genus and every rank at species or below
    # - any abbreviated english keywords within italicized intraspecific ranks
    #   are not italicized (spp. var. f.)
    if rank == "genus" or rank_level <= RANK_LEVELS["species"]:
        name = f"*{name}*"
    if rank_level > RANK_LEVELS["species"]:
        if hierarchy:
            bold = ("\n> **", "**") if rank in TAXON_PRIMARY_RANKS else ("", "")
            name = f"{bold[0]}{name}{bold[1]}"
        elif with_rank:
            name = f"{rank.capitalize()} {name}"
    else:
        if rank in TRINOMIAL_ABBR:
            tri = name.split(" ")
            if len(tri) == 3:
                # Note: name already italicized, so close/reopen italics around insertion.
                name = f"{tri[0]} {tri[1]}* {TRINOMIAL_ABBR[rank]} *{tri[2]}"
    full_name = f"{name} ({common})" if common else name
    if not taxon.is_active:
        full_name += " \N{HEAVY EXCLAMATION MARK SYMBOL} Inactive Taxon"
    return full_name


def _full_means(taxon: Taxon):
    """Get the full establishment means for the place from listed taxa."""
    place = taxon.establishment_means and taxon.establishment_means.place
    listed_taxa = taxon.listed_taxa
    if place and listed_taxa:
        return next(
            (
                listed_taxon
                for listed_taxon in listed_taxa
                if (listed_taxon.place and listed_taxon.place.id) == place.id
            ),
            None,
        )


def format_quality_grade(options: dict = {}):
    """Format as markdown a list of adjectives for quality grade options."""
    adjectives = []
    quality_grade = (options.get("quality_grade") or "").split(",")
    verifiable = options.get("verifiable")
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
    return adjectives


class BaseFormatter:
    def format():
        raise NotImplementedError


class ListFormatter(BaseFormatter):
    def format_page():
        raise NotImplementedError

    def last_page():
        raise NotImplementedError


class BaseCountFormatter(BaseFormatter):
    def count():
        raise NotImplementedError

    def description():
        raise NotImplementedError


class TaxonListFormatter(ListFormatter):
    _pages: dict[dict] = {}

    """
    Attributes
    ----------
    source: TaxonListSource
        Source of taxa including ancestors, enabling arrangement
        into a tree. This can be a life list other list of descendants
        of a common root taxon. The source must be set before any
        format methods can be called.
    """

    source: TaxonListSource

    def __init__(
        self,
        with_url: bool = True,
        with_taxa: bool = True,
        with_indent: bool = False,
        with_index: bool = False,
        with_direct: bool = False,
        with_common: bool = False,
        short_description: str = "Life list",
    ):
        """
        Parameters
        ----------
        with_url: bool, optional
            When True, link the title to a user's life list, provided the query
            was for a single user.

        with_taxa: bool, optional
            When True, format() and format_page() format the specified
            page of taxa on the source as a per_page sized page.

            The first page links to the observations in the query
            and the last page ends with a total per rank in the query.

            When False, only page 0 can be formatted with the observations link
            and per rank summary alone.

        with_indent: bool, optional
            When with_indent is True, per_rank is 'main' or 'any', and with_taxa
            is also True, the taxon names in the taxon list are displayed as
            children of higher taxa on the same page using indent levels and "└"
            to indicate child relationships.

        with_direct: bool, optional
            When with_direct is True, a column of direct observations counts of
            each taxon is shown. The number is only shown when non-zero. If the
            direct obs count is equal to the total obs count, then the total obs
            count is omitted. When shown, the direct obs count is enclosed in
            parentheses.

        with_common: bool, optional
            When with_common is True, if the source contains common names, then
            common names are included in the output.

        short_description: str, optional [default: `Life list`]
            Short description of Taxon list that appears in the title.
        """
        self.with_url = with_url
        self.with_taxa = with_taxa
        self.with_indent = with_indent
        self.with_index = with_index
        self.with_direct = with_direct
        self.with_common = with_common
        self.short_description = short_description

    def format(
        self,
        page: Union[Taxon, list[Taxon]] = None,
        page_number: Optional[int] = None,
        selected: Optional[int] = None,
        with_title: bool = True,
    ):
        """Format the taxon list as markdown."""
        description = self.format_page(page, page_number, selected)
        if with_title:
            description = "\n\n".join([self.format_title(), description])
        return description

    def format_title(self):
        """Format taxon list title as Discord-like markdown.

        Returns
        -------
        str
            - Describe a taxon list that is a life list derived from an
              observations query in terms of the observations query parameters
              passed.
            - When with_url is True, only link to a user life list when the
              query is for one user. The website doesn't have life list pages
              for any other kind of query.
        """
        title = f"{self.short_description} {self.source.query_response.obs_query_description()}"
        if self.with_url:
            if self.source.query_response.user:
                url = lifelists_url_from_query_response(self.source.query_response)
                title = format_link(title, url)
        return title

    def format_page(
        self,
        page: Union[Taxon, list[Taxon]] = None,
        page_number: int = 0,
        selected: int = 0,
    ):
        """Format the taxon list description."""

        def indent_child(taxon: Taxon):
            level = taxon.indent_level
            return protect_leading_blanks(
                "\N{EN SPACE}\N{THIN SPACE}" * (level - 1) + "└\N{THIN SPACE}"
                if level >= 1
                else ""
            )

        def make_page_header(taxon: Taxon):
            """Make a page header for non-top-level taxa."""
            ancestors = taxon.ancestors
            if ancestors:
                if ancestors[0].id == ROOT_TAXON_ID:
                    del ancestors[0]
                if ancestors:
                    header_ranks = included_ranks(self.source.per_rank)
                    header_names = [
                        format_taxon_name(parent, with_rank=False)
                        for parent in ancestors
                        if parent.rank in header_ranks
                    ]
                    if header_names:
                        meta = self.source.meta
                        counts_width = meta.count_digits
                        if self.with_direct:
                            counts_width += meta.direct_digits + 2
                        return (
                            f"`{' ' * counts_width}` __"
                            + " > ".join(header_names)
                            + "__"
                        )
            return None

        def format_page_of_taxa(page: list[Taxon]):
            query_response = self.source.query_response
            formatted_taxa = []
            for taxon in page:
                taxon_count = 0
                formatted_count = ""
                formatted_direct = ""
                meta = self.source.meta
                if getattr(taxon, "descendant_obs_count", None):
                    taxon_count = taxon.descendant_obs_count
                    # Format the direct column similarly to Dynamic Life Lists on
                    # iNat web, i.e.
                    # - never show direct count on non-leaves when it is zero
                    # - only show one column at the leaves, as the counts are equal
                    # - show the leaf count as "direct" at ranks above species,
                    #   a cue that the species count might be improved with more
                    #   ID refinements
                    if self.with_direct:
                        formatted_direct = " " * (meta.direct_digits + 2)
                        if taxon.count > 0:
                            formatted_direct = f"({taxon.count})".rjust(
                                meta.direct_digits + 2
                            )
                            is_leaf = taxon.count == taxon.descendant_obs_count
                            terminal_rank = taxon.rank_level <= RANK_LEVELS["species"]
                            if is_leaf:
                                if terminal_rank:
                                    formatted_direct = " " * (meta.direct_digits + 2)
                                else:
                                    formatted_count = " " * meta.count_digits
                else:
                    taxon_count = taxon.observations_count
                formatted_count = str(taxon_count).rjust(meta.count_digits)
                taxon_name = format_taxon_name(taxon, with_common=False)
                formatted_name = format_link(
                    taxon_name, taxon_obs_url(query_response, taxon)
                )
                if self.with_common and taxon.preferred_common_name:
                    formatted_name = f"{formatted_name} ({taxon.preferred_common_name})"
                formatted_taxa.append(
                    {
                        "count": formatted_count,
                        "direct": formatted_direct,
                        "indent": indent_child(taxon),
                        "name": formatted_name,
                    }
                )
            return formatted_taxa

        def make_page_content(page: list[Taxon], with_summary: bool = False):
            """Format all parts of the page content."""
            structured_page = {
                "header": None,
                "entries_header": None,
                "entries": [],
                "footer": None,
            }
            meta = self.source.meta
            with_page_headers = self.source.per_rank in ("main", "any")
            if page and self.with_taxa:
                formatted_taxa = format_page_of_taxa(page)
                if with_page_headers and page[0].indent_level > 1:
                    structured_page["entries_header"] = make_page_header(page[0])
                structured_page["entries"] = formatted_taxa
            if with_summary:
                structured_page["footer"] = format_taxon_list_summary(meta)
            return structured_page

        def assemble_page(content: dict, selected: int = 0):
            """Assemble page content into a formatted page."""
            sections = []
            if content["header"]:
                sections.append(content["header"])
            if content["entries_header"]:
                sections.append(content["entries_header"])
            if content["entries"]:
                entries = []
                for (index, entry) in enumerate(content["entries"]):
                    _i = f"**`{str(index + 1).zfill(2)}) `**" if self.with_index else ""
                    if selected == index:
                        _s = ">"
                        _n = "**__"
                        _e = "__**"
                    else:
                        _s = "\N{EN SPACE}"
                        _n = ""
                        _e = ""
                    entries.append(
                        f"{_i}`{entry['count']}{entry['direct']}`"
                        f"{_s}{entry['indent']}{_n}{entry['name']}{_e}"
                    )
                sections.append("\n".join(entries))
            if content["footer"]:
                sections.append(content["footer"])
            return "\n\n".join(sections)

        def taxon_obs_url(query_response: QueryResponse, taxon: Taxon):
            obs_args = query_response.obs_args()
            # Replace multiple taxa in the original query with just the one:
            if "taxon_ids" in obs_args:
                del obs_args["taxon_ids"]
            return obs_url_from_v1(
                {
                    **obs_args,
                    "taxon_id": taxon.id,
                }
            )

        with_summary = page_number == self.last_page()
        _page = [page] if isinstance(page, Taxon) else page
        page_content = make_page_content(_page, with_summary=with_summary)
        return assemble_page(page_content, selected)

    def last_page(self):
        if not (self.with_taxa and self.source.per_page > 0 and self.source.entries):
            return 0
        return self.source.get_max_pages() - 1


class TaxonFormatter(BaseFormatter):
    def __init__(
        self,
        taxon: Taxon,
        lang: str = None,
        with_url: bool = True,
        matched_term: str = None,
        max_len: int = 0,
    ):
        """
        Parameters
        ----------
        taxon: Taxon
            The taxon to format.

        lang: str, optional
            If specified, prefer the first name with its locale == lang instead of
            the preferred_common_name.

        matched_term: str, optional
            If specified, use instead of the taxon.matched_term.

        with_url: bool, optional
            When True, link the name to taxon.url.
        """
        self.taxon = taxon
        self.lang = lang
        self.with_url = with_url
        self.matched_term = matched_term
        self.max_len = max_len
        self.obs_count_formatter = self.ObsCountFormatter(taxon)

    def format(self, with_title: bool = True, with_ancestors: bool = True):
        """Format the taxon as markdown.

        with_title: bool, optional
        with_ancestors: bool, optional
            When False, omit ancestors
        """
        description = self.format_taxon_description()
        if with_title:
            description = "\n".join([self.format_title(), description])
        if with_ancestors and self.taxon.ancestors:
            description += " in: " + format_taxon_names(
                self.taxon.ancestors,
                hierarchy=True,
                max_len=self.max_len,
            )
        else:
            description += "."
        return description

    def format_title(self):
        """Format taxon title as Discord-like markdown.

        Returns
        -------
        str
            Like format_name(), except:

            - Append the matching term in its own parentheses after the common name
            in parentheses if the matching term is neither the scientific name nor
            common name, e.g.
            - "Pissenlits" -> "Genus *Taraxacum* (dandelions) (Pissenlits)"
            - if with_url=True, the matched term is not included in the link
            - Apply strikethrough style if the name is invalid, e.g.
            - "Picoides pubescens" ->
                "*Dryobates Pubescens* (Downy woodpecker) (~~Picoides Pubescens~~)
        """
        title = format_taxon_name(self.taxon, lang=self.lang)
        if self.with_url and self.taxon.url:
            title = format_link(title, self.taxon.url)
        # TODO: Remove workaround for outstanding pyinat issue #448 when it is resolved:
        # - https://github.com/pyinat/pyinaturalist/issues/448
        matched = self.matched_term or self.taxon.matched_term
        preferred_common_name = self.taxon.preferred_common_name
        if self.lang and self.taxon.names:
            name = next(
                iter(
                    [
                        name
                        for name in self.taxon.names
                        if name.get("locale") == self.lang
                    ]
                ),
                None,
            )
            if name:
                preferred_common_name = name.get("name")
        if matched not in (None, self.taxon.name, preferred_common_name):
            invalid_names = (
                [name["name"] for name in self.taxon.names if not name["is_valid"]]
                if self.taxon.names
                else []
            )
            if matched in invalid_names:
                matched = f"~~{matched}~~"
            title += f" ({matched})"
        return title

    def format_taxon_description(self):
        """Format the taxon description including rank, status, observation count, and means."""
        a_status_rank = self.format_taxon_status_rank()
        n_observations = self.obs_count_formatter.description()
        description = f"is {a_status_rank} with {n_observations}"
        if self.taxon.establishment_means:
            listed_taxon = _full_means(self.taxon) or self.taxon.establishment_means
            established_in_place = format_taxon_establishment_means(listed_taxon)
            if established_in_place:
                description = f"{description} {established_in_place}"
        return description

    def format_taxon_status_rank(self):
        """
        Format the taxon rank with optional status.
        """
        if self.taxon.conservation_status:
            status = self.taxon.conservation_status
            a_status = format_taxon_conservation_status(
                status, brief=True, inflect=True
            )
            a_status_rank = f"{a_status} {self.taxon.rank}"
        else:
            a_status_rank = p.a(self.taxon.rank)
        return a_status_rank

    class ObsCountFormatter(BaseCountFormatter):
        def __init__(self, taxon: Taxon):
            self.taxon = taxon

        def count(self):
            return self.taxon.observations_count

        def description(self):
            count = self.link()
            return f"{count} {p.plural('observation', count)}"

        def link(self):
            obs_count = self.count()
            obs_url = self.url()
            count = format_link(f"{obs_count:,}", obs_url)
            return count

        def url(self):
            return WWW_BASE_URL + f"/observations?taxon_id={self.taxon.id}"


class ObservationFormatter(BaseFormatter):
    def __init__(
        self,
        obs: Observation,
        with_description=True,
        with_link=False,
        compact=False,
        with_user=True,
        taxon: Taxon = None,
        taxon_summary: TaxonSummary = None,
        community_taxon: Taxon = None,
        community_taxon_summary: TaxonSummary = None,
    ):
        self.obs = obs
        self.compact = compact
        self.with_description = with_description
        self.with_link = with_link
        self.compact = compact
        self.with_user = with_user
        self.taxon = taxon or self.obs.taxon
        self.taxon_summary = taxon_summary
        self.community_taxon = community_taxon
        self.community_taxon_summary = community_taxon_summary

    def format(self, join_title: bool = True):
        title = self.format_title(with_link=join_title)
        summary = self.format_summary(self.taxon, self.taxon_summary)
        title, summary = self.format_community_id(
            title, summary, self.community_taxon_summary
        )
        if not self.compact:
            title += self.format_media_counts()
        result = (title, summary)
        if join_title:
            result = ("" if self.compact else "\n").join(result)
        return result

    def format_taxon_link(self, taxon: Taxon):
        taxon_str = self.get_taxon_name(taxon)
        if taxon and self.with_link:
            common = (
                f" ({taxon.preferred_common_name})"
                if taxon.preferred_common_name
                else ""
            )
            taxon_str = (
                format_link(taxon_str, f"{WWW_BASE_URL}/taxa/{taxon.id}") + common
            )
        return taxon_str

    def format_title(self, with_link: bool = True):
        title = ""
        taxon_str = self.get_taxon_name(self.taxon)
        if with_link and self.with_link:
            taxon_str = format_link(
                taxon_str, f"{WWW_BASE_URL}/observations/{self.obs.id}"
            )
        title += taxon_str
        if not self.compact:
            title += f" by {self.obs.user.login} " + ICONS[self.obs.quality_grade]
            if self.obs.faves:
                title += self.format_count("fave", len(self.obs.faves))
            if self.obs.comments:
                title += self.format_count("comment", len(self.obs.comments))
        return title

    def format_count(self, label, count):
        delim = " " if self.compact else ", "
        return f"{delim}{ICONS[label]}" + (str(count) if count > 1 else "")

    def get_taxon_name(self, taxon):
        if taxon:
            taxon_str = format_taxon_name(
                taxon, with_rank=not self.compact, with_common=False
            )
        else:
            taxon_str = "Unknown"
        return taxon_str

    def format_summary(self, taxon, taxon_summary):
        summary = ""
        obs = self.obs
        compact = self.compact
        with_user = self.with_user
        with_description = self.with_description

        if not compact:
            taxon_str = self.format_taxon_link(taxon)
            summary += f"Taxon: {taxon_str}\n"
        if taxon_summary:
            means = taxon_summary.listed_taxon
            status = taxon_summary.conservation_status
            if status:
                formatted_status = format_taxon_conservation_status(status)
                summary += f"Conservation Status: {formatted_status}\n"
            if means:
                summary += f"{format_taxon_establishment_means(means)}\n"
        login = ""
        if compact:
            if with_user:
                login = obs.user.login
            summary += "\n"
        else:
            summary += "Observed by " + format_user_link(obs.user)
        obs_on = ""
        obs_at = ""
        if obs.observed_on:
            obs_on = format_datetime(obs.observed_on, compact)
            if not compact:
                summary += " on " + obs_on
        if obs.place_guess:
            if compact:
                obs_at = obs.place_guess
            else:
                summary += " at " + obs.place_guess
        if compact:
            line = " ".join((item for item in (login, obs_on, obs_at) if item))
            if len(line) > 32:
                line = line[0:31] + "…"
            summary += "`{0: <32}`".format(line)
            summary += ICONS[obs.quality_grade]
            if obs.faves:
                summary += self.format_count("fave", len(obs.faves))
            if obs.comments:
                summary += self.format_count("comment", len(obs.comments))
            summary += self.format_media_counts()
        if with_description and obs.description:
            # Contribute up to 10 lines from the description, and no more
            # than 500 characters:
            #
            # TODO: if https://bugs.launchpad.net/beautifulsoup/+bug/1873787 is
            # ever fixed, suppress the warning instead of adding this blank
            # as a workaround.
            text_description = html2markdown.convert(" " + obs.description)
            lines = text_description.split("\n", 11)
            description = "\n> %s" % "\n> ".join(lines[:10])
            if len(lines) > 10:
                description += "\n> …"
            if len(description) > 500:
                description = description[:498] + "…"
            summary += description + "\n"
        return summary

    def format_community_id(self, title, summary, taxon_summary):
        idents_count = ""
        if self.obs.identifications_count:
            if self.obs.community_taxon_id:
                (idents_count, idents_agree) = self.obs.cumulative_ids
                idents_count = f"{ICONS['community']} ({idents_agree}/{idents_count})"
            else:
                obs_idents_count = (
                    self.obs.identifications_count
                    if self.obs.identifications_count > 1
                    else ""
                )
                idents_count = f"{ICONS['ident']}{obs_idents_count}"
        if (
            not self.compact
            and self.obs.community_taxon_id
            and self.obs.community_taxon_id != self.taxon.id
        ):
            means_link = ""
            status_link = ""
            if taxon_summary:
                means = taxon_summary.listed_taxon
                status = taxon_summary.conservation_status
                if status:
                    status_link = (
                        "\nConservation Status: "
                        f"{format_taxon_conservation_status(status)}"
                    )
                if means:
                    means_link = f"\n{format_taxon_establishment_means(means)}"
            community_taxon_str = f"{format_taxon_name(self.community_taxon)}"
            if self.with_link:
                community_taxon_str = self.format_taxon_link(self.community_taxon)
            summary = (
                f"Community Taxon: {community_taxon_str} {status_link}{idents_count}{means_link}\n"
                + summary
            )
        else:
            if idents_count:
                if self.compact:
                    summary += " " + idents_count
                else:
                    title += " " + idents_count
        return (title, summary)

    def format_media_counts(self):
        media_counts = ""
        if self.obs.photos:
            media_counts += self.format_count("image", len(self.obs.photos))
        if self.obs.sounds:
            media_counts += self.format_count("sound", len(self.obs.sounds))
        return media_counts


class QualifiedTaxonFormatter(TaxonFormatter):
    def __init__(
        self,
        query_response: "QueryResponse",
        observations: JsonResponse = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.query_response = query_response
        self.observations = observations
        self.obs_count_formatter = self.ObsCountFormatter(
            query_response.taxon, query_response, observations
        )

    class ObsCountFormatter(TaxonFormatter.ObsCountFormatter):
        def __init__(
            self,
            taxon: Taxon,
            query_response: "QueryResponse" = None,
            observations: JsonResponse = None,
        ):
            super().__init__(taxon)
            self.query_response = query_response
            self.observations = observations

        def count(self):
            if self.observations:
                count = self.observations.get("total_results")
            else:
                count = self.taxon.observations_count
            return count

        def url(self):
            return obs_url_from_v1(self.query_response.obs_args())

        def description(self):
            count = self.link()
            count_str = "uncounted" if count is None else str(count)
            adjectives = self.query_response.adjectives  # rg, nid, etc.
            query_without_taxon = copy.copy(self.query_response)
            query_without_taxon.taxon = None
            description = [
                count_str,
                *adjectives,
                p.plural("observation", count),
            ]
            filter = query_without_taxon.obs_query_description(
                with_adjectives=False
            )  # place, prj, etc.
            if filter:
                description.append(filter)
            return " ".join(description)


class UserFormatter(BaseFormatter):
    def __init__(
        self,
        user: User,
    ):
        """
        Parameters
        ----------
        user: User
            The user to format.
        """
        self.user = user

    def format(self, with_link: bool = True):
        """Format the user as markdown.

        with_link: bool, optional
            Link to user's profile.
        """
        name = self.user.name
        if name:
            name += f" ({self.user.login})"
        else:
            name = self.user.login
        if with_link:
            name = f"[{name}]({self.user.url})"
        return name
