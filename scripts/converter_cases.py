"""Shared, stdlib-only case selection for converter evaluation tools."""
import fnmatch


def selector(patterns=('*',), exclude=()):
    if isinstance(patterns, str) or isinstance(exclude, str):
        raise TypeError('case rules must be sequences')
    patterns, exclude = tuple(patterns), tuple(exclude)
    if any(not isinstance(rule, str) or not rule for rule in patterns + exclude):
        raise ValueError('case rules must be nonempty strings')
    def matches(key, rules):
        return any(fnmatch.fnmatchcase(key, rule) or fnmatch.fnmatchcase(key.split(':', 1)[-1], rule)
                   for rule in rules)
    return lambda key: matches(key, patterns) and not matches(key, exclude)


def select_keys(keys, patterns=('*',), exclude=()):
    selected = selector(patterns, exclude)
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate converter case keys')
    result = [key for key in keys if selected(key)]
    if not result:
        raise ValueError('no selected converter cases')
    return result


def arguments(parser):
    parser.add_argument('--case', action='append', help='case key/id glob; repeat for OR')
    parser.add_argument('--exclude', action='append', help='exclude case key/id glob')
    parser.add_argument('--list', action='store_true', help='list case keys without reading fixtures or converting')
