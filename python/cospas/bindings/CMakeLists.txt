# Copyright 2020 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

########################################################################
# Check if there is C++ code at all
########################################################################
if(NOT cospas_sources)
    message(STATUS "No C++ sources... skipping python bindings")
    return()
endif(NOT cospas_sources)

########################################################################
# Check for pygccxml
########################################################################
gr_python_check_module_raw("pygccxml" "import pygccxml" PYGCCXML_FOUND)

include(GrPybind)

########################################################################
# Python Bindings
########################################################################

list(APPEND cospas_python_files
    cospas_sarsat_demodulator_python.cc
    cospas_burst_detector_python.cc
    burst_router_python.cc
    python_bindings.cc)

gr_pybind_make_oot(cospas ../../.. gr::cospas "${cospas_python_files}")

# copy bindings extension for use in QA test module
add_custom_command(
    TARGET cospas_python
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:cospas_python>
            ${PROJECT_BINARY_DIR}/test_modules/gnuradio/cospas/)

install(
    TARGETS cospas_python
    DESTINATION ${GR_PYTHON_DIR}/gnuradio/cospas
    COMPONENT pythonapi)
