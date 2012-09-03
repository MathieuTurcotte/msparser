#!/usr/bin/env python3

# Copyright (c) 2011 Mathieu Turcotte
# Licensed under the MIT license.

import json
import msparser
import optparse
import os
import re
import sys
import traceback


def inst_unit_scaling(peak):
    """
    Given the peak instruction value to plot, get a scaling factor which will
    divide the data point and the resulting unit name. Those informations is
    used to scale the data and set the axis label in the print_gnuplot_script
    function.
    """

    unit_table = [
        (2 ** 0, "i"),
        (2 ** 10, "ki"),
        (2 ** 20, "Mi"),
        (2 ** 30, "Gi"),
        (2 ** 40, "Ti"),
        (2 ** 50, "Pi"),
        (2 ** 60, "Ei")
    ]

    for value, name in unit_table:
        if peak // value < 2 ** 10:
            return (value, name)


def time_unit_scaling(peak):
    """
    Given the peak time value to plot, get a scaling factor which will divide
    the data point and the resulting unit name. Those informations is used to
    scale the data and set the axis label in the print_gnuplot_script function.
    """

    if peak // 1000 < 1:
        return (1, "milliseconds (ms)")
    elif 1 <= peak // 1000 < 60:
        return (1000, "seconds (s)")
    else:
        return (60000, "minutes (m)")


def memory_unit_scaling(peak):
    """
    Given the peak memory value to plot, get a scaling factor which will divide
    the data point and the resulting unit name. Those informations is used to
    scale the data and set the axis label in the print_gnuplot_script function.
    """

    unit_table = [
        (2 ** 0, "bytes (B)"),
        (2 ** 10, "kibibytes (KiB)"),
        (2 ** 20, "mebibytes (MiB)"),
        (2 ** 30, "gibibytes (GiB)"),
        (2 ** 40, "tebibytes (TiB)"),
        (2 ** 50, "pebibytes (PiB)"),
        (2 ** 60, "exbibytes (EiB)")
    ]

    for value, name in unit_table:
        if peak // value < 2 ** 10:
            return (value, name)


def print_as_json(mdata, indent):
    """
    Print mdata as json. If indent is true, the outputed json is indented.
    """

    if indent:
        print(json.dumps(mdata, indent=1))
    else:
        print(json.dumps(mdata))


def print_gnuplot_dtable(mdata):
    """
    Print mdata as a data table ready for gnuplot consumption.
    """

    print("# ms_processor.py - (C) Mathieu Turcotte, 2011")
    print("# valgrind --tool=massif", mdata["desc"], mdata["cmd"])
    print("# id", "time", "heap", "extra", "total", "stack", sep="\t")
    for snapshot in mdata["snapshots"]:
        id = snapshot["id"]
        time = snapshot["time"]
        heap = snapshot["mem_heap"]
        extra = snapshot["mem_heap_extra"]
        total = heap + extra
        stack = snapshot["mem_stack"]
        print("  " + str(id), time, heap, extra, total, stack, sep="\t")


GNUPLOT_HEADER = """\
# msprint.py - (C) Mathieu Turcotte, 2011
# yscale: {yscale}
# xscale: {xscale}
set terminal {format} giant size {xsize}, {ysize}
set output "{filename}.{extension}"
set title "valgrind --tool=massif {description} {command}"
set xlabel "{xlabel}"
set ylabel "{ylabel}"
set mxtics 10
set mytics 10
set grid
plot "-" using 1:2 title "Useful Heap",\\
     "-" using 1:2 title "Wasted Heap",\\
     "-" using 1:2 title "Total Heap"
"""


def print_gnuplot_script(mdata, filename, format="png", xsize=1024, ysize=768):
    """
    Print mdata as a gnuplot batch script which, when executed, will produce a
    plot of the massif.out data.
    """

    # Retrieve the time peak and determine the y axis
    # scale and label.
    peak_snapshot_id = mdata["peak_snapshot"]
    peak_snapshot = mdata["snapshots"][peak_snapshot_id]
    memory_peak = peak_snapshot["mem_heap"] + peak_snapshot["mem_heap_extra"]
    (yscale, ylabel) = memory_unit_scaling(memory_peak)

    # Retrieve the time peak and the time unit in order
    # to calculate the x axis scale and label.
    time_peak = mdata["snapshots"][-1]["time"]
    time_unit = mdata["time_unit"]
    if time_unit == "B":
        (xscale, xlabel) = memory_unit_scaling(time_peak)
    elif time_unit == "ms":
        (xscale, xlabel) = time_unit_scaling(time_peak)
    elif time_unit == "i":
        (xscale, xlabel) = inst_unit_scaling(time_peak)
    else:
        raise Exception("Can't handle time unit.")

    # Output the gnuplot script header.
    print(GNUPLOT_HEADER.format(
        format=format,
        filename=filename,
        extension=format,
        description=mdata["desc"],
        command=mdata["cmd"],
        xsize=xsize,
        ysize=ysize,
        xscale=xscale,
        yscale=yscale,
        xlabel=xlabel,
        ylabel=ylabel
    ))

    # Output the useful heap data.
    for snapshot in mdata["snapshots"]:
        print(snapshot["time"] / xscale,
              snapshot["mem_heap"] / yscale, sep="\t")
    print("end")

    # Then, output the wasted heap data.
    for snapshot in mdata["snapshots"]:
        print(snapshot["time"] / xscale,
              snapshot["mem_heap_extra"] / yscale, sep="\t")
    print("end")

    # Finally, output the total heap data.
    for snapshot in mdata["snapshots"]:
        total = snapshot["mem_heap"] + snapshot["mem_heap_extra"]
        print(snapshot["time"] / xscale,
              total / yscale, sep="\t")
    print("end")


def parse_args():
    usage = "usage: %prog [options] massif-out-file"
    description = "Extraction utility for the massif.out data format."
    version = "%prog 1.0"

    argparser = optparse.OptionParser(description=description,
                                      usage=usage, version=version)

    argparser.add_option("-o", "--output",
                         dest="output",
                         default="table",
                         choices=["json", "gnuplot", "table", "graphviz"],
                         metavar="F",
                         help="specify the output format: "
                              "json, gnuplot, graphviz or table")

    json_group = optparse.OptionGroup(argparser, "JSON Options")
    json_group.add_option("-i", "--indent",
                          action="store_true",
                          dest="indent",
                          help="indent the json output")
    argparser.add_option_group(json_group)

    graphviz_group = optparse.OptionGroup(argparser, "Graphviz Options")
    graphviz_group.add_option("--snapshot",
                              type="int",
                              dest="snapshot",
                              metavar="ID",
                              help="output Graphviz script for a given "
                                   "snapshot")
    argparser.add_option_group(graphviz_group)

    gnuplot_group = optparse.OptionGroup(argparser, "GNUPlot Options")
    gnuplot_group.add_option("-f", "--format",
                             dest="format",
                             default="png",
                             choices=["png", "gif", "jpeg"],
                             metavar="F",
                             help="specify the plot output format: "
                                  "png, jpeg or gif")
    gnuplot_group.add_option("-x", "--xsize",
                             type="int",
                             dest="xsize",
                             default=1024,
                             metavar="X",
                             help="plot horizontal size")
    gnuplot_group.add_option("-y", "--ysize",
                             type="int",
                             dest="ysize",
                             default=768,
                             metavar="Y",
                             help="plot vertical size")
    argparser.add_option_group(gnuplot_group)

    # - options contains optional arguments
    # - args contains positional arguments
    (options, args) = argparser.parse_args()

    if len(args) == 0:
        argparser.error("No input file !")

    for path in args[0:]:
        if os.path.isfile(path) is False:
            argparser.error(path)

    return (options, args)


def main():
    (options, args) = parse_args()
    for path in args[0:]:
        try:
            mdata = msparser.parse_file(path)

            if options.output == "json":
                print_as_json(mdata, options.indent)
            elif options.output == "gnuplot":
                print_gnuplot_script(mdata, os.path.basename(path),
                                     options.format, options.xsize,
                                     options.ysize)
            elif options.output == "table":
                print_gnuplot_dtable(mdata)

        except ParseError as perr:
            print(perr, file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as err:
        traceback.print_exc(file=sys.stdout)
