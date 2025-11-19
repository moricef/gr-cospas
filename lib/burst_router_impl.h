/* -*- c++ -*- */
/*
 * Copyright 2025 COSPAS-SARSAT.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_COSPAS_BURST_ROUTER_IMPL_H
#define INCLUDED_COSPAS_BURST_ROUTER_IMPL_H

#include <gnuradio/cospas/burst_router.h>
#include <vector>
#include <mutex>

namespace gr {
namespace cospas {

class burst_router_impl : public burst_router
{
private:
    // Configuration
    float d_sample_rate;
    bool d_debug_mode;

    // État du burst en cours
    std::vector<gr_complex> d_current_burst;
    bool d_in_burst;
    bool d_burst_ready_for_output;  // true après burst_end
    int d_burst_output_offset;  // Position de sortie dans le burst actuel

    // Statistiques
    int d_bursts_1g;
    int d_bursts_2g;

    // Thread-safety
    mutable std::mutex d_mutex;

    // Méthodes privées
    enum BurstType {
        TYPE_1G,  // First Generation (FGB)
        TYPE_2G   // Second Generation (SGB)
    };

    BurstType detect_burst_type(const std::vector<gr_complex>& samples);
    bool detect_unmodulated_carrier(const std::vector<gr_complex>& samples, int window_size);

    // Message handler
    void handle_burst_message(pmt::pmt_t msg);

public:
    burst_router_impl(float sample_rate, bool debug_mode);
    ~burst_router_impl();

    // GNU Radio work
    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items) override;

    // Méthodes publiques
    int get_bursts_1g() const override;
    int get_bursts_2g() const override;
    void reset_statistics() override;
    void set_debug_mode(bool enable) override;
};

} // namespace cospas
} // namespace gr

#endif /* INCLUDED_COSPAS_BURST_ROUTER_IMPL_H */
