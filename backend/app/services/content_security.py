import nh3

_CLEANER = nh3.Cleaner(
    tags={'p','br','h1','h2','h3','h4','strong','em','u','s','a','ul','ol','li','blockquote','pre','code','table','thead','tbody','tr','th','td','figure','figcaption','img'},
    attributes={'a': {'href','title','target'}, 'img': {'src','alt','title','width','height'}, 'th': {'scope'}, 'td': {'colspan','rowspan'}},
    clean_content_tags={'script','style','iframe','object','embed'},
    url_schemes={'http','https','mailto'},
    link_rel='noopener noreferrer',
)


def sanitize_content(value: str) -> str:
    return _CLEANER.clean(value)
