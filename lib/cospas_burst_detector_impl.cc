/* -*- c++ -*- */
/*
 * Copyright 2025 COSPAS-SARSAT.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "cospas_burst_detector_impl.h"
#include <gnuradio/io_signature.h>
#include <pmt/pmt.h>
#include <iostream>
#include <cmath>
#include <algorithm>
#include <cstring>

namespace gr {
namespace cospas {

cospas_burst_detector::sptr
cospas_burst_detector::make(float sample_rate,
                            int buffer_duration_ms,
                            float threshold,
                            int min_burst_duration_ms,
                            bool debug_mode)
{
    return gnuradio::make_block_sptr<cospas_burst_detector_impl>(
        sample_rate, buffer_duration_ms, threshold, min_burst_duration_ms, debug_mode);
}

cospas_burst_detector_impl::cospas_burst_detector_impl(float sample_rate,
                                                       int buffer_duration_ms,
                                                       float threshold,
                                                       int min_burst_duration_ms,
                                                       bool debug_mode)
    : gr::block("cospas_burst_detector",
                gr::io_signature::make(1, 1, sizeof(gr_complex)),
                gr::io_signature::make(1, 1, sizeof(gr_complex))),
      d_sample_rate(sample_rate),
      d_buffer_duration_ms(buffer_duration_ms),
      d_threshold_factor(threshold),
      d_min_burst_duration_ms(min_burst_duration_ms),
      d_debug_mode(debug_mode),
      d_adaptive_threshold(0.0f),
      d_threshold_initialized(false),
      d_state(IDLE),
      d_silence_count(0),
      d_output_offset(0),
      d_bursts_detected(0)
{
    // Calculer les tailles
    d_buffer_size = static_cast<int>((sample_rate * buffer_duration_ms) / 1000.0f);
    d_min_burst_samples = static_cast<int>((sample_rate * min_burst_duration_ms) / 1000.0f);

    // Réserver le buffer pour calcul du seuil adaptatif (500ms de signal)
    // Plus long pour capturer la dynamique réelle du signal, pas juste le bruit initial
    int calibration_samples = static_cast<int>(sample_rate * 0.5f);
    d_amplitude_buffer.reserve(calibration_samples);

    // Enregistrer message port pour envoi asynchrone de bursts
    message_port_register_out(pmt::mp("bursts"));

    if (d_debug_mode) {
        std::cout << "[BURST_DETECTOR] Initialized:" << std::endl;
        std::cout << "  Sample rate: " << d_sample_rate << " Hz" << std::endl;
        std::cout << "  Buffer size: " << d_buffer_size << " samples ("
                  << d_buffer_duration_ms << " ms)" << std::endl;
        std::cout << "  Threshold factor: " << d_threshold_factor << std::endl;
        std::cout << "  Min burst duration: " << d_min_burst_samples << " samples ("
                  << d_min_burst_duration_ms << " ms)" << std::endl;
        std::cout << "  Calibration samples: " << calibration_samples << std::endl;
        std::cout << "  Message port 'bursts' enregistre" << std::endl;
    }
}

cospas_burst_detector_impl::~cospas_burst_detector_impl()
{
}

void cospas_burst_detector_impl::process_sample(const gr_complex& sample)
{
    float amplitude = std::abs(sample);

    // Phase de calibration : collecter les amplitudes pour calculer le seuil adaptatif
    if (!d_threshold_initialized) {
        d_amplitude_buffer.push_back(amplitude);

        // Une fois le buffer de calibration rempli, calculer le seuil
        if (d_amplitude_buffer.size() >= d_amplitude_buffer.capacity()) {
            // Utiliser le max pour détecter le niveau du signal le plus fort
            // Ceci permet de détecter les bursts même s'ils arrivent tôt
            float max_amp = *std::max_element(d_amplitude_buffer.begin(), d_amplitude_buffer.end());

            // Seuil adaptatif : threshold_factor * max amplitude
            d_adaptive_threshold = d_threshold_factor * max_amp;

            // Seuil minimum : éviter un seuil trop bas si que du bruit
            const float MIN_THRESHOLD = 0.01f;  // 1% d'amplitude
            if (d_adaptive_threshold < MIN_THRESHOLD) {
                d_adaptive_threshold = MIN_THRESHOLD;
                if (d_debug_mode) {
                    std::cout << "[BURST_DETECTOR] Warning: low signal, using minimum threshold" << std::endl;
                }
            }

            d_threshold_initialized = true;

            if (d_debug_mode) {
                std::cout << "[BURST_DETECTOR] Calibration complete:" << std::endl;
                std::cout << "  Max amplitude: " << max_amp << std::endl;
                std::cout << "  Adaptive threshold: " << d_adaptive_threshold << std::endl;
            }

            // Libérer la mémoire du buffer de calibration
            d_amplitude_buffer.clear();
            d_amplitude_buffer.shrink_to_fit();
        }
        // Pendant la calibration, ne pas détecter de bursts
        return;
    }

    switch (d_state) {
        case IDLE:
            // Chercher le debut d'un burst
            if (amplitude > d_adaptive_threshold) {
                d_state = IN_BURST;
                d_burst_samples.clear();
                d_burst_samples.push_back(sample);
                d_silence_count = 0;

                if (d_debug_mode) {
                    std::cout << "[BURST_DETECTOR] Burst started, amp=" << amplitude << std::endl;
                }
            }
            break;

        case IN_BURST:
            // Stocker l'échantillon
            d_burst_samples.push_back(sample);

            // Suivre le burst
            if (amplitude > d_adaptive_threshold) {
                // Signal fort : réinitialiser le compteur de silence
                d_silence_count = 0;
            } else {
                // Signal faible : incrémenter le compteur de silence
                d_silence_count++;

                // Seuil de silence : 50ms (2000 samples @ 40kHz)
                int silence_threshold = static_cast<int>(d_sample_rate * 0.05f);

                if (d_silence_count >= silence_threshold) {
                    // Fin du burst detectee
                    int burst_duration = static_cast<int>(d_burst_samples.size());

                    if (d_debug_mode) {
                        std::cout << "[BURST_DETECTOR] Fin detectee: amplitude=" << amplitude
                                  << ", threshold=" << d_adaptive_threshold
                                  << ", silence_count=" << d_silence_count
                                  << ", burst_duration=" << burst_duration << std::endl;
                    }

                    if (burst_duration >= d_min_burst_samples) {
                        // Burst valide - NE PAS retirer le silence, garder 520ms complets
                        // On garde tous les echantillons pour avoir le burst complet de 20800 samples
                        // Le demodulateur gerera le padding

                        d_state = BURST_COMPLETE;
                        d_bursts_detected++;

                        if (d_debug_mode) {
                            std::cout << "[BURST_DETECTOR] Burst #" << d_bursts_detected
                                      << " complete: duration=" << d_burst_samples.size() << " samples ("
                                      << (d_burst_samples.size() * 1000.0f / d_sample_rate) << " ms)"
                                      << std::endl;
                        }
                    } else {
                        // Burst trop court : ignorer
                        if (d_debug_mode) {
                            std::cout << "[BURST_DETECTOR] Burst too short (" << burst_duration
                                      << " < " << d_min_burst_samples << ") - ignored" << std::endl;
                        }
                        reset_burst_state();
                    }
                }
            }
            break;

        case BURST_COMPLETE:
            // Attendre que le burst soit extrait (ne rien faire)
            break;
    }
}

bool cospas_burst_detector_impl::is_burst_ready()
{
    return d_state == BURST_COMPLETE;
}

void cospas_burst_detector_impl::extract_burst(std::vector<gr_complex>& burst_data)
{
    // Copier les echantillons du burst
    burst_data = d_burst_samples;

    // Réinitialiser l'état apres extraction
    reset_burst_state();
}

void cospas_burst_detector_impl::reset_burst_state()
{
    d_state = IDLE;
    d_burst_samples.clear();
    d_silence_count = 0;
}

int cospas_burst_detector_impl::general_work(int noutput_items,
                                             gr_vector_int& ninput_items,
                                             gr_vector_const_void_star& input_items,
                                             gr_vector_void_star& output_items)
{
    const gr_complex* in = static_cast<const gr_complex*>(input_items[0]);
    gr_complex* out = static_cast<gr_complex*>(output_items[0]);

    std::lock_guard<std::mutex> lock(d_mutex);

    int ninput = ninput_items[0];
    int produced = 0;
    int consumed = 0;

    // Priorité 1: Si on a un burst en cours de sortie, continuer a le produire
    if (d_output_offset < d_output_burst.size()) {
        size_t remaining = d_output_burst.size() - d_output_offset;
        size_t to_copy = std::min(remaining, static_cast<size_t>(noutput_items));

        // Copier la portion du burst
        std::memcpy(out, &d_output_burst[d_output_offset], to_copy * sizeof(gr_complex));
        d_output_offset += to_copy;
        produced = static_cast<int>(to_copy);

        // Si le burst est completement sorti, le libérer
        if (d_output_offset >= d_output_burst.size()) {
            if (d_debug_mode) {
                std::cout << "[BURST_DETECTOR] Burst fully output ("
                          << d_output_burst.size() << " samples)" << std::endl;
            }

            // Tag de fin de burst (à la dernière position)
            add_item_tag(0, nitems_written(0) + produced - 1,
                         pmt::intern("burst_end"),
                         pmt::PMT_T);

            d_output_burst.clear();
            d_output_offset = 0;
        }

        // Ne pas consommer d'entree pendant qu'on sort un burst
        consume_each(0);
        return produced;
    }

    // Priorité 2: Traiter les echantillons entrants
    for (int i = 0; i < ninput; i++) {
        process_sample(in[i]);
    }
    consumed = ninput;

    // Priorité 3: Si un burst est pret, le préparer pour la sortie
    if (is_burst_ready()) {
        extract_burst(d_output_burst);
        d_output_offset = 0;

        // Envoyer le burst via message port (asynchrone)
        pmt::pmt_t burst_msg = pmt::make_dict();
        pmt::pmt_t samples_vec = pmt::init_c32vector(d_output_burst.size(), d_output_burst.data());
        burst_msg = pmt::dict_add(burst_msg, pmt::mp("samples"), samples_vec);
        burst_msg = pmt::dict_add(burst_msg, pmt::mp("size"), pmt::from_long(d_output_burst.size()));
        burst_msg = pmt::dict_add(burst_msg, pmt::mp("timestamp"), pmt::from_uint64(nitems_read(0)));

        message_port_pub(pmt::mp("bursts"), burst_msg);

        if (d_debug_mode) {
            std::cout << "[BURST_DETECTOR] Message envoye: " << d_output_burst.size()
                      << " samples via port 'bursts'" << std::endl;
        }

        // Tag de debut de burst (pour compatibilité stream)
        add_item_tag(0, nitems_written(0),
                     pmt::intern("burst_start"),
                     pmt::from_long(d_output_burst.size()));

        // Produire autant que possible immédiatement
        size_t to_copy = std::min(d_output_burst.size(), static_cast<size_t>(noutput_items));
        std::memcpy(out, &d_output_burst[0], to_copy * sizeof(gr_complex));
        d_output_offset = to_copy;
        produced = static_cast<int>(to_copy);

        if (d_debug_mode) {
            if (to_copy < d_output_burst.size()) {
                std::cout << "[BURST_DETECTOR] Burst partial output: "
                          << to_copy << " / " << d_output_burst.size() << " samples" << std::endl;
            } else {
                std::cout << "[BURST_DETECTOR] Burst fully output ("
                          << d_output_burst.size() << " samples)" << std::endl;

                // Tag de fin de burst (à la dernière position)
                add_item_tag(0, nitems_written(0) + produced - 1,
                             pmt::intern("burst_end"),
                             pmt::PMT_T);

                d_output_burst.clear();
                d_output_offset = 0;
            }
        }
    }

    // Consommer les echantillons d'entree
    consume_each(consumed);

    // Retourner le nombre d'echantillons produits
    return produced;
}

int cospas_burst_detector_impl::get_bursts_detected() const
{
    std::lock_guard<std::mutex> lock(d_mutex);
    return d_bursts_detected;
}

void cospas_burst_detector_impl::reset_statistics()
{
    std::lock_guard<std::mutex> lock(d_mutex);
    d_bursts_detected = 0;
}

void cospas_burst_detector_impl::set_debug_mode(bool enable)
{
    std::lock_guard<std::mutex> lock(d_mutex);
    d_debug_mode = enable;
}

} // namespace cospas
} // namespace gr
