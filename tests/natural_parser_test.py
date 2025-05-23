"""Tests for NaturalParser."""
# pylint: disable=missing-class-docstring, no-self-use, missing-function-docstring
# pylint: disable=redefined-outer-name
import re

import pytest

from dronefly.core.parsers.natural import NaturalParser


@pytest.fixture
def parser():
    return NaturalParser()


class TestNaturalParser:
    def test_standard_order(self, parser):
        parsed = parser.parse("by benarmstrong from nova scotia")
        assert str(parsed) == "from nova scotia by benarmstrong"

    def test_implied_taxon_listed_first(self, parser):
        parsed = parser.parse("by benarmstrong of birds")
        assert str(parsed) == "birds by benarmstrong"

    def test_ancestor_without_main(self, parser):
        with pytest.raises(ValueError) as err:
            parser.parse("in animals")
            assert re.match(r"Missing.*taxon", str(err), re.I)

    def test_ancestor_with_with_ranks(self, parser):
        parsed = parser.parse("rank species in animals")
        assert str(parsed) == "species in animals"

    def test_ancestor_with_main(self, parser):
        parsed = parser.parse("of prunella in animals")
        assert str(parsed) == "prunella in animals"

    def test_user(self, parser):
        parsed = parser.parse("by benarmstrong")
        assert str(parsed) == "by benarmstrong"

    def test_place(self, parser):
        parsed = parser.parse("from nova scotia")
        assert str(parsed) == "from nova scotia"

    def test_with(self, parser):
        parsed = parser.parse("with sex f")
        assert str(parsed) == "with sex f"

    def test_unobserved_by(self, parser):
        parsed = parser.parse("not by me")
        assert str(parsed) == "not by me"

    def test_except_by(self, parser):
        parsed = parser.parse("except by me")
        assert str(parsed) == "except by me"

    def test_id_by(self, parser):
        parsed = parser.parse("id by me")
        assert str(parsed) == "id by me"

    def test_per(self, parser):
        parsed = parser.parse("per species")
        assert str(parsed) == "per species"

    def test_project(self, parser):
        parsed = parser.parse('in prj "arthropods on snow"')
        assert str(parsed) == 'in prj "arthropods on snow"'

    def test_options(self, parser):
        parsed = parser.parse("opt sounds popular")
        assert str(parsed) == "opt sounds popular"

    def test_since(self, parser):
        parsed = parser.parse("since today")
        assert bool(re.match(r"since \d{4}", str(parsed)))

    def test_until(self, parser):
        parsed = parser.parse("until today")
        assert bool(re.match(r"until \d{4}", str(parsed)))

    def test_on(self, parser):
        parsed = parser.parse("on today")
        assert bool(re.match(r"on \d{4}", str(parsed)))

    def test_added_since(self, parser):
        parsed = parser.parse("added since today")
        assert bool(re.match(r"added since \d{4}", str(parsed)))

    def test_added_until(self, parser):
        parsed = parser.parse("added until today")
        assert bool(re.match(r"added until \d{4}", str(parsed)))

    def test_added_on(self, parser):
        parsed = parser.parse("added on today")
        assert bool(re.match(r"added on \d{4}", str(parsed)))

    def test_code(self, parser):
        parsed = parser.parse("wtsp")
        assert parsed.main.code == "WTSP"

    def test_id(self, parser):
        parsed = parser.parse("12345")
        assert parsed.main.taxon_id == "12345"

    def test_url(self, parser):
        parsed = parser.parse("https://www.inaturalist.org/taxa/1-Animalia")
        assert parsed.main.taxon_id == "1"

    def test_change_only_arg_keyword_case(self, parser):
        parsed = parser.parse("BY SyntheticBee")
        assert str(parsed) == "by SyntheticBee"

    def test_macro(self, parser):
        parsed = parser.parse("my myrtle warbler")
        assert str(parsed) == "myrtle warbler by me"

    def test_macro_sort_by_and_order(self, parser):
        parsed = parser.parse("my oldest")
        assert str(parsed) == "by me sort by observed order asc"

    def test_macros_combined(self, parser):
        parsed = parser.parse("my home birds")
        assert str(parsed) == "birds from home by me"

    def test_macros_combined_complex(self, parser):
        parsed = parser.parse("least unseen")
        assert str(parsed) == "from home not by me per species sort by obs order asc"

    def test_group_opt(self, parser):
        parsed = parser.parse("herps")
        assert str(parsed) == "opt taxon_ids=20978,26036"

    def test_macro_group_and_opt(self, parser):
        parsed = parser.parse("rg herps opt taxon_geoprivacy=open")
        assert (
            str(parsed)
            == "opt quality_grade=research taxon_ids=20978,26036 taxon_geoprivacy=open"
        )

    def test_group_and_macro(self, parser):
        parsed = parser.parse("my herps")
        assert str(parsed) == "by me opt taxon_ids=20978,26036"

    def test_group_and_opt_macro(self, parser):
        parsed = parser.parse("rg herps")
        assert str(parsed) == "opt quality_grade=research taxon_ids=20978,26036"

    def test_group_ignored_second_word(self, parser):
        parsed = parser.parse("my green herps")
        assert str(parsed) == "green herps by me"

    def test_group_ignored_first_of_two_words(self, parser):
        parsed = parser.parse("my herps green")
        assert str(parsed) == "herps green by me"
