# Copyright (c) 2011 Mathieu Turcotte
# Licensed under the MIT license.

from __future__ import with_statement  # Enable with statement in Python 2.5.
import json
import msparser
import os
import sys

# Use unittest2 on versions older than Python 2.7.
if sys.version_info[0] < 3 and sys.version_info[1] < 7:
    from unittest2 import TestCase, main
else:
    from unittest import TestCase, main


class FakeContext():
    def __init__(self, lines=[], filename="fake.txt", baseline=0):
        self.index_ = 0
        self.lines_ = lines
        self.filename_ = filename
        self.baseline_ = baseline

    def set_content(self, lines, baseline=0):
        self.index_ = 0
        self.lines_ = lines
        self.baseline_ = baseline

    def line(self):
        return self.baseline_ + self.index_

    def readline(self):
        if len(self.lines_) > self.index_:
            line = self.lines_[self.index_] + "\n"
            self.index_ += 1
            return line
        else:
            return ""

    def filename(self):
        return self.filename_


class ParseHeaderTest(TestCase):
    def setUp(self):
        self.ctx = FakeContext([
            "desc: --time-unit=B --pages-as-heap=yes",
            "cmd: ./thompson --log=2 --fastpath",
            "time_unit: B"
        ])
        self.mdata = {}

    def test_parse_header(self):
        msparser._parse_header(self.ctx, self.mdata)
        self.assertEqual(self.mdata["desc"],
                         "--time-unit=B --pages-as-heap=yes")
        self.assertEqual(self.mdata["cmd"], "./thompson --log=2 --fastpath")
        self.assertEqual(self.mdata["time_unit"], "B")


class ParseHeapTreeTest(TestCase):
    def parse_heap_tree(self, lines):
        self.ctx = FakeContext()
        self.ctx.set_content(lines)
        return msparser._parse_heap_tree(self.ctx)

    def test_parse_one_level_simple(self):
        tree = self.parse_heap_tree([
            "n0: 50456 0x804BFC0: DancingLinksSolver::build_cover_matrix("
            "Sudoku&) (SudokuSolver.cpp:30)"
        ])
        self.assertEqual(tree["nbytes"], 50456)
        self.assertEqual(len(tree["children"]), 0)
        self.assertEqual(tree["details"], {
            "function": "DancingLinksSolver::build_cover_matrix(Sudoku&)",
            "address": "0x804BFC0",
            "file": "SudokuSolver.cpp",
            "line": 30
        })

    def test_parse_one_level_empty_filename(self):
        tree = self.parse_heap_tree(["n0: 24305664 0x7FF0007A5: ???"])
        self.assertEqual(tree["nbytes"], 24305664)
        self.assertEqual(len(tree["children"]), 0)
        self.assertEqual(tree["details"], {
            "function": "???",
            "address": "0x7FF0007A5",
            "file": None,
            "line": None
        })

    def test_parse_one_level_page_allocation(self):
        tree = self.parse_heap_tree([
            "n0: 165990400 (page allocation syscalls) mmap/mremap/brk, "
            "--alloc-fns, etc."
        ])
        self.assertEqual(tree["nbytes"], 165990400)
        self.assertEqual(len(tree["children"]), 0)
        self.assertEqual(tree["details"], None)

    def test_parse_one_level_below_threshold(self):
        tree = self.parse_heap_tree([
            "n0: 8192 in 1 place, below massif's threshold (01.00%)"
        ])
        self.assertEqual(tree["nbytes"], 8192)
        self.assertEqual(len(tree["children"]), 0)
        self.assertEqual(tree["details"], None)

    def test_parse_multi_levels(self):
        tree = self.parse_heap_tree([
            "n2: 165990400 (page allocation syscalls) mmap/mremap/brk, "
            "--alloc-fns, etc.",
            " n2: 111468544 0x5E70169: mmap (syscall-template.S:82)",
            "  n0: 83079168 0x5E031E7: malloc (arena.c:824)",
            "  n0: 8192 in 1 place, below massif's threshold (01.00%)",
            " n0: 83079168 0x5DFE377: new_heap (arena.c:554)"
        ])

        self.assertEqual(tree["nbytes"], 165990400)
        self.assertEqual(len(tree["children"]), 2)
        self.assertEqual(tree["details"], None)

        child1 = tree["children"][0]
        self.assertEqual(child1["nbytes"], 111468544)
        self.assertEqual(len(child1["children"]), 2)
        self.assertEqual(child1["details"], {
            "function": "mmap",
            "address": "0x5E70169",
            "file": "syscall-template.S",
            "line": 82
        })

        child11 = child1["children"][0]
        self.assertEqual(child11["nbytes"], 83079168)
        self.assertEqual(len(child11["children"]), 0)
        self.assertEqual(child11["details"], {
            "function": "malloc",
            "address": "0x5E031E7",
            "file": "arena.c",
            "line": 824
        })

        child12 = child1["children"][1]
        self.assertEqual(child12["nbytes"], 8192)
        self.assertEqual(len(child12["children"]), 0)
        self.assertEqual(child12["details"], None)

        child2 = tree["children"][1]
        self.assertEqual(child2["nbytes"], 83079168)
        self.assertEqual(len(child2["children"]), 0)
        self.assertEqual(child2["details"], {
            "function": "new_heap",
            "address": "0x5DFE377",
            "file": "arena.c",
            "line": 554
        })


class ParseSnapshotTest(TestCase):
    def setUp(self):
        self.ctx = FakeContext()
        self.mdata = {
            "snapshots": [],
            "detailed_snapshots_index": []
        }

    def parse_snapshot(self, lines):
        self.ctx.set_content(lines)
        return msparser._parse_snapshot(self.ctx, self.mdata)

    def test_parse_empty_snapshot(self):
        success = self.parse_snapshot([
            "#-----------",
            "snapshot=1",
            "#-----------",
            "time=100279",
            "mem_heap_B=30035968",
            "mem_heap_extra_B=0",
            "mem_stacks_B=0",
            "heap_tree=empty"
        ])

        self.assertTrue(success)
        self.assertEqual(len(self.mdata["detailed_snapshots_index"]), 0)
        self.assertEqual(self.mdata["snapshots"][0], {
            "id": 1,
            "time": 100279,
            "mem_heap": 30035968,
            "mem_heap_extra": 0,
            "mem_stack": 0,
            "heap_tree": None
        })

    def test_parse_peak_snapshot(self):
        success = self.parse_snapshot([
            "#-----------",
            "snapshot=1",
            "#-----------",
            "time=100279",
            "mem_heap_B=30035968",
            "mem_heap_extra_B=0",
            "mem_stacks_B=0",
            "heap_tree=peak",
            "n0: 8192 in 1 place, below massif's threshold (01.00%)"
        ])

        self.assertTrue(success)
        self.assertEqual(self.mdata["peak_snapshot_index"], 0)
        self.assertEqual(self.mdata["detailed_snapshots_index"][0], 0)
        self.assertEqual(len(self.mdata["detailed_snapshots_index"]), 1)
        self.assertIsNotNone(self.mdata["snapshots"][0]["heap_tree"])


class TestFullParse(TestCase):
    pass


def make_parse_test(path_to_actual, path_to_expected):
    def test_parse(self):
        actual = msparser.parse_file(path_to_actual)
        expected = json.load(open(path_to_expected))
        self.assertEqual(expected, actual)
    return test_parse


for filename in os.listdir("test_data"):
    if not filename.endswith("json"):
        path_to_actual = "test_data/" + filename
        path_to_expected = path_to_actual + ".json"
        test_name = "test" + filename.replace(".", "_")
        test_function = make_parse_test(path_to_actual, path_to_expected)
        test_function.__doc__ = test_name
        setattr(TestFullParse, test_name, test_function)


if __name__ == "__main__":
    main()
