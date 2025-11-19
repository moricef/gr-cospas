/*
 * Copyright 2025 Free Software Foundation, Inc.
 *
 * This file is part of GNU Radio
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 */

#include <pybind11/complex.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include <gnuradio/cospas/cospas_burst_detector.h>

void bind_cospas_burst_detector(py::module& m)
{
    using cospas_burst_detector = ::gr::cospas::cospas_burst_detector;

    py::class_<cospas_burst_detector,
               gr::block,
               gr::basic_block,
               std::shared_ptr<cospas_burst_detector>>(
        m, "cospas_burst_detector", "COSPAS-SARSAT burst detector with circular buffering")

        .def(py::init(&cospas_burst_detector::make),
             py::arg("sample_rate"),
             py::arg("buffer_duration_ms") = 1500,
             py::arg("threshold") = 0.1f,
             py::arg("min_burst_duration_ms") = 200,
             py::arg("debug_mode") = false)

        .def("get_bursts_detected",
             &cospas_burst_detector::get_bursts_detected)

        .def("reset_statistics",
             &cospas_burst_detector::reset_statistics)

        .def("set_debug_mode",
             &cospas_burst_detector::set_debug_mode,
             py::arg("enable"))

        ;
}
