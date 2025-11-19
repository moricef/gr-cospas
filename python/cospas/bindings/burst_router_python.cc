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

#include <gnuradio/cospas/burst_router.h>

void bind_burst_router(py::module& m)
{
    using burst_router = ::gr::cospas::burst_router;

    py::class_<burst_router,
               gr::block,
               gr::basic_block,
               std::shared_ptr<burst_router>>(
        m, "burst_router", "Router automatique pour bursts 1G/2G COSPAS-SARSAT")

        .def(py::init(&burst_router::make),
             py::arg("sample_rate") = 40000.0f,
             py::arg("debug_mode") = false)

        .def("get_bursts_1g",
             &burst_router::get_bursts_1g)

        .def("get_bursts_2g",
             &burst_router::get_bursts_2g)

        .def("reset_statistics",
             &burst_router::reset_statistics)

        .def("set_debug_mode",
             &burst_router::set_debug_mode,
             py::arg("enable"))

        ;
}
