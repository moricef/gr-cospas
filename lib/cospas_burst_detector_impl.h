/* -*- c++ -*- */
/*
 * Copyright 2025 COSPAS-SARSAT.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_COSPAS_COSPAS_BURST_DETECTOR_IMPL_H
#define INCLUDED_COSPAS_COSPAS_BURST_DETECTOR_IMPL_H

#include <gnuradio/cospas/cospas_burst_detector.h>
#include <deque>
#include <vector>
#include <mutex>

namespace gr {
namespace cospas {

class cospas_burst_detector_impl : public cospas_burst_detector
{
private:
    // Paramètres de configuration
    float d_sample_rate;
    int d_buffer_duration_ms;
    float d_threshold_factor;   // Facteur multiplicatif du niveau du signal (0.0-1.0)
    int d_min_burst_duration_ms;
    bool d_debug_mode;

    // Tailles calculées
    int d_buffer_size;          // Taille du buffer circulaire en échantillons
    int d_min_burst_samples;    // Durée minimale d'un burst en échantillons

    // Seuil adaptatif
    float d_adaptive_threshold; // Seuil calculé automatiquement
    bool d_threshold_initialized; // Indicateur de calcul du seuil
    std::vector<float> d_amplitude_buffer; // Buffer pour calcul statistique

    // Autocorrélation
    int d_samples_per_bit;
    std::vector<float> d_correlation_buffer;
    int d_buffer_index;
    float compute_autocorrelation();

    // Buffer circulaire
    std::deque<gr_complex> d_circular_buffer;

    // État de détection
    enum BurstState {
        IDLE,           // Pas de burst en cours
        IN_BURST,       // Burst en cours de capture
        BURST_COMPLETE  // Burst capturé, prêt a sortir
    };

    BurstState d_state;
    std::vector<gr_complex> d_burst_samples;  // Échantillons du burst en cours de détection
    int d_silence_count;                       // Compteur d'échantillons sous le seuil

    // Sortie du burst en cours (peut être produit sur plusieurs appels)
    std::vector<gr_complex> d_output_burst;   // Burst prêt a sortir
    size_t d_output_offset;                    // Position dans d_output_burst

    // Statistiques
    int d_bursts_detected;

    // Thread-safety
    mutable std::mutex d_mutex;

    // Méthodes privées
    void process_sample(const gr_complex& sample);
    bool is_burst_ready();
    void extract_burst(std::vector<gr_complex>& burst_data);
    void reset_burst_state();

public:
    cospas_burst_detector_impl(float sample_rate,
                               int buffer_duration_ms,
                               float threshold,
                               int min_burst_duration_ms,
                               bool debug_mode);
    ~cospas_burst_detector_impl();

    // GNU Radio general_work
    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items) override;

    // Méthodes publiques
    int get_bursts_detected() const override;
    void reset_statistics() override;
    void set_debug_mode(bool enable) override;
};

} // namespace cospas
} // namespace gr

#endif /* INCLUDED_COSPAS_COSPAS_BURST_DETECTOR_IMPL_H */
