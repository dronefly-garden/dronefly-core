"""Constants for formatters."""

WWW_BASE_URL = "https://www.inaturalist.org"

ICONS = {
    "research": "\N{WHITE HEAVY CHECK MARK}",
    "needs_id": "\N{LARGE ORANGE DIAMOND}",
    "casual": "\N{MEDIUM WHITE CIRCLE}",
    "fave": "\N{WHITE MEDIUM STAR}",
    "comment": "\N{LEFT SPEECH BUBBLE}",
    "community": "\N{BUSTS IN SILHOUETTE}",
    "image": "\N{CAMERA}",
    "sound": "\N{SPEAKER WITH ONE SOUND WAVE}",
    "ident": "\N{LABEL}",
}
# For use in cases where an entity is normally
# expected to have a value but may not, e.g.
#
#   ICONS.get(obs.quality_grade, UNKNOWN_ICON)
#   - will alaways return an icon representing the quality grade, even if obs is
#     only a partial (as when created from test data or a data set missing
#     fields normally present in observations returned from the API)
UNKNOWN_ICON = "\N{REPLACEMENT CHARACTER}"
