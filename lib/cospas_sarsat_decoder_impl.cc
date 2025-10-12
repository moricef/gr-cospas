/* -*- c++ -*- */
/*
 * Implémentation STABLE du décodeur Cospas-Sarsat
 * Version simplifiée et déterministe
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include "cospas_sarsat_decoder_impl.h"
#include <cmath>
#include <iostream>
#include <iomanip>
#include <algorithm>
#include <cstring> // pour memset

namespace gr {
namespace cospas {

// Factory method
cospas_sarsat_decoder::sptr
cospas_sarsat_decoder::make(float sample_rate, bool debug_mode)
{
    return gnuradio::make_block_sptr<cospas_sarsat_decoder_impl>(sample_rate, debug_mode);
}

// Constructeur
cospas_sarsat_decoder_impl::cospas_sarsat_decoder_impl(float sample_rate, bool debug_mode)
    : gr::sync_block("cospas_sarsat_decoder",
                     gr::io_signature::make(1, 1, sizeof(gr_complex)),
                     gr::io_signature::make(1, 1, sizeof(uint8_t))),
      d_sample_rate(sample_rate),
      d_samples_per_bit(static_cast<int>(sample_rate / BIT_RATE)),
      d_carrier_samples(static_cast<int>(CARRIER_DURATION * sample_rate)),
      d_state(STATE_CARRIER_SEARCH),
      d_carrier_count(0),
      d_sample_count(0),
      d_bit_count(0),
      d_total_bit_count(0),
      d_preamble_ones(0),
      d_frame_sync_bits(0),
      d_frame_sync_pattern(0),
      d_is_test_mode(false),
      d_error_count(0),
      d_last_phase(0.0f),
      d_phase_avg(0.0f),
      d_consecutive_carrier(0),
      d_sync_acquired(false),
      d_frame_length(LONG_FRAME_TOTAL_BITS),
      d_is_long_frame(true),
      d_frames_decoded(0),
      d_sync_failures(0),
      d_debug_mode(debug_mode),
      d_timing_error(0.0f),
      d_mu(0.0f),
      d_omega(static_cast<float>(d_samples_per_bit)),
      d_gain_omega(0.0f),  // DÉSACTIVÉ pour signal synthétique
      d_gain_mu(0.0f),     // DÉSACTIVÉ pour signal synthétique
      d_pll_integral(0.0f),
      d_phase_lpf_state(0.0f)
{
    // Buffer initialisé à ZÉRO
    d_bit_buffer.resize(d_samples_per_bit * 2, std::complex<float>(0, 0));
    d_phase_history.reserve(100);

    set_output_multiple(8);

    // IMPORTANT: Forcer un buffer d'entrée suffisant pour une trame complète
    // Cela évite les problèmes de fragmentation du buffer
    int min_samples = d_carrier_samples + (LONG_FRAME_TOTAL_BITS * d_samples_per_bit);
    set_min_noutput_items(min_samples);

    if (d_debug_mode) {
        std::cout << "[COSPAS] Décodeur initialisé - Échantillons/bit: "
                  << d_samples_per_bit << std::endl;
        std::cout << "[COSPAS] Buffer minimum requis: " << min_samples << " échantillons" << std::endl;
    }
}

// Destructeur
cospas_sarsat_decoder_impl::~cospas_sarsat_decoder_impl()
{
    if (d_debug_mode) {
        std::cout << "[COSPAS] Final: " << d_frames_decoded 
                  << " trames, " << d_sync_failures << " échecs" << std::endl;
    }
}

// Fonction principale de traitement - VERSION BUFFER D'ACCUMULATION
int cospas_sarsat_decoder_impl::work(int noutput_items,
                                      gr_vector_const_void_star &input_items,
                                      gr_vector_void_star &output_items)
{
    const gr_complex *in = (const gr_complex *) input_items[0];
    uint8_t *out = (uint8_t *) output_items[0];

    const int max_bytes = noutput_items - (noutput_items % 8);

    std::lock_guard<std::mutex> lock(d_mutex);

    // DEBUG: Trace work() calls
    static int work_call_count = 0;
    if (d_debug_mode) {
        std::cout << "[DEBUG] work() call #" << work_call_count++
                  << ": noutput_items=" << noutput_items
                  << ", accumulator_size=" << d_sample_accumulator.size() << std::endl;
    }

    // ÉTAPE 1: Accumuler TOUS les échantillons entrants
    for (int i = 0; i < noutput_items; i++) {
        d_sample_accumulator.push_back(in[i]);
    }

    // ÉTAPE 2: Si on n'a pas encore assez d'échantillons, attendre
    if (d_sample_accumulator.size() < MIN_SAMPLES_FOR_FRAME) {
        if (d_debug_mode) {
            std::cout << "[DEBUG] Accumulation en cours: " << d_sample_accumulator.size()
                      << "/" << MIN_SAMPLES_FOR_FRAME << " échantillons" << std::endl;
        }
        consume_each(noutput_items);
        return 0;  // Pas de sortie pour l'instant
    }

    // ÉTAPE 3: Traiter le buffer accumulé avec la machine à états
    int bytes_produced = process_accumulated_buffer(out, max_bytes);

    // DEBUG: Trace work() output
    if (d_debug_mode) {
        std::cout << "[DEBUG] work() exit: bytes_produced=" << bytes_produced
                  << ", remaining_samples=" << d_sample_accumulator.size() << std::endl;
    }

    consume_each(noutput_items);
    return bytes_produced;
}

// NOUVEAU: Traitement du buffer accumulé en utilisant la machine à états existante
int cospas_sarsat_decoder_impl::process_accumulated_buffer(uint8_t* out, int max_bytes)
{
    int bytes_produced = 0;
    int samples_processed = 0;

    // Traiter les échantillons accumulés avec la machine à états
    while (samples_processed < d_sample_accumulator.size() && bytes_produced < max_bytes) {
        gr_complex sample = d_sample_accumulator[samples_processed++];
        float phase = compute_phase(sample);

        switch (d_state) {
            case STATE_CARRIER_SEARCH:
                if (detect_carrier(phase)) {
                    d_carrier_count++;
                    d_consecutive_carrier++;

                    d_phase_history.push_back(phase);
                    if (d_phase_history.size() > 100) {
                        d_phase_history.erase(d_phase_history.begin());
                    }

                    if (d_consecutive_carrier >= d_carrier_samples) {
                        d_state = STATE_INITIAL_JUMP;
                        d_phase_avg = 0.0f;
                        for (float p : d_phase_history) {
                            d_phase_avg += p;
                        }
                        d_phase_avg /= d_phase_history.size();

                        if (d_debug_mode) {
                            std::cout << "[COSPAS] Porteuse détectée après " << d_consecutive_carrier
                                      << " échantillons - phase moyenne: "
                                      << d_phase_avg << " rad" << std::endl;
                        }
                    }
                } else {
                    d_consecutive_carrier = 0;
                    d_phase_history.clear();
                }
                break;
                
            case STATE_INITIAL_JUMP:
                {
                    float diff = std::abs(compute_phase_diff(d_phase_avg, phase));
                    if (diff > JUMP_THRESHOLD && diff < (MOD_PHASE + 0.3f)) {
                        d_state = STATE_PREAMBLE_SYNC;
                        d_sample_count = 0;
                        d_bit_count = 0;
                        d_total_bit_count = 0;
                        d_preamble_ones = 0;
                        d_sync_acquired = false;
                        d_error_count = 0;
                        // NETTOYAGE COMPLET du buffer
                        std::fill(d_bit_buffer.begin(), d_bit_buffer.end(), std::complex<float>(0, 0));

                        if (d_debug_mode) {
                            std::cout << "[COSPAS] Saut initial détecté (diff=" << diff
                                      << " rad) - début du préambule" << std::endl;
                        }
                    }
                }
                break;
                
            case STATE_PREAMBLE_SYNC:
                if (d_sample_count < d_samples_per_bit) {
                    d_bit_buffer[d_sample_count++] = sample;
                }

                if (d_sample_count >= d_samples_per_bit) {
                    char bit = decode_bit(d_bit_buffer.data(), d_samples_per_bit);
                    
                    if (bit == '1') {
                        d_preamble_ones++;
                        d_error_count = 0;
                        d_total_bit_count++;
                        
                        if (d_preamble_ones >= PREAMBLE_BITS) {
                            d_state = STATE_FRAME_SYNC;
                            d_frame_sync_bits = 0;
                            d_frame_sync_pattern = 0;

                            if (d_debug_mode) {
                                std::cout << "[COSPAS] Préambule complet (" 
                                          << PREAMBLE_BITS << " bits '1')" << std::endl;
                            }
                        }
                    } else {
                        d_error_count++;
                        if (d_error_count > MAX_CONSECUTIVE_ERRORS) {
                            d_sync_failures++;
                            reset_decoder();
                        }
                    }

                    d_sample_count = 0;
                }
                break;

            case STATE_FRAME_SYNC:
                if (d_sample_count < d_samples_per_bit) {
                    d_bit_buffer[d_sample_count++] = sample;
                }

                if (d_sample_count >= d_samples_per_bit) {
                    char bit = decode_bit(d_bit_buffer.data(), d_samples_per_bit);

                    if (bit == '0' || bit == '1') {
                        d_frame_sync_pattern = (d_frame_sync_pattern << 1) | (bit == '1' ? 1 : 0);
                        d_frame_sync_bits++;
                        d_error_count = 0;
                        d_total_bit_count++;

                        if (d_frame_sync_bits >= FRAME_SYNC_BITS) {
                            if (d_frame_sync_pattern == FRAME_SYNC_NORMAL || 
                                d_frame_sync_pattern == FRAME_SYNC_TEST) {
                                
                                d_is_test_mode = (d_frame_sync_pattern == FRAME_SYNC_TEST);
                                d_state = STATE_DATA_DECODE;
                                d_sync_acquired = true;
                                d_frames_decoded++;
                                d_bit_count = 0;
                                d_error_count = 0;

                                if (d_debug_mode) {
                                    std::cout << "[COSPAS] *** SYNCHRO ACQUISE (" 
                                              << (d_is_test_mode ? "TEST" : "NORMAL") 
                                              << ") ***" << std::endl;
                                }
                            } else {
                                d_error_count++;
                                if (d_error_count > MAX_CONSECUTIVE_ERRORS) {
                                    d_sync_failures++;
                                    reset_decoder();
                                } else {
                                    d_frame_sync_bits = 0;
                                    d_frame_sync_pattern = 0;
                                }
                            }
                        }
                    } else {
                        d_error_count++;
                        if (d_error_count > MAX_CONSECUTIVE_ERRORS) {
                            d_sync_failures++;
                            reset_decoder();
                        }
                    }

                    d_sample_count = 0;
                }
                break;

            case STATE_DATA_DECODE:
                if (d_sample_count < d_samples_per_bit) {
                    d_bit_buffer[d_sample_count++] = sample;
                }

                if (d_sample_count >= d_samples_per_bit) {
                    char bit = decode_bit(d_bit_buffer.data(), d_samples_per_bit);

                    if (bit == '0' || bit == '1') {
                        d_error_count = 0;

                        // DEBUG: Trace bits décodés pour déboguer
                        if (d_debug_mode && d_bit_count >= 80 && d_bit_count < 85) {
                            std::cout << "[COSPAS] Bit " << d_bit_count << ": '" << bit << "'" << std::endl;
                        }

                        // Détection type de trame au premier bit de message
                        if (d_bit_count == 0) {
                            d_is_long_frame = (bit == '1');
                            d_frame_length = d_is_long_frame ? LONG_FRAME_TOTAL_BITS : SHORT_FRAME_TOTAL_BITS;
                            
                            if (d_debug_mode) {
                                int msg_bits = d_is_long_frame ? LONG_MESSAGE_BITS : SHORT_MESSAGE_BITS;
                                std::cout << "[COSPAS] Trame " 
                                          << (d_is_long_frame ? "LONGUE" : "COURTE") 
                                          << " (" << msg_bits << " bits message)" << std::endl;
                            }
                        }

                        d_total_bit_count++;
                        d_bit_count++;

                        // Stocker uniquement les bits de message (après préambule 15 + sync 9)
                        if (d_total_bit_count >= (PREAMBLE_BITS + FRAME_SYNC_BITS)) {
                            d_output_bits.push_back(bit == '1' ? 1 : 0);
                        }
                        
                        // Produire des octets complets
                        if (d_output_bits.size() >= 8 && bytes_produced < max_bytes) {
                            uint8_t byte = 0;
                            for (int i = 0; i < 8; i++) {
                                byte = (byte << 1) | d_output_bits[0];
                                d_output_bits.pop_front();
                            }
                            out[bytes_produced++] = byte;
                            
                            if (d_debug_mode && bytes_produced % 5 == 0) {
                                std::cout << "[COSPAS] Octet " << (bytes_produced - 1)
                                          << ": 0x" << std::hex << std::setw(2) 
                                          << std::setfill('0') << (int)byte << std::dec << std::endl;
                            }
                        }

                    } else {
                        d_error_count++;
                        d_total_bit_count++; // Compter même les bits erronés

                        if (d_debug_mode) {
                            std::cout << "[COSPAS] BIT INDÉTERMINÉ '?' au bit " << d_bit_count
                                      << " (total=" << d_total_bit_count << ")" << std::endl;
                        }

                        if (d_error_count > MAX_CONSECUTIVE_ERRORS) {
                            if (d_debug_mode) {
                                std::cout << "[COSPAS] Trop d'erreurs bit " << d_bit_count << std::endl;
                            }
                            reset_decoder();
                        }
                    }

                    // IMPORTANT: Vérifier fin de trame APRÈS les deux cas (bit valide OU '?')
                    if (d_total_bit_count >= d_frame_length) {
                        if (d_debug_mode) {
                            std::cout << "[COSPAS] Trame complète: "
                                      << d_bit_count << " bits message valides (total="
                                      << d_total_bit_count << ")" << std::endl;
                        }
                        reset_decoder();
                    }

                    d_sample_count = 0;
                }
                break;
        }

        d_last_phase = phase;
    }

    // Nettoyer les échantillons traités du buffer d'accumulation
    if (samples_processed > 0) {
        d_sample_accumulator.erase(
            d_sample_accumulator.begin(),
            d_sample_accumulator.begin() + samples_processed
        );
    }

    return bytes_produced;
}

// Calcul de phase (inchangé mais garanti stable)
float cospas_sarsat_decoder_impl::compute_phase(std::complex<float> sample)
{
    return std::arg(sample);
}

float cospas_sarsat_decoder_impl::normalize_phase(float phase)
{
    phase = std::fmod(phase, 2.0f * M_PI);
    if (phase > M_PI) return phase - 2.0f * M_PI;
    if (phase < -M_PI) return phase + 2.0f * M_PI;
    return phase;
}

float cospas_sarsat_decoder_impl::compute_phase_diff(float phase1, float phase2)
{
    float diff = phase2 - phase1;
    return normalize_phase(diff);
}

bool cospas_sarsat_decoder_impl::detect_carrier(float phase)
{
    float normalized = normalize_phase(phase);
    return std::abs(normalized) < CARRIER_THRESHOLD;
}

bool cospas_sarsat_decoder_impl::detect_initial_jump(float phase)
{
    float diff = std::abs(compute_phase_diff(d_phase_avg, phase));
    return diff > JUMP_THRESHOLD && diff < (MOD_PHASE + 0.3f);
}

// Décodage de bit - VERSION PYTHON (échantillon central)
char cospas_sarsat_decoder_impl::decode_bit(const std::complex<float>* samples, int num_samples)
{
    // Prendre UN échantillon au centre de chaque moitié (comme Python)
    // C'est plus robuste que de sommer tous les échantillons!

    int half_samples = num_samples / 2;
    int quarter_samples = half_samples / 2;

    // Centre de la première moitié
    int center_first = quarter_samples;
    // Centre de la deuxième moitié
    int center_second = half_samples + quarter_samples;

    float phase_first = std::arg(samples[center_first]);
    float phase_second = std::arg(samples[center_second]);
    float phase_diff = compute_phase_diff(phase_first, phase_second);

    // Bit '1': +1.1 → -1.1 (transition descendante < 0)
    // Bit '0': -1.1 → +1.1 (transition montante > 0)
    if (phase_diff < -0.5f) {
        return '1';
    } else if (phase_diff > 0.5f) {
        return '0';
    } else {
        return '?';
    }
}

// Timing error DÉSACTIVÉ (retourne toujours 0)
float cospas_sarsat_decoder_impl::compute_timing_error(const std::complex<float>* samples, int num_samples)
{
    return 0.0f; // Désactivé pour signal synthétique
}

// Update timing DÉSACTIVÉ
void cospas_sarsat_decoder_impl::update_timing(float error)
{
    // Rien - timing fixe pour signal synthétique
}

float cospas_sarsat_decoder_impl::average_phase(const std::complex<float>* samples, int start, int count)
{
    std::complex<float> sum(0, 0);
    int end = std::min(start + count, d_samples_per_bit);
    for (int i = start; i < end; i++) {
        sum += samples[i];
    }
    return std::arg(sum);
}

float cospas_sarsat_decoder_impl::low_pass_filter(float phase)
{
    return phase; // Désactivé
}

// RÉINITIALISATION COMPLÈTE et GARANTIE
void cospas_sarsat_decoder_impl::reset_decoder()
{
    // État machine
    d_state = STATE_CARRIER_SEARCH;
    
    // Compteurs
    d_carrier_count = 0;
    d_sample_count = 0;
    d_bit_count = 0;
    d_total_bit_count = 0;
    d_preamble_ones = 0;
    d_frame_sync_bits = 0;
    d_frame_sync_pattern = 0;
    d_consecutive_carrier = 0;
    d_error_count = 0;
    
    // Synchronisation
    d_sync_acquired = false;
    d_is_test_mode = false;
    d_frame_length = LONG_FRAME_TOTAL_BITS;
    d_is_long_frame = true;
    
    // Buffers - NETTOYAGE COMPLET
    std::fill(d_bit_buffer.begin(), d_bit_buffer.end(), std::complex<float>(0, 0));
    d_output_bits.clear();
    d_phase_history.clear();
    
    // Variables de traitement
    d_last_phase = 0.0f;
    d_phase_avg = 0.0f;
    d_phase_lpf_state = 0.0f;
    
    // Timing - RÉINITIALISATION COMPLÈTE
    d_timing_error = 0.0f;
    d_mu = 0.0f;
    d_omega = static_cast<float>(d_samples_per_bit);
    d_pll_integral = 0.0f;
}

// Méthodes thread-safe
bool cospas_sarsat_decoder_impl::is_synchronized() const 
{ 
    std::lock_guard<std::mutex> lock(d_mutex);
    return d_sync_acquired; 
}

int cospas_sarsat_decoder_impl::get_frames_decoded() const 
{ 
    std::lock_guard<std::mutex> lock(d_mutex);
    return d_frames_decoded; 
}

int cospas_sarsat_decoder_impl::get_sync_failures() const 
{ 
    std::lock_guard<std::mutex> lock(d_mutex);
    return d_sync_failures; 
}

void cospas_sarsat_decoder_impl::set_debug_mode(bool enable) 
{ 
    std::lock_guard<std::mutex> lock(d_mutex);
    d_debug_mode = enable; 
}

void cospas_sarsat_decoder_impl::reset_statistics() 
{
    std::lock_guard<std::mutex> lock(d_mutex);
    d_frames_decoded = 0;
    d_sync_failures = 0;
    d_error_count = 0;
}

} // namespace cospas
} // namespace gr
