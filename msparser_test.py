# Copyright (c) 2011 Mathieu Turcotte
# Licensed under the MIT license.

from __future__ import with_statement  # Enable with statement in Python 2.5.
import sys

# Use unittest2 on versions older than Python 2.7.
if sys.version_info[0] < 3 and sys.version_info[1] < 7:
    from unittest2 import TestCase, main
else:
    from unittest import TestCase, main

import msparser


EMPTY_SNAPSHOTS = """
desc: --time-unit=ms
cmd: ./a.out
time_unit: ms
#-----------
snapshot=0
#-----------
time=0
mem_heap_B=0
mem_heap_extra_B=0
mem_stacks_B=0
heap_tree=empty
#-----------
snapshot=1
#-----------
time=183
mem_heap_B=1000
mem_heap_extra_B=8
mem_stacks_B=0
heap_tree=empty
#-----------
snapshot=2
#-----------
time=184
mem_heap_B=2000
mem_heap_extra_B=16
mem_stacks_B=0
heap_tree=empty"""

DETAILED_SNAPSHOTS = """
desc: --time-unit=i
cmd: ./memory-run
time_unit: i
#-----------
snapshot=0
#-----------
time=1887671
mem_heap_B=91458
mem_heap_extra_B=39022
mem_stacks_B=0
heap_tree=empty
#-----------
snapshot=1
#-----------
time=1937480
mem_heap_B=56850
mem_heap_extra_B=24190
mem_stacks_B=0
heap_tree=detailed
n3: 56850 (heap allocation functions) malloc/new/new[], --alloc-fns, etc.
 n1: 50456 0x804BFC0: DancingLinksSolver::build_cover_matrix(Sudoku&) (SudokuSolver.cpp:114)
  n2: 50456 0x804C30F: DancingLinksSolver::solve(Sudoku&) (SudokuSolver.cpp:15)
   n1: 50456 0x8049C2C: main (memory.cpp:30)
    n1: 50456 0x804C: ??? (memory.cpp:125)
     n1: 50456 0x804BE5C: (below main) (libc-start.c:226)
      n0: 50456 0x2: ???
   n0: 0 in 1 place, below massif's threshold (01.00%)
 n1: 5628 0x804BE5C: DancingLinksSolver::build_cover_matrix(Sudoku&) (SudokuSolver.cpp:42)
  n2: 5628 0x804C30F: DancingLinksSolver::solve(Sudoku&) (SudokuSolver.cpp:15)
   n0: 5628 0x8049C2C: main (memory.cpp:30)
   n0: 0 in 1 place, below massif's threshold (01.00%)
 n0: 766 in 6 places, all below massif's threshold (01.00%)
#-----------
snapshot=2
#-----------
time=3068292
mem_heap_B=441458
mem_heap_extra_B=186670
mem_stacks_B=0
heap_tree=empty
#-----------
snapshot=3
#-----------
time=3194213
mem_heap_B=494014
mem_heap_extra_B=209194
mem_stacks_B=0
heap_tree=peak
n4: 494014 (heap allocation functions) malloc/new/new[], --alloc-fns, etc.
 n1: 344064 0x804BFC0: DancingLinksSolver::build_cover_matrix(Sudoku&) (SudokuSolver.cpp:114)
  n2: 344064 0x804C30F: DancingLinksSolver::solve(Sudoku&) (SudokuSolver.cpp:15)
   n0: 344064 0x8049C88: main (memory.cpp:49)
   n0: 0 in 2 places, all below massif's threshold (01.00%)
 n1: 114688 0x804BF7C: DancingLinksSolver::build_cover_matrix(Sudoku&) (SudokuSolver.cpp:91)
  n2: 114688 0x804C30F: DancingLinksSolver::solve(Sudoku&) (SudokuSolver.cpp:15)
   n0: 114688 0x8049C88: main (memory.cpp:49)
   n0: 0 in 2 places, all below massif's threshold (01.00%)
 n1: 28672 0x804BE5C: DancingLinksSolver::build_cover_matrix(Sudoku&) (SudokuSolver.cpp:42)
  n2: 28672 0x804C30F: DancingLinksSolver::solve(Sudoku&) (SudokuSolver.cpp:15)
   n0: 28672 0x8049C88: main (memory.cpp:49)
   n0: 0 in 2 places, all below massif's threshold (01.00%)
 n0: 6590 in 5 places, all below massif's threshold (01.00%)
#-----------
snapshot=4
#-----------
time=4342249
mem_heap_B=489890
mem_heap_extra_B=209174
mem_stacks_B=0
heap_tree=empty"""


class MockFile():
    def __init__(self, content):
        self.lines = content.split("\n")
        self.index = 0

    def readline(self):
        if len(self.lines) > self.index:
            line = self.lines[self.index] + "\n"
            self.index += 1
            return line
        else:
            return ""


def parse(content):
    fd = MockFile(content)
    return msparser.parse(fd)


class MassifParserEmptySnaphostTest(TestCase):
    def setUp(self):
        self.data = parse(EMPTY_SNAPSHOTS)

    def test_parse_time_unit(self):
        self.assertEqual(self.data["time_unit"], "ms")

    def test_parse_cmd(self):
        self.assertEqual(self.data["cmd"], "./a.out")

    def test_parse_desc(self):
        self.assertEqual(self.data["desc"], "--time-unit=ms")

    def test_parse_snaphosts(self):
        self.assertEqual(len(self.data["snapshots"]), 3)

    def test_parse_empty_snapshot(self):
        snapshot = self.data["snapshots"][2]
        self.assertEqual(snapshot["id"], 2, "id")
        self.assertEqual(snapshot["time"], 184, "time")
        self.assertEqual(snapshot["mem_heap"], 2000, "mem_heap")
        self.assertEqual(snapshot["mem_heap_extra"], 16, "mem_heap_extra")
        self.assertEqual(snapshot["mem_stack"], 0, "mem_stack")
        self.assertEqual(snapshot["heap_tree"], None, "heap_tree")


class MassifParserDetailedSnaphostTest(TestCase):
    def setUp(self):
        self.data = parse(DETAILED_SNAPSHOTS)

    def test_parse_snapshot_heap_tree(self):
        snapshot = self.data["snapshots"][1]

        # Check the heap tree's root.
        root = snapshot["heap_tree"]
        self.assertEqual(root["nbytes"], 56850)
        self.assertEqual(len(root["children"]), 3)

        # Check root's first child.
        root_children = sorted(root["children"], key=lambda x: x["nbytes"],
                               reverse=True)
        first_root_child = root_children[0]
        self.assertEqual(first_root_child["nbytes"], 50456)
        self.assertEqual(first_root_child["details"], {
            "function": "DancingLinksSolver::build_cover_matrix(Sudoku&)",
            "address": "0x804BFC0",
            "file": "SudokuSolver.cpp",
            "line": 114
        })

    def test_find_peak_snapshot(self):
        peak_snapshot_index = self.data["peak_snapshot_index"]
        self.assertEqual(peak_snapshot_index, 3)


class MassifParserErrorDetectionTest(TestCase):
    def test_detect_partial_file(self):
        with self.assertRaises(msparser.ParseError):
            msparser.parse(MockFile("desc: --time-unit=ms\n"
                                    "cmd: ./a.out\n"
                                    "time_unit: ms\n"
                                    "#-----------\n"
                                    "snapshot=0\n"
                                    "#-----------\n"
                                    "time=0\n"
                                    "mem_heap_B=0"))  # Missing snapshot's fields.

    def test_detect_broken_header(self):
        with self.assertRaises(msparser.ParseError):
            msparser.parse(MockFile("desc: --time-unit=ms\n"
                                    "c broken  md: ./a.out\n"  # Bad tag name.
                                    "time_unit: ms\n"
                                    "#-----------\n"
                                    "snapshot=0\n"
                                    "#-----------\n"
                                    "time=0\n"
                                    "mem_heap_B=0\n"
                                    "mem_heap_extra_B=0\n"
                                    "mem_stacks_B=0\n"
                                    "heap_tree=empty\n"))

    def test_detect_broken_snapshot(self):
        with self.assertRaises(msparser.ParseError):
            msparser.parse(MockFile("desc: --time-unit=ms\n"
                                    "cmd: ./a.out\n"
                                    "time_unit: ms\n"
                                    "#-----------\n"
                                    "snapshot=0\n"
                                    "#-----------\n"
                                    "time=0\n"
                                    "mem_heap_B=0\n"
                                    "mem_h e a p_extra_B=0\n"  # Bad tag name.
                                    "mem_stacks_B=0\n"
                                    "heap_tree=empty\n"))

    def test_detect_broken_heap_tree(self):
        fd = MockFile("desc: --time-unit=ms\n"
                      "cmd: ./a.out\n"
                      "time_unit: ms\n"
                      "#-----------\n"
                      "snapshot=0\n"
                      "#-----------\n"
                      "time=0\n"
                      "mem_heap_B=0\n"
                      "mem_heap_extra_B=0\n"
                      "mem_stacks_B=0\n"
                      "heap_tree=peak\n"
                      "n4: 32000 (heap allocation functions) malloc/new/new[], --alloc-fns, etc.\n"
                      " n1: 12000 0x8048404: h (prog.c:4)\n"
                      "  n2: 12000 0x804841D: g (prog.c:9)\n"
                      "   n1: 6000 0x8048436: f (prog.c:14)\n"
                      "    n0: 6000 0x8048472: main (prog.c:24)\n"
                      "   n0: 6000 0x8048477: main (prog.c:26)\n"
                      " n0: 10000 0x8048457: main (prog.c:22)\n"
                      " n2: 8000 0x8048418: g (prog.c:8)\n"
                      "  n1: 4000 0x8048436: f (prog.c:14)\n"
                      # "   n0: 4000 0x8048472: main (prog.c:24)\n"
                      "  n0: 4000 0x8048477: main (prog.c:26)\n"
                      " n1: 2000 0x8048431: f (prog.c:13)\n"
                      "  n0: 2000 0x8048472: main (prog.c:24)\n")

        with self.assertRaises(msparser.ParseError):
            msparser.parse(fd)


if __name__ == "__main__":
    main()
