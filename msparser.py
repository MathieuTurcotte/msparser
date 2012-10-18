# Copyright (c) 2011 Mathieu Turcotte
# Licensed under the MIT license.

"""
The msparser module offers a simple interface to parse the Valgrind massif.out
file format, i.e. data files produced the Valgrind heap profiler.
"""

from __future__ import with_statement  # Enable with statement in Python 2.5.
import re

__all__ = ["parse", "parse_file", "ParseError"]

# Precompiled regex used to parse comments.
_COMMENT_RE = re.compile("\s*(#|$)")

# Precompiled regexes used to parse header fields.
_FIELD_DESC_RE = re.compile("desc:\s(?P<data>\S+)")
_FIELD_CMD_RE = re.compile("cmd:\s(?P<data>\S+)")
_FIELD_TIME_UNIT_RE = re.compile("time_unit:\s(?P<data>ms|B|i)")

# Precompiled regexes used to parse snaphot fields.
_FIELD_SNAPSHOT_RE = re.compile("snapshot=(?P<data>\d+)")
_FIELD_TIME_RE = re.compile("time=(?P<data>\d+)")
_FIELD_MEM_HEAP_RE = re.compile("mem_heap_B=(?P<data>\d+)")
_FIELD_MEM_EXTRA_RE = re.compile("mem_heap_extra_B=(?P<data>\d+)")
_FIELD_MEM_STACK_RE = re.compile("mem_stacks_B=(?P<data>\d+)")
_FIELD_HEAP_TREE_RE = re.compile("heap_tree=(?P<data>\w+)")

# Precompiled regex to parse heap entries. Matches three things:
#   - the number of children,
#   - the number of bytes
#   - and the details section.
_HEAP_ENTRY_RE = re.compile("""
    \s*n                    # skip zero or more spaces, then 'n'
    (?P<num_children>\d+)   # match number of children, 1 or more digits
    :\s                     # skip ':' and one space
    (?P<num_bytes>\d+)      # match the number of bytes, 1 or more digits
    \s                      # skip one space
    (?P<details>.*)         # match the details
""", re.VERBOSE)

# Precompiled regex to check if the details section is below threshold.
_HEAP_BELOW_THRESHOLD_RE = re.compile(r"""in.*places?.*""")

# Precompiled regex to parse the details section of entries above threshold.
# This should match four things:
#   - the hexadecimal address,
#   - the function name,
#   - the file name or binary path, i.e. file.cpp or usr/local/bin/foo.so,
#   - and a line number if present.
# Last two parts are optional to handle entries without a file name or binary
# path.
_HEAP_DETAILS_RE = re.compile(r"""
    (?P<address>[a-fA-F0-9x]+)  # match the hexadecimal address
    :\s                         # skip ': '
    (?P<function>.+?)           # match the function's name, non-greedy
    (?:                         # don't capture fname/line group
        \s
        \(
        (?:in\s)?               # skip 'in ' if present
        (?P<fname>[^:]+)        # match the file name
        :?                      # skip ':', if present
        (?P<line>\d+)?          # match the line number, if present
        \)
    )?                          # fname/line group is optional
    $                           # should have reached the EOL
""", re.VERBOSE)


class ParseError(Exception):
    """
    Error raised when a parsing error is encountered.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


def parse_file(filepath):
    """
    Convenience function taking a file path instead of a file descriptor.
    """
    with open(filepath) as fd:
        return parse(fd)


def parse(fd):
    """
    Parse an already opened massif output file.
    """
    mdata = {}
    mdata["snapshots"] = []
    mdata["detailed_snapshots_index"] = []

    # Parse header data.
    mdata["desc"] = _get_next_field(fd, _FIELD_DESC_RE)
    mdata["cmd"] = _get_next_field(fd, _FIELD_CMD_RE)
    mdata["time_unit"] = _get_next_field(fd, _FIELD_TIME_UNIT_RE)

    while _get_next_snapshot(fd, mdata):
        continue

    return mdata


def _match_unconditional(regex, string):
    """
    Unconditionaly match a regular expression against a string, i.e. if there
    is no match we raise a ParseError.
    """
    match = regex.match(string)
    if match is None:
        raise ParseError("".join(["can't match '", string, "' against '",
                         regex.pattern, "'"]))
    return match


def _get_next_line(fd, may_reach_eof=False):
    """
    Read another line from fd. If may_reach_eof is False, reaching EOF will
    be considered as an error.
    """
    line = fd.readline()  # Returns an empty string on EOF.

    if len(line) == 0:
        if may_reach_eof is False:
            raise ParseError("unexpected EOF")
        else:
            return None
    else:
        return line.strip("\n")


def _get_next_field(fd, field_regex, may_reach_eof=False):
    """
    Read the next data field. The field_regex arg is a regular expression that
    will be used to match the field. Data will be extracted from the match
    object by calling m.group('data'). If may_reach_eof is False, reaching EOF
    will be considered as an error.
    """
    line = _get_next_line(fd, may_reach_eof)
    while line is not None:
        if _COMMENT_RE.match(line):
            line = _get_next_line(fd, may_reach_eof)
        else:
            match = _match_unconditional(field_regex, line)
            return match.group("data")

    return None


def _get_next_snapshot(fd, mdata):
    """
    Parse another snapshot, appending it to the mdata["snapshots"] list. On
    EOF, False will be returned.
    """
    snapshot_id = _get_next_field(fd, _FIELD_SNAPSHOT_RE, may_reach_eof=True)

    if snapshot_id is None:
        return False

    snapshot_id = int(snapshot_id)
    time = int(_get_next_field(fd, _FIELD_TIME_RE))
    mem_heap = int(_get_next_field(fd, _FIELD_MEM_HEAP_RE))
    mem_heap_extra = int(_get_next_field(fd, _FIELD_MEM_EXTRA_RE))
    mem_stacks = int(_get_next_field(fd, _FIELD_MEM_STACK_RE))
    heap_tree = _get_next_field(fd, _FIELD_HEAP_TREE_RE)

    # Handle the heap_tree field.
    if heap_tree != "empty":
        if heap_tree == "peak":
            mdata["peak_snapshot_index"] = snapshot_id
        heap_tree = _parse_heap_tree(fd)
        mdata["detailed_snapshots_index"].append(snapshot_id)
    else:
        heap_tree = None

    mdata["snapshots"].append({
        "id": snapshot_id,
        "time": time,
        "mem_heap": mem_heap,
        "mem_heap_extra": mem_heap_extra,
        "mem_stack": mem_stacks,
        "heap_tree": heap_tree
    })

    return True


def _parse_heap_tree(fd):
    """
    Parse a snapshot heap tree.
    """
    line = _get_next_line(fd)
    match = _match_unconditional(_HEAP_ENTRY_RE, line)

    children = []
    for i in range(0, int(match.group("num_children"))):
        children.append(_parse_heap_node(fd))

    root_node = {}
    root_node["details"] = None
    root_node["nbytes"] = int(match.group("num_bytes"))
    root_node["children"] = children

    return root_node


def _parse_heap_node(fd):
    """
    Parse a normal heap tree node.
    """
    line = _get_next_line(fd)
    entry_match = _match_unconditional(_HEAP_ENTRY_RE, line)

    details = entry_match.group("details")
    if _HEAP_BELOW_THRESHOLD_RE.match(details):
        details = None
    else:
        details_match = _match_unconditional(_HEAP_DETAILS_RE, details)
        # The 'line' field could be None if the binary/library wasn't compiled
        # with debug info. To avoid errors on this condition, we need to make
        # sure that the 'line' field is not None before trying to convert it to
        # an integer.
        linum = details_match.group(4)
        if linum is not None:
            linum = int(linum)

        details = {
            "address": details_match.group("address"),
            "function": details_match.group("function"),
            "file": details_match.group("fname"),
            "line": linum
        }

    children = []
    for i in range(0, int(entry_match.group("num_children"))):
        children.append(_parse_heap_node(fd))

    heap_node = {}
    heap_node["nbytes"] = int(entry_match.group("num_bytes"))
    heap_node["children"] = children
    heap_node["details"] = details

    return heap_node
