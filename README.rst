Massif Parser
=============

A parser for Valgrind massif.out files.

The msparser module offers a simple interface to parse the Valgrind massif.out
file format, i.e. data files produced by the valgrind heap profiler.

How do I use it?
----------------

Import the module
`````````````````
As usual, import the module::

    >>> import msparser

Parse a massif.out file
```````````````````````
To extract the data from a massif.out file, you simply have to give its path to
the ``parse_file`` function::

    >>> data = msparser.parse_file('massif.out')

You could also use the ``msparser.parse`` function directly with a file
descriptor.

Understand the data
```````````````````

The parsed data is returned as a dictionary which follow closely the massif.out
format. It looks like this::

    >>> from pprint import pprint
    >>> pprint(data, depth=1)
    {'cmd': './a.out',
     'desc': '--time-unit=ms',
     'detailed_snapshots_index': [...],
     'peak_snapshot_index': 16,
     'snapshots': [...],
     'time_unit': 'ms'}

The ``detailed_snapshots_index`` and ``peak_snapshot_index`` fields allow
efficient localisation of the detailled and peak snapshots in the ``snapshots``
list. For example, to retrieve the peak snapshot from the ``snapshots`` list,
we could do::

    >>> peak_index = data['peak_snapshot_index']
    >>> peak_snapshot = data['snapshots'][peak_index]

The ``snapshots`` list stores dictionaries representing each snapshot data::

    >>> second_snapshot = data['snapshots'][1]
    >>> pprint(second_snapshot)
    {'heap_tree': None,
     'id': 1,
     'mem_heap': 1000,
     'mem_heap_extra': 8,
     'mem_stack': 0,
     'time': 183}

If the snapshot is detailled, the ``heap_tree`` field, instead of being None,
will store a heap tree::

    >>> peak_heap_tree = peak_snapshot['heap_tree']
    >>> pprint(peak_heap_tree, depth=3)
    {'children': [{'children': [...], 'details': {...}, 'nbytes': 12000},
                  {'children': [], 'details': {...}, 'nbytes': 10000},
                  {'children': [...], 'details': {...}, 'nbytes': 8000},
                  {'children': [...], 'details': {...}, 'nbytes': 2000}],
     'details': None,
     'nbytes': 32000}

On the root node, the ``details`` field is always None, but on the children
nodes it's a dictionary which looks like this::

    >>> first_child = peak_snapshot['heap_tree']['children'][0]
    >>> pprint(first_child['details'], width=1)
    {'address': '0x8048404',
     'file': 'prog.c',
     'function': 'h',
     'line': 4}

Obviously, if the node is below the massif threshold, the ``details`` field
will be None.

Putting It All Together
```````````````````````
From this data structure, it's very easy to write a procedure that produce a
data table ready for Gnuplot consumption::

    print("# valgrind --tool=massif", data['desc'], data['cmd'])
    print("# id", "time", "heap", "extra", "total", "stack", sep='\t')
    for snapshot in data['snapshots']:
        id = snapshot['id']
        time = snapshot['time']
        heap = snapshot['mem_heap']
        extra = snapshot['mem_heap_extra']
        total = heap + extra
        stack = snapshot['mem_stack']
        print('  '+str(id), time, heap, extra, total, stack, sep='\t')

The output should looks like this::

    # valgrind --tool=massif --time-unit=ms ./a.out
    # id    time    heap    extra   total   stack
      0     0       0       0       0       0
      1     183     1000    8       1008    0
      2     184     2000    16      2016    0
      3     184     3000    24      3024    0
      4     184     4000    32      4032    0
      5     184     5000    40      5040    0
      6     184     6000    48      6048    0
      7     184     7000    56      7056    0
      8     184     8000    64      8064    0
      9     184     9000    72      9072    0

Tests
-----

To run msparser's test suite::

    $ python msparser_test.py --verbose

The current build status on travis: http://travis-ci.org/#!/MathieuTurcotte/msparser

License
-------

This code is free to use under the terms of the `MIT license <http://mturcotte.mit-license.org/>`_.
