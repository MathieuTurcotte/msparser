# Copyright (c) 2011 Mathieu Turcotte
# Licensed under the MIT license.

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
   n0: 50456 0x8049C2C: main (memory.cpp:30)
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
            line = self.lines[self.index]
            self.index += 1
            return line + "\n"
        else:
            return ""


def parse(content):
    fd = MockFile(content)
    return msparser.parse(fd)


class MassifParserTest(TestCase):
    def test_parse_time_unit(self):
        data = parse(EMPTY_SNAPSHOTS)
        self.assertEqual(data["time_unit"], "ms")

    def test_parse_cmd(self):
        data = parse(EMPTY_SNAPSHOTS)
        self.assertEqual(data["cmd"], "./a.out")

    def test_parse_desc(self):
        data = parse(EMPTY_SNAPSHOTS)
        self.assertEqual(data["desc"], "--time-unit=ms")

    def test_parse_snaphosts(self):
        data = parse(EMPTY_SNAPSHOTS)
        self.assertEqual(len(data["snapshots"]), 3)

    def test_parse_empty_snapshot(self):
        data = parse(EMPTY_SNAPSHOTS)
        snapshot = data["snapshots"][2]
        self.assertEqual(snapshot["id"], 2, "id")
        self.assertEqual(snapshot["time"], 184, "time")
        self.assertEqual(snapshot["mem_heap"], 2000, "mem_heap")
        self.assertEqual(snapshot["mem_heap_extra"], 16, "mem_heap_extra")
        self.assertEqual(snapshot["mem_stack"], 0, "mem_stack")
        self.assertEqual(snapshot["heap_tree"], None, "heap_tree")

    def test_parse_snapshot_heap_tree(self):
        data = parse(DETAILED_SNAPSHOTS)
        snapshot = data["snapshots"][1]

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
        data = parse(DETAILED_SNAPSHOTS)
        peak_snapshot_index = data["peak_snapshot_index"]
        self.assertEqual(peak_snapshot_index, 3)

if __name__ == "__main__":
    main()
