/* -*- c++ -*- */
/*
 * Copyright 2025 COSPAS-SARSAT.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "cospas_burst_detector_impl.h"
#include <gnuradio/io_signature.h>
#include <pmt/pmt.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <iostream>

namespace gr {
namespace cospas {

cospas_burst_detector::sptr cospas_burst_detector::make(float sample_rate,
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
      d_calibration_p95_amplitude(0.0f),
      d_samples_per_bit(static_cast<int>(sample_rate / 400.0f)),
      d_buffer_index(0),
      d_state(IDLE),
      d_silence_count(0),
      d_burst_mean_snr(0.0f),
      d_burst_detected_by_correlation(false),
      d_output_offset(0),
      d_bursts_detected(0)
{
    d_buffer_size = static_cast<int>((sample_rate * buffer_duration_ms) / 1000.0f);
    d_min_burst_samples =
        static_cast<int>((sample_rate * min_burst_duration_ms) / 1000.0f);

    int calibration_samples = static_cast<int>(sample_rate * 0.5f);
    d_amplitude_buffer.reserve(calibration_samples);
    d_amplitude_raw_buffer.reserve(calibration_samples);

    d_correlation_buffer.resize(2 * d_samples_per_bit, 0.0f);

    // Enregistrer message port pour envoi asynchrone de bursts
    message_port_register_out(pmt::mp("bursts"));

    if (d_debug_mode) {
        std::cerr << "[BURST_DETECTOR] Initialized:" << std::endl;
        std::cerr << "  Sample rate: " << d_sample_rate << " Hz" << std::endl;
        std::cerr << "  Buffer size: " << d_buffer_size << " samples ("
                  << d_buffer_duration_ms << " ms)" << std::endl;
        std::cerr << "  Threshold factor: " << d_threshold_factor << std::endl;
        std::cerr << "  Min burst duration: " << d_min_burst_samples << " samples ("
                  << d_min_burst_duration_ms << " ms)" << std::endl;
        std::cerr << "  Calibration samples: " << calibration_samples << std::endl;
        std::cerr << "  Message port 'bursts' enregistre" << std::endl;
    }
}

cospas_burst_detector_impl::~cospas_burst_detector_impl() {}

float cospas_burst_detector_impl::compute_autocorrelation()
{
    float mean = 0.0f;
    for (int i = 0; i < 2 * d_samples_per_bit; i++) {
        mean += d_correlation_buffer[i];
    }
    mean /= (2 * d_samples_per_bit);

    float correlation = 0.0f;
    for (int i = 0; i < d_samples_per_bit; i++) {
        int idx1 = (d_buffer_index + i) % (2 * d_samples_per_bit);
        int idx2 = (d_buffer_index + i + d_samples_per_bit) % (2 * d_samples_per_bit);
        correlation +=
            (d_correlation_buffer[idx1] - mean) * (d_correlation_buffer[idx2] - mean);
    }

    return std::abs(correlation);
}

void cospas_burst_detector_impl::forecast(int noutput_items,
                                           gr_vector_int& ninput_items_required)
{
    // Le burst detector traite les échantillons en entrée indépendamment de la sortie
    // On bufferise les bursts en interne, donc on demande toujours des échantillons
    // IMPORTANT: Limiter à 1024 pour éviter de bloquer le scheduler si noutput_items est trop grand
    int requested = std::min(noutput_items, 1024);

    if (d_debug_mode) {
        static int forecast_count = 0;
        forecast_count++;
        // Log premier appel ET toutes les 1000 fois
        if (forecast_count == 1 || forecast_count % 1000 == 0) {
            std::cerr << "[BURST_DETECTOR] forecast() called " << forecast_count
                      << " times, noutput=" << noutput_items
                      << ", requesting " << requested << " input samples" << std::endl;
        }
    }

    for (unsigned int i = 0; i < ninput_items_required.size(); i++) {
        ninput_items_required[i] = requested;
    }
}

void cospas_burst_detector_impl::process_sample(const gr_complex& sample)
{
    float amplitude = std::abs(sample);

    d_correlation_buffer[d_buffer_index] = amplitude;
    d_buffer_index = (d_buffer_index + 1) % (2 * d_samples_per_bit);

    // Calculer la corrélation AVANT le squelch pour détecter signaux faibles
    float correlation = compute_autocorrelation();

    // Squelch adaptatif: bloque seulement si amplitude ET corrélation sont faibles
    // Pour signaux faibles, la corrélation peut détecter même si amplitude < squelch
    if (d_threshold_initialized && d_state == IDLE) {
        float squelch_threshold;

        if (d_calibration_p95_amplitude >= 0.15f) {
            // Signal fort: squelch légèrement plus haut pour délimiter le burst
            squelch_threshold = 0.008f;
        } else if (d_calibration_p95_amplitude <= 0.02f) {
            // Signal faible: squelch minimal juste au-dessus du bruit
            squelch_threshold = 0.006f;
        } else {
            // Signal moyen: interpolation linéaire
            float ratio = (d_calibration_p95_amplitude - 0.02f) / (0.15f - 0.02f);
            squelch_threshold = 0.006f + ratio * (0.008f - 0.006f);
        }

        // Bloquer seulement si amplitude < squelch ET corrélation < seuil
        // Cela permet la détection par corrélation sur signaux faibles
        if (amplitude < squelch_threshold && correlation < d_adaptive_threshold) {
            if (d_debug_mode) {
                static int squelch_block_count = 0;
                squelch_block_count++;
                // Log toutes les 40000 samples bloqués (~1 seconde à 40kHz)
                if (squelch_block_count % 40000 == 0) {
                    std::cerr << "[BURST_DETECTOR] Squelch bloque: amp=" << amplitude
                              << " < " << squelch_threshold
                              << ", corr=" << correlation
                              << " < " << d_adaptive_threshold << std::endl;
                }
            }
            return;
        }

        // Log périodique en IDLE quand signal passe le squelch
        if (d_debug_mode) {
            static int idle_sample_count = 0;
            idle_sample_count++;
            // Log toutes les 10000 samples qui passent (~250 ms à 40kHz)
            if (idle_sample_count % 10000 == 0) {
                std::cerr << "[BURST_DETECTOR] IDLE sample passed squelch: amp=" << amplitude
                          << " (squelch=" << squelch_threshold << "), corr=" << correlation
                          << " (threshold=" << d_adaptive_threshold << ")" << std::endl;
            }
        }
    }

    // Decay adaptatif
    if (d_threshold_initialized) {
        const float decay_factor = 0.9999f;
        d_adaptive_threshold *= decay_factor;

        const float floor_threshold = 1e-6f;
        if (d_adaptive_threshold < floor_threshold) {
            d_adaptive_threshold = floor_threshold;
        }

        float target_threshold = d_threshold_factor * correlation;
        if (target_threshold > d_adaptive_threshold) {
            d_adaptive_threshold = target_threshold;
        }
    }

    if (!d_threshold_initialized) {
        d_amplitude_buffer.push_back(correlation);
        d_amplitude_raw_buffer.push_back(amplitude);

        if (d_amplitude_buffer.size() >= d_amplitude_buffer.capacity()) {
            float max_corr =
                *std::max_element(d_amplitude_buffer.begin(), d_amplitude_buffer.end());

            // Calculer p95 d'amplitude pour squelch adaptatif
            std::vector<float> sorted_amplitudes = d_amplitude_raw_buffer;
            std::sort(sorted_amplitudes.begin(), sorted_amplitudes.end());
            size_t p95_idx = static_cast<size_t>(sorted_amplitudes.size() * 0.95f);
            d_calibration_p95_amplitude = (p95_idx < sorted_amplitudes.size())
                                              ? sorted_amplitudes[p95_idx]
                                              : sorted_amplitudes.back();

            d_adaptive_threshold = d_threshold_factor * max_corr;

            const float MIN_THRESHOLD = 1e-6f;
            if (d_adaptive_threshold < MIN_THRESHOLD) {
                d_adaptive_threshold = MIN_THRESHOLD;
            }

            d_threshold_initialized = true;

            if (d_debug_mode) {
                // Calculer le squelch qui sera utilisé
                float squelch_threshold;
                if (d_calibration_p95_amplitude >= 0.15f) {
                    squelch_threshold = 0.008f;
                } else if (d_calibration_p95_amplitude <= 0.02f) {
                    squelch_threshold = 0.006f;
                } else {
                    float ratio = (d_calibration_p95_amplitude - 0.02f) / (0.15f - 0.02f);
                    squelch_threshold = 0.006f + ratio * (0.008f - 0.006f);
                }

                std::cerr << "[BURST_DETECTOR] Calibration:" << std::endl;
                std::cerr << "  Max correlation: " << max_corr << std::endl;
                std::cerr << "  P95 amplitude: " << d_calibration_p95_amplitude << std::endl;
                std::cerr << "  Adaptive threshold: " << d_adaptive_threshold << std::endl;
                std::cerr << "  Squelch threshold: " << squelch_threshold << std::endl;
                std::cerr << "  Amplitude threshold: " << ((d_calibration_p95_amplitude >= 0.15f) ? 0.016f : 0.012f) << std::endl;
            }

            d_amplitude_buffer.clear();
            d_amplitude_buffer.shrink_to_fit();
            d_amplitude_raw_buffer.clear();
            d_amplitude_raw_buffer.shrink_to_fit();
        }
        return;
    }

    switch (d_state) {
    case IDLE: {
        // Démarrer sur corrélation (données Manchester) OU amplitude (préambule non modulé)
        // Seuil amplitude = 2x le squelch pour éviter faux déclenchements
        float amplitude_threshold = (d_calibration_p95_amplitude >= 0.15f) ? 0.016f : 0.012f;

        if (correlation > d_adaptive_threshold || amplitude > amplitude_threshold) {
            d_state = IN_BURST;
            d_burst_samples.clear();
            d_burst_samples.push_back(sample);
            d_silence_count = 0;

            // Marquer si détection par corrélation (Manchester) → bypass squelch validation
            d_burst_detected_by_correlation = (correlation > d_adaptive_threshold);

            if (d_debug_mode) {
                std::string reason;
                if (correlation > d_adaptive_threshold && amplitude > amplitude_threshold) {
                    reason = "CORR+AMP";
                } else if (correlation > d_adaptive_threshold) {
                    reason = "CORR";
                } else {
                    reason = "AMP";
                }

                std::cerr << "[BURST_DETECTOR] *** Burst started (" << reason << ") ***" << std::endl;
                std::cerr << "  Correlation: " << correlation << " (threshold=" << d_adaptive_threshold << ")" << std::endl;
                std::cerr << "  Amplitude: " << amplitude << " (threshold=" << amplitude_threshold << ")" << std::endl;
            }
        }
        break;
    }

    case IN_BURST: {
        // === TECHNIQUE 2: Tracking SNR adaptatif ===
        // Calculer SNR instantané (basé sur corrélation, pas amplitude)
        float instant_snr = correlation / (d_adaptive_threshold + 1e-9f);
        d_snr_history.push_back(instant_snr);

        // Garder seulement 100ms d'historique (4000 samples @ 40kHz)
        const size_t SNR_HISTORY_SIZE = 4000;
        if (d_snr_history.size() > SNR_HISTORY_SIZE) {
            d_snr_history.erase(d_snr_history.begin());
        }

        // Calculer SNR moyen du burst
        float sum_snr = 0.0f;
        for (float snr : d_snr_history) {
            sum_snr += snr;
        }
        d_burst_mean_snr = sum_snr / d_snr_history.size();

        // === TECHNIQUE 1: Double seuil (hystérésis) ===
        // Seuil bas adaptatif selon SNR du burst
        // SNR typique : Local 100-400, CNES Firmin <30
        float threshold_low;
        if (d_burst_mean_snr > 300.0f) {
            // Signal très fort → seuil bas à 50% du seuil haut
            threshold_low = d_adaptive_threshold * 0.5f;
        } else if (d_burst_mean_snr > 100.0f) {
            // Signal fort (local) → seuil bas à 40%
            threshold_low = d_adaptive_threshold * 0.4f;
        } else if (d_burst_mean_snr > 30.0f) {
            // Signal moyen → seuil bas à 30%
            threshold_low = d_adaptive_threshold * 0.3f;
        } else {
            // Signal faible (CNES distant) → seuil bas à 20% (très tolérant)
            threshold_low = d_adaptive_threshold * 0.2f;
        }

        // Utiliser le seuil BAS pour rester dans le burst
        // Corrélation OU amplitude (pour préambule non modulé)
        float amplitude_threshold = (d_calibration_p95_amplitude >= 0.15f) ? 0.016f : 0.012f;

        if (correlation > threshold_low || amplitude > amplitude_threshold) {
            // Signal présent (corrélation ou amplitude) → continuer le burst
            d_burst_samples.push_back(sample);

            // Si on était dans un creux, le valider et l'ajouter au burst
            if (!d_gap_buffer.empty()) {
                d_burst_samples.insert(d_burst_samples.end(),
                                       d_gap_buffer.begin(),
                                       d_gap_buffer.end());
                d_gap_buffer.clear();
                if (d_debug_mode) {
                    std::cerr << "[BURST_DETECTOR] Gap interpolated ("
                              << d_gap_buffer.size() << " samples)" << std::endl;
                }
            }
            d_silence_count = 0;
        } else {
            // Signal faible → possible début de creux
            d_silence_count++;

            // === TECHNIQUE 3: Interpolation des creux ===
            // Seuil court pour détecter début de creux potentiel (50ms)
            const int GAP_DETECT_THRESHOLD = static_cast<int>(d_sample_rate * 0.05f);

            if (d_silence_count >= GAP_DETECT_THRESHOLD && d_gap_buffer.empty()) {
                // Début d'un creux potentiel → passer en mode GAP
                // NE PAS transférer les échantillons déjà dans burst_samples
                // Seulement les nouveaux échantillons (à partir de maintenant) vont dans gap_buffer
                d_state = IN_GAP;
                d_gap_buffer.push_back(sample);  // Ajouter l'échantillon courant au gap
                if (d_debug_mode) {
                    std::cerr << "[BURST_DETECTOR] Potential gap detected at silence_count="
                              << d_silence_count << std::endl;
                }
            } else if (d_gap_buffer.empty()) {
                // Pas encore un creux, continuer à ajouter au burst
                d_burst_samples.push_back(sample);
            }

            // Seuil long adaptatif pour abandonner le burst
            int silence_threshold;
            if (d_burst_mean_snr > 300.0f) {
                // Signal très fort → seuil court (110ms)
                silence_threshold = static_cast<int>(d_sample_rate * 0.11f);
            } else if (d_burst_mean_snr > 100.0f) {
                // Signal fort (local) → seuil standard (120ms)
                silence_threshold = static_cast<int>(d_sample_rate * 0.12f);
            } else if (d_burst_mean_snr > 30.0f) {
                // Signal moyen → seuil tolérant (150ms)
                silence_threshold = static_cast<int>(d_sample_rate * 0.15f);
            } else {
                // Signal faible (CNES distant) → seuil très long (200ms)
                silence_threshold = static_cast<int>(d_sample_rate * 0.20f);
            }

            if (d_silence_count >= silence_threshold) {
                // Fin du burst detectee
                int burst_duration = static_cast<int>(d_burst_samples.size());

                // Calculer p95 du burst pour squelch
                std::vector<float> amplitudes;
                amplitudes.reserve(d_burst_samples.size());
                for (const auto& s : d_burst_samples) {
                    amplitudes.push_back(std::abs(s));
                }
                std::sort(amplitudes.begin(), amplitudes.end());
                size_t p95_idx = static_cast<size_t>(amplitudes.size() * 0.95f);
                float burst_p95 = (p95_idx < amplitudes.size()) ? amplitudes[p95_idx]
                                                                : amplitudes.back();

                // Squelch adaptatif juste au-dessus du plancher de bruit
                float squelch_threshold;
                if (d_calibration_p95_amplitude >= 0.15f) {
                    squelch_threshold = 0.008f;
                } else if (d_calibration_p95_amplitude <= 0.02f) {
                    squelch_threshold = 0.006f;
                } else {
                    float ratio = (d_calibration_p95_amplitude - 0.02f) / (0.15f - 0.02f);
                    squelch_threshold = 0.006f + ratio * (0.008f - 0.006f);
                }

                if (d_debug_mode) {
                    std::cerr << "[BURST_DETECTOR] Fin detectee: amplitude=" << amplitude
                              << ", threshold=" << d_adaptive_threshold
                              << ", silence_count=" << d_silence_count
                              << ", burst_duration=" << burst_duration
                              << ", p95=" << burst_p95
                              << ", squelch=" << squelch_threshold << std::endl;
                }

                // Bypass squelch si burst détecté par corrélation (Manchester fiable)
                if (!d_burst_detected_by_correlation && burst_p95 < squelch_threshold) {
                    if (d_debug_mode) {
                        std::cerr << "[BURST_DETECTOR] Burst rejected by squelch (p95="
                                  << burst_p95 << " < " << squelch_threshold << ")"
                                  << std::endl;
                    }
                    reset_burst_state();
                } else if (burst_duration >= d_min_burst_samples) {
                    // Burst valide - NE PAS retirer le silence, garder 520ms complets
                    // On garde tous les echantillons pour avoir le burst complet de 20800
                    // samples Le demodulateur gerera le padding

                    d_state = BURST_COMPLETE;
                    d_bursts_detected++;

                    if (d_debug_mode) {
                        std::cerr << "[BURST_DETECTOR] Burst #" << d_bursts_detected
                                  << " complete: duration=" << d_burst_samples.size()
                                  << " samples ("
                                  << (d_burst_samples.size() * 1000.0f / d_sample_rate)
                                  << " ms)" << std::endl;
                    }
                } else {
                    // Burst trop court : ignorer
                    if (d_debug_mode) {
                        std::cerr << "[BURST_DETECTOR] Burst too short ("
                                  << burst_duration << " < " << d_min_burst_samples
                                  << ") - ignored" << std::endl;
                    }
                    reset_burst_state();
                }
            }
        }
        break;
    }

    case BURST_COMPLETE:
        // Attendre que le burst soit extrait (ne rien faire)
        break;

    case IN_GAP: {
        // Stocker échantillons du creux temporairement
        if (d_debug_mode && d_gap_buffer.empty()) {
            std::cerr << "[BURST_DETECTOR] First sample in IN_GAP state" << std::endl;
        }
        d_gap_buffer.push_back(sample);
        d_silence_count++;

        // Pour sortir du gap, on utilise le seuil HAUT (detection initiale)
        // Ceci garantit qu'on ne sort que si le signal est vraiment revenu fort
        float gap_exit_threshold = d_adaptive_threshold;

        if (correlation > gap_exit_threshold) {
            // Signal revenu → creux confirmé court, interpoler
            d_burst_samples.insert(d_burst_samples.end(),
                                   d_gap_buffer.begin(),
                                   d_gap_buffer.end());
            d_burst_samples.push_back(sample);
            d_gap_buffer.clear();
            d_silence_count = 0;
            d_state = IN_BURST;

            if (d_debug_mode) {
                std::cerr << "[BURST_DETECTOR] Gap filled, back to IN_BURST" << std::endl;
            }
        } else {
            // Seuil long adaptatif pour abandonner le creux
            int gap_abandon_threshold;
            if (d_burst_mean_snr > 300.0f) {
                gap_abandon_threshold = static_cast<int>(d_sample_rate * 0.11f);
            } else if (d_burst_mean_snr > 100.0f) {
                gap_abandon_threshold = static_cast<int>(d_sample_rate * 0.12f);
            } else if (d_burst_mean_snr > 30.0f) {
                gap_abandon_threshold = static_cast<int>(d_sample_rate * 0.15f);
            } else {
                gap_abandon_threshold = static_cast<int>(d_sample_rate * 0.20f);
            }

            if (d_silence_count >= gap_abandon_threshold) {
                // Creux trop long → fin du burst
                d_gap_buffer.clear();  // Ne pas inclure le creux
                int burst_duration = static_cast<int>(d_burst_samples.size());

                // Calculer p95 du burst pour squelch
                std::vector<float> amplitudes;
                amplitudes.reserve(d_burst_samples.size());
                for (const auto& s : d_burst_samples) {
                    amplitudes.push_back(std::abs(s));
                }
                std::sort(amplitudes.begin(), amplitudes.end());
                size_t p95_idx = static_cast<size_t>(amplitudes.size() * 0.95f);
                float burst_p95 = (p95_idx < amplitudes.size()) ? amplitudes[p95_idx]
                                                                : amplitudes.back();

                // Squelch adaptatif juste au-dessus du plancher de bruit
                float squelch_threshold;
                if (d_calibration_p95_amplitude >= 0.15f) {
                    squelch_threshold = 0.008f;
                } else if (d_calibration_p95_amplitude <= 0.02f) {
                    squelch_threshold = 0.006f;
                } else {
                    float ratio = (d_calibration_p95_amplitude - 0.02f) / (0.15f - 0.02f);
                    squelch_threshold = 0.006f + ratio * (0.008f - 0.006f);
                }

                if (d_debug_mode) {
                    std::cerr << "[BURST_DETECTOR] Gap too long, burst end: amplitude="
                              << amplitude << ", silence_count=" << d_silence_count
                              << ", burst_duration=" << burst_duration
                              << ", p95=" << burst_p95
                              << ", squelch=" << squelch_threshold
                              << ", mean_snr=" << d_burst_mean_snr << std::endl;
                }

                // Bypass squelch si burst détecté par corrélation (Manchester fiable)
                if (!d_burst_detected_by_correlation && burst_p95 < squelch_threshold) {
                    if (d_debug_mode) {
                        std::cerr << "[BURST_DETECTOR] Burst rejected by squelch (p95="
                                  << burst_p95 << " < " << squelch_threshold << ")"
                                  << std::endl;
                    }
                    reset_burst_state();
                } else if (burst_duration >= d_min_burst_samples) {
                    d_state = BURST_COMPLETE;
                    d_bursts_detected++;

                    if (d_debug_mode) {
                        std::cerr << "[BURST_DETECTOR] Burst #" << d_bursts_detected
                                  << " complete: duration=" << d_burst_samples.size()
                                  << " samples ("
                                  << (d_burst_samples.size() * 1000.0f / d_sample_rate)
                                  << " ms)" << std::endl;
                    }
                } else {
                    if (d_debug_mode) {
                        std::cerr << "[BURST_DETECTOR] Burst too short ("
                                  << burst_duration << " < " << d_min_burst_samples
                                  << ") - ignored" << std::endl;
                    }
                    reset_burst_state();
                }
            }
        }
        break;
    }
    }
}

bool cospas_burst_detector_impl::is_burst_ready() { return d_state == BURST_COMPLETE; }

void cospas_burst_detector_impl::extract_burst(std::vector<gr_complex>& burst_data)
{
    // Copier les echantillons du burst
    burst_data = d_burst_samples;

    // Réinitialiser l'état apres extraction
    reset_burst_state();
}

void cospas_burst_detector_impl::reset_burst_state()
{
    if (d_debug_mode && d_state != IDLE) {
        std::cerr << "[BURST_DETECTOR] reset_burst_state() called from state "
                  << d_state << ", burst_samples=" << d_burst_samples.size() << std::endl;
    }
    d_state = IDLE;
    d_burst_samples.clear();
    d_gap_buffer.clear();
    d_snr_history.clear();
    d_burst_mean_snr = 0.0f;
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
        if (d_debug_mode) {
            static int output_block_count = 0;
            output_block_count++;
            if (output_block_count % 100 == 0) {
                std::cerr << "[BURST_DETECTOR] Blocked " << output_block_count
                          << " times outputting burst, offset=" << d_output_offset
                          << "/" << d_output_burst.size() << std::endl;
            }
        }
        size_t remaining = d_output_burst.size() - d_output_offset;
        size_t to_copy = std::min(remaining, static_cast<size_t>(noutput_items));

        // Copier la portion du burst
        std::memcpy(out, &d_output_burst[d_output_offset], to_copy * sizeof(gr_complex));
        d_output_offset += to_copy;
        produced = static_cast<int>(to_copy);

        // Si le burst est completement sorti, le libérer
        if (d_output_offset >= d_output_burst.size()) {
            if (d_debug_mode) {
                std::cerr << "[BURST_DETECTOR] Burst fully output ("
                          << d_output_burst.size() << " samples)" << std::endl;
            }

            // Tag de fin de burst (à la dernière position)
            add_item_tag(0,
                         nitems_written(0) + produced - 1,
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
    if (d_debug_mode) {
        static int work_call_count = 0;
        work_call_count++;
        if (work_call_count % 1000 == 0) {
            std::cerr << "[BURST_DETECTOR] general_work() called " << work_call_count
                      << " times, ninput=" << ninput << ", noutput=" << noutput_items << std::endl;
        }
    }

    if (d_debug_mode) {
        static int total_samples_processed = 0;
        static int last_log_at = 0;
        total_samples_processed += ninput;
        if (total_samples_processed - last_log_at >= 40000) {  // Log every 1 second
            std::cerr << "[BURST_DETECTOR] Processed " << total_samples_processed
                      << " samples, state=" << d_state << std::endl;
            last_log_at = total_samples_processed;
        }
    }

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
        pmt::pmt_t samples_vec =
            pmt::init_c32vector(d_output_burst.size(), d_output_burst.data());
        burst_msg = pmt::dict_add(burst_msg, pmt::mp("samples"), samples_vec);
        burst_msg = pmt::dict_add(
            burst_msg, pmt::mp("size"), pmt::from_long(d_output_burst.size()));
        burst_msg = pmt::dict_add(
            burst_msg, pmt::mp("timestamp"), pmt::from_uint64(nitems_read(0)));

        message_port_pub(pmt::mp("bursts"), burst_msg);

        if (d_debug_mode) {
            std::cerr << "[BURST_DETECTOR] Message envoye: " << d_output_burst.size()
                      << " samples via port 'bursts'" << std::endl;
        }

        // Tag de debut de burst (pour compatibilité stream)
        add_item_tag(0,
                     nitems_written(0),
                     pmt::intern("burst_start"),
                     pmt::from_long(d_output_burst.size()));

        // Produire autant que possible immédiatement
        size_t to_copy =
            std::min(d_output_burst.size(), static_cast<size_t>(noutput_items));
        std::memcpy(out, &d_output_burst[0], to_copy * sizeof(gr_complex));
        d_output_offset = to_copy;
        produced = static_cast<int>(to_copy);

        if (d_debug_mode) {
            if (to_copy < d_output_burst.size()) {
                std::cerr << "[BURST_DETECTOR] Burst partial output: " << to_copy << " / "
                          << d_output_burst.size() << " samples" << std::endl;
            } else {
                std::cerr << "[BURST_DETECTOR] Burst fully output ("
                          << d_output_burst.size() << " samples)" << std::endl;

                // Tag de fin de burst (à la dernière position)
                add_item_tag(0,
                             nitems_written(0) + produced - 1,
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
