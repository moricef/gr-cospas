/* -*- c++ -*- */
/*
 * Implémentation STABLE du décodeur Cospas-Sarsat
 * Version simplifiée et déterministe
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include <pmt/pmt.h>
#include "cospas_sarsat_demodulator_impl.h"
#include <cmath>
#include <iostream>
#include <iomanip>
#include <algorithm>
#include <cstring> // pour memset
#include <bitset>   // pour afficher les patterns binaires

// Décodeur COSPAS-SARSAT
extern "C" {
#include "dec406.h"
}

namespace gr {
namespace cospas {

// Factory method
cospas_sarsat_demodulator::sptr
cospas_sarsat_demodulator::make(float sample_rate, bool debug_mode)
{
    return gnuradio::make_block_sptr<cospas_sarsat_demodulator_impl>(sample_rate, debug_mode);
}

// Constructeur
cospas_sarsat_demodulator_impl::cospas_sarsat_demodulator_impl(float sample_rate, bool debug_mode)
    : gr::sync_block("cospas_sarsat_demodulator",
                     //gr::io_signature::make(1, 1, sizeof(gr_complex)),
                     //gr::io_signature::make(1, 1, sizeof(uint8_t))),
                    gr::io_signature::make(0, 0, 0),  // AUCUNE entree stream
                    gr::io_signature::make(0, 0, 0)), // AUCUNE sortie stream
      d_sample_rate(sample_rate),
      d_samples_per_bit(static_cast<int>(sample_rate / BIT_RATE)),
      d_carrier_samples(static_cast<int>(CARRIER_DURATION * sample_rate)),
      d_carrier_samples_min(static_cast<int>(0.025f * sample_rate)),  // 25ms = 1000 samples
      d_state(STATE_CARRIER_SEARCH),
      d_carrier_count(0),
      d_carrier_start_idx(0),
      d_sample_count(0),
      d_bits_demodulated(0),
      d_total_bit_count(0),
      d_preamble_ones(0),
      d_error_count(0),
      d_sync_sample_count(0),
      d_measured_samples_per_bit(static_cast<float>(d_samples_per_bit)),
      d_expected_burst_size(0),  // 0 = pas de burst_start tag, utiliser MIN_SAMPLES_FOR_FRAME
      d_waiting_for_burst(false), // false = mode standalone (sans tags), true = attendre burst_start
      d_last_phase(0.0f),
      d_phase_avg(0.0f),
      d_consecutive_carrier(0),
      d_timing_error(0.0f),
      d_mu(0.0f),
      d_omega(static_cast<float>(d_samples_per_bit)),
      d_gain_omega(0.0f),
      d_gain_mu(0.0f),
      d_pll_integral(0.0f),
      d_pll_phase(0.0f),
      d_freq_offset(0.0f),
      d_phase_correction(0.0f),
      d_freq_lock(false),
      d_freq_correction_frozen(false),
      d_carrier_phase_ref(0.0f),
      d_bursts_detected(0),
      d_debug_mode(debug_mode),
      d_phase_lpf_state(0.0f)
{
        // Enregistrer le port de message pour recevoir les bursts
    message_port_register_in(pmt::mp("bursts"));
    set_msg_handler(pmt::mp("bursts"), [this](pmt::pmt_t msg) { this->handle_burst_message(msg); });
    
    d_bit_buffer.resize(d_samples_per_bit, std::complex<float>(0, 0));
    d_phase_history.reserve(200);
    d_transition_positions.reserve(30);  // 15 bits = jusqu'à 30 transitions (mi-bit + fin-bit)

    set_output_multiple(1);

    int min_samples = d_carrier_samples + (TOTAL_BITS * d_samples_per_bit);
    set_min_noutput_items(min_samples);

    if (d_debug_mode) {
        std::cout << "[BPSK_DEMOD] Demodulateur initialise" << std::endl;
        std::cout << "[BPSK_DEMOD] Echantillons/bit: " << d_samples_per_bit << std::endl;
        std::cout << "[BPSK_DEMOD] Buffer minimum: " << min_samples << " echantillons" << std::endl;
    }
}

// Destructeur
cospas_sarsat_demodulator_impl::~cospas_sarsat_demodulator_impl()
{
    if (d_debug_mode) {
        std::cout << "[BPSK_DEMOD] Final: " << d_bursts_detected << " bursts detectes" << std::endl;
    }
}

// Fonction principale de traitement - VERSION BUFFER D'ACCUMULATION
int cospas_sarsat_demodulator_impl::work(int noutput_items,
                                      gr_vector_const_void_star &input_items,
                                      gr_vector_void_star &output_items)
{
    const gr_complex *in = (const gr_complex *) input_items[0];
    uint8_t *out = (uint8_t *) output_items[0];

    const int max_bytes = noutput_items - (noutput_items % 8);

    std::lock_guard<std::mutex> lock(d_mutex);

    // MODE AUTONOME: Ignorer les tags burst_start/burst_end
    // Le demodulateur détecte les bursts via la porteuse (STATE_CARRIER_SEARCH)
    // Cela évite les problèmes de timing avec le Router

    // DEBUG: Trace work() calls
    static int work_call_count = 0;
    if (d_debug_mode) {
        std::cout << "[DEBUG] work() call #" << work_call_count++
                  << ": noutput_items=" << noutput_items
                  << ", accumulator_size=" << d_sample_accumulator.size() << std::endl;
    }

    // ÉTAPE 1: Accumuler TOUS les echantillons entrants
    for (int i = 0; i < noutput_items; i++) {
        d_sample_accumulator.push_back(in[i]);
    }

    // ÉTAPE 2: Vérifier si on a assez d'echantillons pour traiter
    size_t min_samples = MIN_SAMPLES_FOR_FRAME;

    if (d_sample_accumulator.size() < min_samples) {
        if (d_debug_mode) {
            std::cout << "[DEBUG] Accumulation en cours: " << d_sample_accumulator.size()
                      << "/" << min_samples << " echantillons" << std::endl;
        }
        consume_each(noutput_items);
        return 0;  // Pas de sortie pour l'instant
    }

    // ÉTAPE 3: Traiter le buffer accumule avec la machine a états
    int bytes_produced = process_accumulated_buffer(out, max_bytes);

    // DEBUG: Trace work() output
    if (d_debug_mode) {
        std::cout << "[DEBUG] work() exit: bytes_produced=" << bytes_produced
                  << ", remaining_samples=" << d_sample_accumulator.size() << std::endl;
    }

    consume_each(noutput_items);
    return bytes_produced;
}

// NOUVEAU: Traitement du buffer accumule en utilisant la machine a états existante
int cospas_sarsat_demodulator_impl::process_accumulated_buffer(uint8_t* out, int max_bytes)
{
    int bytes_produced = 0;
    int samples_processed = 0;

    int strong_samples_in_loop = 0;  // Compteur pour debug

    // AGC: Normalisation automatique basée sur le niveau du signal
    // Utiliser le 95ème percentile au lieu du max pour robustesse a la saturation
    std::vector<float> amplitudes;
    amplitudes.reserve(d_sample_accumulator.size());
    int saturated_count = 0;

    for (const auto& s : d_sample_accumulator) {
        float amp = std::abs(s);
        if (amp > 1.0f) saturated_count++;
        amplitudes.push_back(amp);
    }

    std::sort(amplitudes.begin(), amplitudes.end());
    size_t p95_idx = static_cast<size_t>(amplitudes.size() * 0.95f);
    float signal_p95 = (p95_idx < amplitudes.size()) ? amplitudes[p95_idx] : amplitudes.back();

    // AGC DÉSACTIVÉ en mode autonome - chaque burst a son propre niveau
    // Le Router envoie les bursts avec leurs amplitudes originales
    // L'AGC global sur tout le buffer mélange les niveaux de différents bursts
    float agc_gain = 1.0f;  // Pas de correction

    /*
    // AGC conditionnel : uniquement si signal hors de la plage optimale [0.06, 0.40]
    const float MIN_OPTIMAL = 0.06f;  // En dessous : trop faible
    const float MAX_OPTIMAL = 0.40f;  // Au dessus : trop fort
    const float TARGET_LEVEL = 0.20f; // Niveau cible

    if (signal_p95 < MIN_OPTIMAL && signal_p95 > 0.01f) {
        // Signal trop faible : amplifier
        agc_gain = TARGET_LEVEL / signal_p95;
    } else if (signal_p95 > MAX_OPTIMAL) {
        // Signal trop fort : atténuer
        agc_gain = TARGET_LEVEL / signal_p95;
    }

    // Appliquer AGC uniquement si nécessaire
    if (agc_gain != 1.0f) {
        for (auto& s : d_sample_accumulator) {
            s *= agc_gain;
        }
    }
    */

    if (d_debug_mode) {
        // Compter combien d'echantillons sont > 0.05 apres AGC
        int strong_samples = 0;
        for (const auto& s : d_sample_accumulator) {
            if (std::abs(s) > 0.05f) strong_samples++;
        }
        std::cout << "[DEBUG] process_accumulated_buffer(): " << d_sample_accumulator.size()
                  << " echantillons, " << strong_samples << " > 0.05"
                  << " | AGC: p95=" << signal_p95 << ", gain=" << agc_gain
                  << ", saturated=" << saturated_count << std::endl;
    }

    // Traiter les echantillons accumules avec la machine a états
    while (samples_processed < d_sample_accumulator.size() && bytes_produced < max_bytes && 
       d_total_bit_count < TOTAL_BITS) {
        gr_complex sample = d_sample_accumulator[samples_processed++];

        // Appliquer la correction de frequence si active
        sample = apply_freq_correction(sample);

        float phase = compute_phase(sample);

        switch (d_state) {
            case STATE_CARRIER_SEARCH:
                // Debug amplitude et phase apres correction
                if (d_debug_mode && samples_processed == 5000) {
                    std::cout << "[DEBUG] Sample #5000: |sample|=" << std::abs(sample); 
                }
                // Vérifier d'abord si on a un signal fort (pour éviter d'estimer sur le bruit)
                if (std::abs(sample) > 0.05f) {  // Seuil d'amplitude
                    strong_samples_in_loop++;

                    // Accumuler la phase
                    d_phase_history.push_back(phase);
                    size_t max_history = d_freq_lock ? 200 : 5000;
                    if (d_phase_history.size() > max_history) {
                        d_phase_history.erase(d_phase_history.begin());
                    }

                    // ÉTAPE 1: Détecter la porteuse AVANT d'estimer la frequence
                    // Porteuse = différences de phase constantes (frequence constante)
                    // BPSK = différences de phase variables (sauts ±1.1 rad)
                    if (!d_freq_lock && d_phase_history.size() >= 200) {
                        // Calculer la variance des différences de phase
                        float diff_sum = 0, diff_sq_sum = 0;
                        int count = 199;  // 200 echantillons = 199 différences
                        for (int i = d_phase_history.size() - 200; i < (int)d_phase_history.size() - 1; i++) {
                            float diff = d_phase_history[i+1] - d_phase_history[i];
                            // Normaliser entre -π et +π
                            if (diff > M_PI) diff -= 2.0f * M_PI;
                            else if (diff < -M_PI) diff += 2.0f * M_PI;
                            diff_sum += diff;
                            diff_sq_sum += diff * diff;
                        }
                        float diff_mean = diff_sum / count;
                        float diff_var = diff_sq_sum / count - diff_mean * diff_mean;
                        if (diff_var < 0) diff_var = 0;
                        float diff_std = std::sqrt(diff_var);

                        // Porteuse : diff_std < 0.1 rad (frequence constante)
                        // BPSK : diff_std > 0.3 rad (sauts de phase)
                        if (diff_std > 0.1f) {
                            d_phase_history.clear();
                            if (d_debug_mode && samples_processed % 10000 == 0) {
                                std::cout << "[DEBUG] Phase diff variance too high (" << diff_std
                                          << " rad) - not carrier, resetting" << std::endl;
                            }
                        }
                    }

                    // ÉTAPE 2: Une fois 5000 echantillons de porteuse accumules, estimer la frequence
                    if (!d_freq_lock && d_phase_history.size() >= 5000) {
                        if (d_debug_mode) {
                            std::cout << "[DEBUG] 5000 carrier samples accumulated, estimating freq" << std::endl;
                        }
                        estimate_freq_offset();
                    }

                    // APRES estimation, tester la porteuse
                    // IMPORTANT: Ne pas tester la porteuse AVANT d'avoir freq_lock
                    // Sinon la phase tourne et on ne détecte jamais de carrier stable
                    if (d_freq_lock && detect_carrier(phase)) {
                        d_carrier_count++;
                        d_consecutive_carrier++;

                        // Utiliser un seuil plus bas avec correction de frequence (convergence progressive)
                        int carrier_threshold = d_freq_lock ? d_carrier_samples_min : d_carrier_samples;

                        if (d_debug_mode && d_consecutive_carrier % 1000 == 0) {
                            std::cout << "[DEBUG] Carrier detected: freq_lock=" << d_freq_lock
                                      << ", consecutive=" << d_consecutive_carrier
                                      <<", threshold=" << (d_freq_lock ? d_carrier_samples_min : d_carrier_samples)
                                      <<", << detect_carrier_result=" << detect_carrier(phase) << std::endl;
                        }

                        if (d_consecutive_carrier >= carrier_threshold) {
                            // Porteuse detectee : mémoriser la position de debut et chercher le saut de phase
                            d_state = STATE_CARRIER_TRACKING;
                            d_carrier_start_idx = samples_processed - d_consecutive_carrier;

                            // Calculer la phase moyenne sur les 50 DERNIERS echantillons
                            d_phase_avg = 0.0f;
                            int count = std::min(50, (int)d_phase_history.size());
                            for (int i = d_phase_history.size() - count; i < d_phase_history.size(); i++) {
                                d_phase_avg += d_phase_history[i];
                            }
                            d_phase_avg /= count;

                            if (d_debug_mode) {
                                std::cout << "[COSPAS] Porteuse detectee apres " << d_consecutive_carrier
                                          << " echantillons - phase moyenne: "
                                          << d_phase_avg << " rad" << std::endl;
                                std::cout << "[COSPAS] Position de debut: " << d_carrier_start_idx << std::endl;
                            }
                        }
                    } else {
                        if (d_debug_mode && d_consecutive_carrier > 3000) {
                            // Calculer la phase moyenne récente pour debug
                            float phase_sum = 0;
                            int count = std::min(50, (int)d_phase_history.size());
                            for (int i = d_phase_history.size() - count; i < d_phase_history.size(); i++) {
                                phase_sum += d_phase_history[i];
                            }
                            float phase_mean = phase_sum / count;
                            float diff = compute_phase_diff(phase_mean, phase);
                            float abs_diff = std::abs(diff);

                            std::cout << "[DEBUG] Carrier lost at sample " << samples_processed
                                      << ", consecutive was " << d_consecutive_carrier
                                      << ", phase=" << phase << " rad, phase_mean=" << phase_mean
                                      << " rad, diff=" << abs_diff << " rad (threshold=0.5)" << std::endl;
                        }
                        d_consecutive_carrier = 0;
                        // NE PAS vider l'historique une fois qu'on a verrouillé
                    }
                }
                break;
                
            case STATE_CARRIER_TRACKING:
                {
                    // Continuer a accumuler la phase pour tracking
                    if (std::abs(sample) > 0.05f) {
                        d_phase_history.push_back(phase);
                        if (d_phase_history.size() > 200) {
                            d_phase_history.erase(d_phase_history.begin());
                        }
                    }

                    // Correction adaptative DÉSACTIVÉE
                    // L'estimation sur 5000 echantillons (125ms) de porteuse est suffisante
                    // Les corrections adaptatives introduisent des erreurs car elles modifient
                    // l'offset basé sur des données bruitées pendant le tracking
                    /*
                    int correction_period = d_freq_correction_frozen ? 500 : 984;
                    if (d_freq_lock && samples_processed % correction_period == 0 && d_phase_history.size() >= 200) {
                        // Régression linéaire sur les 200 derniers echantillons
                        float sum_x = 0.0f, sum_y = 0.0f, sum_xy = 0.0f, sum_x2 = 0.0f;
                        int n = 200;
                        for (int i = 0; i < n; i++) {
                            float x = (float)i;
                            float y = d_phase_history[i];
                            sum_x += x;
                            sum_y += y;
                            sum_xy += x * y;
                            sum_x2 += x * x;
                        }

                        // Pente = dérive en rad/échantillon
                        float slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x);

                        // Convertir en Hz : dérive_hz = (slope * sample_rate) / (2 * PI)
                        float drift_hz = (slope * d_sample_rate) / (2.0f * M_PI);

                        // Ajuster la correction de frequence
                        d_freq_offset += drift_hz;

                        if (d_debug_mode) {
                            std::cout << "[COSPAS] Correction adaptative: drift=" << drift_hz
                                      << " Hz, offset total=" << d_freq_offset << " Hz" << std::endl;
                        }
                    }
                    */

                    // Détecter un saut de phase BRUTAL (pas une dérive progressive)
                    // Comparer avec la phase il y a 10 echantillons pour différencier saut vs dérive
                    float phase_jump = 0.0f;
                    if (d_phase_history.size() >= 10) {
                        float phase_10_ago = d_phase_history[d_phase_history.size() - 10];
                        phase_jump = phase - phase_10_ago;
                        // Normaliser le saut entre -π et +π
                        while (phase_jump > M_PI) phase_jump -= 2.0f * M_PI;
                        while (phase_jump < -M_PI) phase_jump += 2.0f * M_PI;
                    }

                    if (d_debug_mode && samples_processed % 500 == 0) {
                        int carrier_samples_so_far = samples_processed - d_carrier_start_idx;
                        std::cout << "[DEBUG] STATE_CARRIER_TRACKING: carrier_samples=" << carrier_samples_so_far
                                  << ", phase=" << phase
                                  << ", phase_jump(10samp)=" << phase_jump << " rad" << std::endl;
                    }

                    // Chercher un saut de phase BRUTAL > 1.0 rad en 10 echantillons (transition 0 -> +1.1 rad)
                    if (d_phase_history.size() >= 10 && phase_jump > 1.0f) {
                        // Geler la correction de frequence : fin de la porteuse, debut BPSK
                        if (!d_freq_correction_frozen) {
                            d_freq_correction_frozen = true;
                            if (d_debug_mode) {
                                std::cout << "[COSPAS] Saut de phase detecte: offset=" << d_freq_offset
                                          << " Hz. Correction gelee: " << (-d_freq_offset) << " Hz" << std::endl;
                            }
                        }

                        if (d_debug_mode) {
                            std::cout << "[COSPAS] Transition vers demodulation BPSK" << std::endl;
                        }

                        // Passer directement a la demodulation sans REWIND
                        d_state = STATE_BIT_SYNC;
                        d_sample_count = 0;
                        d_total_bit_count = 0;
                        d_preamble_ones = 0;
                        d_bits_demodulated = 0;
                        d_error_count = 0;
                        std::fill(d_bit_buffer.begin(), d_bit_buffer.end(), std::complex<float>(0, 0));

                        // Initialiser la PLL avec la phase actuelle (apres le saut BPSK)
                        d_pll_phase = phase;
                        d_pll_integral = 0.0f;
                    }
                }
                break;
                
            case STATE_BIT_SYNC:
                if (d_sample_count < d_samples_per_bit) {
                    // Stocker l'échantillon sans correction de phase
                    // La correction de frequence est deja appliquée en amont
                    d_bit_buffer[d_sample_count++] = sample;

                    // Detection des transitions pour récupération de timing
                    // Manchester '1': transition phase +1.1 -> -1.1 au milieu du bit
                    d_sync_sample_count++;
                    if (d_sync_sample_count > 1) {
                        // Détecter transition de phase significative (>1.5 rad)
                        float phase_diff = compute_phase_diff(d_last_phase, phase);
                        if (std::abs(phase_diff) > 1.5f) {
                            d_transition_positions.push_back(d_sync_sample_count);
                        }
                    }
                }

                if (d_sample_count >= d_samples_per_bit) {
                    char bit = decode_bit(d_bit_buffer.data(), d_samples_per_bit);
                    d_total_bit_count++;

                    // Produire le bit en sortie
                    if (bit == '0' || bit == '1') {
                        uint8_t bit_value = (bit == '1') ? 1 : 0;
                        out[bytes_produced++] = bit_value;
                        d_bits_demodulated++;

                        if (bit == '1') {
                            d_preamble_ones++;
                        }
                    }

                    if (d_total_bit_count >= BIT_SYNC_BITS) {
                        // Calculer le timing réel a partir des transitions detectees
                        if (d_transition_positions.size() >= 4) {
                            // Calculer intervalles entre transitions consécutives
                            float interval_sum = 0;
                            int interval_count = 0;
                            for (size_t i = 1; i < d_transition_positions.size(); i++) {
                                int interval = d_transition_positions[i] - d_transition_positions[i-1];
                                // Intervalle attendu: 50 samples (demi-bit)
                                if (interval > 30 && interval < 70) {
                                    interval_sum += interval;
                                    interval_count++;
                                }
                            }
                            if (interval_count > 0) {
                                float avg_half_bit = interval_sum / interval_count;
                                d_measured_samples_per_bit = avg_half_bit * 2.0f;

                                if (d_debug_mode) {
                                    std::cout << "[COSPAS] Timing recovery: " << d_transition_positions.size()
                                              << " transitions, interval moyen=" << avg_half_bit
                                              << " samples, samples/bit=" << d_measured_samples_per_bit
                                              << " (nominal=" << d_samples_per_bit << ")" << std::endl;
                                }
                            }
                        }

                        d_state = STATE_FRAME_SYNC;

                        if (d_debug_mode) {
                            std::cout << "[COSPAS] Bit sync complet (" << d_preamble_ones
                                      << " '1' sur " << BIT_SYNC_BITS << " bits)" << std::endl;
                        }
                    }

                    d_sample_count = 0;
                }
                break;

            case STATE_FRAME_SYNC:
            {
                // Utiliser le timing mesure au lieu du timing nominal
                int samples_per_bit_actual = static_cast<int>(d_measured_samples_per_bit + 0.5f);

                if (d_sample_count < samples_per_bit_actual) {
                    d_bit_buffer[d_sample_count++] = sample;
                }

                if (d_sample_count >= samples_per_bit_actual) {
                    char bit = decode_bit(d_bit_buffer.data(), samples_per_bit_actual);
                    d_total_bit_count++;

                    // Tracking adaptatif des transitions Manchester
                    int detected_position = detect_transition_position(d_bit_buffer.data(), samples_per_bit_actual);
                    int expected_position = samples_per_bit_actual / 2;
                    d_timing_error = static_cast<float>(detected_position - expected_position);

                    // Tracking adaptatif avec d_mu initialisé à -20
                    // Gain modéré pour affinage continu
                    float gain = 0.2f;  // Gain pour phase de sync
                    d_mu += d_timing_error * gain;

                    // Borner d_mu pour eviter derive excessive
                    if (d_mu > 25.0f) d_mu = 25.0f;
                    if (d_mu < -25.0f) d_mu = -25.0f;

                    // Produire le bit en sortie
                    if (bit == '0' || bit == '1') {
                        uint8_t bit_value = (bit == '1') ? 1 : 0;
                        out[bytes_produced++] = bit_value;
                        d_bits_demodulated++;
                    }

                    if (d_total_bit_count >= BIT_SYNC_BITS + FRAME_SYNC_BITS) {
                        d_state = STATE_MESSAGE;
                        // Note: d_bursts_detected incrémenté APRES trame complète (ligne 526+)

                        if (d_debug_mode) {
                            std::cout << "[DEBUG] Transition to STATE_MESSAGE at bit " << d_total_bit_count 
                                      << " (SYNC: " << BIT_SYNC_BITS << " + FRAME: " << FRAME_SYNC_BITS << ")" 
                                      << std::endl;
                                      
                            std::cout << "[DEBUG] Expected message bits: " << MESSAGE_BITS 
                                      << " (from bit #" << (d_total_bit_count + 1) 
                                      << " to #" << (d_total_bit_count + MESSAGE_BITS) << ")" << std::endl;
                        }
                    }

                    d_sample_count = 0;
                }
            }
                break;

            case STATE_MESSAGE:
            {
                // Utiliser le timing mesure pour les bits de message aussi
                int samples_per_bit_msg = static_cast<int>(d_measured_samples_per_bit + 0.5f);

                if (d_sample_count < samples_per_bit_msg) {
                    d_bit_buffer[d_sample_count++] = sample;
                }

                if (d_sample_count >= samples_per_bit_msg) {
                    char bit = decode_bit(d_bit_buffer.data(), samples_per_bit_msg);
                    d_total_bit_count++;

                    // Tracking adaptatif des transitions Manchester (continue sur message)
                    int detected_position = detect_transition_position(d_bit_buffer.data(), samples_per_bit_msg);
                    int expected_position = samples_per_bit_msg / 2;
                    d_timing_error = static_cast<float>(detected_position - expected_position);

                    // Gain leger pour phase de message (tracking fin)
                    float gain = 0.1f;  // Reduit a 0.1 pour stabilite en phase message
                    d_mu += d_timing_error * gain;

                    // Borner d_mu pour eviter derive excessive
                    if (d_mu > 25.0f) d_mu = 25.0f;
                    if (d_mu < -25.0f) d_mu = -25.0f;

                    if (d_total_bit_count == 143 || d_total_bit_count == 144) {
                        std::cout << "[DEBUG BIT " << d_total_bit_count << "] "
                                  << "bit='" << bit << "'"
                                  << ", detected_pos=" << detected_position
                                  << ", expected_pos=" << expected_position
                                  << ", timing_error=" << d_timing_error
                                  << ", d_mu=" << d_mu << std::endl;
                    }

                     if (d_debug_mode) {
                         int message_bit_index = d_total_bit_count - BIT_SYNC_BITS - FRAME_SYNC_BITS;
                         std::cout << "[DEBUG] Message Bit #" << message_bit_index
                                   <<"/" << MESSAGE_BITS
                                   << " (global: " << d_total_bit_count << "/" << TOTAL_BITS << ")"
                                   << "=" << bit << std::endl;
                    }

                    if (bit == '0' || bit == '1') {
                        uint8_t bit_value = (bit == '1') ? 1 : 0;
                        out[bytes_produced++] = bit_value;
                        d_bits_demodulated++;
                    }
                    
                    d_sample_count = 0;
                    
                    if (d_total_bit_count >= TOTAL_BITS) {
                        d_bursts_detected++;
            
                        if (d_debug_mode) {
                            std::cout << "[SUCCESS] Trame COMPLETE - " << d_bits_demodulated 
                                      << " bits valides sur " << TOTAL_BITS << " bits attendus" 
                                      << ", burst_count=" << d_bursts_detected << std::endl;
                        }

                        // Afficher le HEX de la trame démodulée
                        // Les bits sont dans out[bytes_produced - d_bits_demodulated ... bytes_produced - 1]
                        if (d_bits_demodulated >= 112) {  // Au moins trame courte
                            std::cout << "[REF FR HEX]: FFFE2F8E39048D158AC01E3AA482856824CE"<< std::endl;
                            std::cout << "[COSPAS] HEX: ";
                            int start_bit = bytes_produced - d_bits_demodulated;
                            // Convertir bits en hex (4 bits = 1 digit hex)
                            for (int i = 0; i < d_bits_demodulated; i += 4) {
                                int hex_val = 0;
                                for (int j = 0; j < 4 && (i + j) < d_bits_demodulated; j++) {
                                    if (out[start_bit + i + j] == 1) {
                                        hex_val |= (1 << (3 - j));
                                    }
                                }
                                std::cout << std::hex << std::uppercase << hex_val;
                            }
                            std::cout << std::dec << std::endl;

                            // Appel du décodeur COSPAS-SARSAT avec correction BCH
                            decode_1g(out + start_bit, d_bits_demodulated);
                        }

                        reset_demodulator();
                        // VIDER l'accumulateur apres une trame complète
                        // Les echantillons restants sont probablement du burst suivant
                        // mais au milieu (BPSK), pas au debut (porteuse)
                        // Mieux vaut les ignorer et attendre le prochain burst complet
                        d_sample_accumulator.clear();
                        samples_processed = 0;  // Rien a effacer, tout est vidé
                        break;
                    }
                }
            }
                break;
        }

        d_last_phase = phase;
    }

    // Nettoyer les echantillons traites du buffer d'accumulation
    if (d_state == STATE_CARRIER_SEARCH || (samples_processed > 0 && d_total_bit_count >= TOTAL_BITS)) {
        d_sample_accumulator.erase(
            d_sample_accumulator.begin(),
            d_sample_accumulator.begin() + samples_processed
        );
    }

    if (d_debug_mode) {
        std::cout << "[DEBUG] process_accumulated_buffer() end: samples_processed=" << samples_processed
                  << ", strong_samples_in_loop=" << strong_samples_in_loop
                  << ", phase_history.size()=" << d_phase_history.size()
                  << ", freq_lock=" << d_freq_lock << std::endl;
    }

    return bytes_produced;
}

// Calcul de phase (inchangé mais garanti stable)
float cospas_sarsat_demodulator_impl::compute_phase(std::complex<float> sample)
{
    return std::arg(sample);
}

float cospas_sarsat_demodulator_impl::normalize_phase(float phase)
{
    phase = std::fmod(phase, 2.0f * M_PI);
    if (phase > M_PI) return phase - 2.0f * M_PI;
    if (phase < -M_PI) return phase + 2.0f * M_PI;
    return phase;
}

float cospas_sarsat_demodulator_impl::compute_phase_diff(float phase1, float phase2)
{
    float diff = phase2 - phase1;
    return normalize_phase(diff);
}

bool cospas_sarsat_demodulator_impl::detect_carrier(float phase)
{
    // Si la correction est active, la phase peut dériver - utiliser une condition différente
    if (d_freq_lock) {
        // Après correction de frequence, la phase devrait être relativement stable
        // mais peut avoir une légère dérive résiduelle
        // Utiliser une fenêtre de moyenne plus grande et une tolérance adaptative
        
        //if (d_phase_history.size() < 50) {
            return true;  // Pas assez d'historique, accepter
        }

      /*  // Calculer la dérive moyenne récente
        float recent_drift = 0.0f;
        int window_size = std::min(100, (int)d_phase_history.size());
        for (int i = d_phase_history.size() - window_size; i < (int)d_phase_history.size() - 1; i++) {
            float diff = d_phase_history[i+1] - d_phase_history[i];
            // Normaliser entre -π et +π
            if (diff > M_PI) diff -= 2.0f * M_PI;
            else if (diff < -M_PI) diff += 2.0f * M_PI;
            recent_drift += diff;
        }
        recent_drift /= (window_size - 1);
        
        // Calculer la variance autour de cette dérive
        float variance = 0.0f;
        for (int i = d_phase_history.size() - window_size; i < (int)d_phase_history.size(); i++) {
            float expected = d_phase_history[d_phase_history.size() - window_size] + 
                           recent_drift * (i - (d_phase_history.size() - window_size));
            float diff = d_phase_history[i] - expected;
            // Normaliser
            if (diff > M_PI) diff -= 2.0f * M_PI;
            else if (diff < -M_PI) diff += 2.0f * M_PI;
            variance += diff * diff;
        }
        variance /= window_size;
        float stddev = std::sqrt(variance);
        
        // Porteuse = faible variance autour d'une dérive linéaire
        // BPSK = forte variance (sauts de phase)
        return stddev < 0.5f;  // Seuil augmenté pour la dérive résiduelle
        
    } else {*/
        // Mode sans correction : phase proche de 0
        float normalized = normalize_phase(phase);
        float threshold = CARRIER_THRESHOLD;
        return std::abs(normalized) < threshold;
//    }
}

// Timing error DÉSACTIVÉ (retourne toujours 0)
// Correction de frequence automatique
gr_complex cospas_sarsat_demodulator_impl::apply_freq_correction(gr_complex sample)
{
    if (!d_freq_lock) {
        return sample;  // Pas encore de correction
    }

    // Appliquer la correction: sample * e^(-j*phase_correction)
    // phase_correction augmente de 2*pi*freq_offset/sample_rate a chaque échantillon
    float correction_i = std::cos(-d_phase_correction);
    float correction_q = std::sin(-d_phase_correction);
    gr_complex correction(correction_i, correction_q);

    // Avancer la phase de correction
    d_phase_correction += 2.0f * M_PI * d_freq_offset / d_sample_rate;

    // Normaliser la phase entre -π et +π
    while (d_phase_correction > M_PI) {
        d_phase_correction -= 2.0f * M_PI;
    }
    while (d_phase_correction < -M_PI) {
        d_phase_correction += 2.0f * M_PI;
    }

    return sample * correction;
}

void cospas_sarsat_demodulator_impl::estimate_freq_offset()
{
    // Estimer l'offset de frequence a partir de l'historique de phase
    // Utiliser au minimum 2000 echantillons (50ms) pour une estimation précise
    if (d_phase_history.size() < 2000) {
        return;  // Pas assez d'echantillons
    }

    // Calculer la dérivée moyenne de la phase (= frequence)
    float phase_diff_sum = 0.0f;
    for (size_t i = 1; i < d_phase_history.size(); i++) {
        float diff = d_phase_history[i] - d_phase_history[i-1];
        // Unwrap: gérer les sauts -π/+π
        if (diff > M_PI) {
            diff -= 2.0f * M_PI;
        } else if (diff < -M_PI) {
            diff += 2.0f * M_PI;
        }
        phase_diff_sum += diff;
    }

    float phase_diff_avg = phase_diff_sum / (d_phase_history.size() - 1);

    // VÉRIFIER QUE C'EST BIEN UNE PORTEUSE (phase linéaire, pas escalier BPSK)
    // Calculer l'erreur résiduelle : écart entre phase réelle et droite ajustée
    float phase_unwrapped = d_phase_history[0];
    float residual_sq_sum = 0.0f;
    for (size_t i = 1; i < d_phase_history.size(); i++) {
        float diff = d_phase_history[i] - d_phase_history[i-1];
        if (diff > M_PI) diff -= 2.0f * M_PI;
        else if (diff < -M_PI) diff += 2.0f * M_PI;
        phase_unwrapped += diff;

        // Phase attendue si linéaire : phase_history[0] + i * slope
        float expected = d_phase_history[0] + i * phase_diff_avg;
        float residual = phase_unwrapped - expected;
        residual_sq_sum += residual * residual;
    }
    float residual_std = std::sqrt(residual_sq_sum / (d_phase_history.size() - 1));

    if (d_debug_mode) {
        std::cout << "[DEBUG] estimate_freq_offset(): slope=" << phase_diff_avg
                  << " rad/sample, residual_std=" << residual_std << " rad" << std::endl;
    }

    // Si résidu trop grand, ce n'est pas une porteuse (c'est du BPSK avec marches)
    // Porteuse : résidu < 0.3 rad (juste du bruit)
    // BPSK : résidu > 1 rad (les marches ±2.2 rad créent des écarts)
    if (residual_std > 0.3f) {
        if (d_debug_mode) {
            std::cout << "[COSPAS] Residu trop grand (" << residual_std
                      << " rad) - pas une porteuse linéaire, probablement BPSK" << std::endl;
        }
        // Vider l'historique et recommencer
        d_phase_history.clear();
        return;
    }

    // Convertir en Hz
    d_freq_offset = phase_diff_avg / (2.0f * M_PI) * d_sample_rate;

    if (d_debug_mode) {
        std::cout << "[DEBUG] estimate_freq_offset(): offset=" << d_freq_offset
                  << " Hz, |offset|=" << std::abs(d_freq_offset) << std::endl;
    }

    // Verrouiller si l'offset est significatif (> 10 Hz)
    if (std::abs(d_freq_offset) > 10.0f) {
        d_freq_lock = true;
        d_phase_correction = 0.0f;
        d_carrier_phase_ref = 0.0f;  // Sera calculé apres quelques echantillons corrigés

        if (d_debug_mode) {
            std::cout << "[COSPAS] Offset de frequence detecte: "
                      << d_freq_offset << " Hz - correction activée" << std::endl;
            std::cout << "[COSPAS] Phase de reference sera calculee apres correction" << std::endl;
        }
    } else if (d_debug_mode) {
        std::cout << "[DEBUG] Offset trop faible (" << d_freq_offset
                  << " Hz) - pas de verrouillage" << std::endl;
    }
}

// Detecte la position exacte de la transition Manchester dans un bit
// Retourne la position du saut de phase (devrait etre proche de num_samples/2)
int cospas_sarsat_demodulator_impl::detect_transition_position(const std::complex<float>* samples, int num_samples)
{
    float max_phase_diff = 0.0f;
    int best_position = num_samples / 2;  // Position par defaut au centre

    // Chercher autour du centre prevu (+/- 40% = large fenetre pour gros decalages)
    // Evite de detecter les bords du bit (debut ou fin) qui ne sont pas la transition Manchester
    int center = num_samples / 2;
    int window = num_samples * 2 / 5;  // +/- 40%
    int search_start = center - window;
    int search_end = center + window;

    if (search_start < 2) search_start = 2;
    if (search_end > num_samples - 2) search_end = num_samples - 2;

    // Chercher le saut de phase le plus abrupt (gradient maximum)
    for (int i = search_start; i < search_end; i++) {
        float phase_before = std::arg(samples[i - 1]);
        float phase_after = std::arg(samples[i + 1]);
        float phase_diff = std::abs(compute_phase_diff(phase_before, phase_after));

        if (phase_diff > max_phase_diff) {
            max_phase_diff = phase_diff;
            best_position = i;
        }
    }

    return best_position;
}

// Décodage de bit - échantillonnage au centre de chaque demi-bit avec tracking adaptatif
char cospas_sarsat_demodulator_impl::decode_bit(const std::complex<float>* samples, int num_samples)
{
    int half_samples = num_samples / 2;
    int quarter_samples = half_samples / 2;

    // Appliquer l'offset de timing adaptatif (d_mu)
    int timing_offset = static_cast<int>(d_mu);
    int center_first = quarter_samples + timing_offset;
    int center_second = half_samples + quarter_samples + timing_offset;

    // Bornes de securite
    if (center_first < 0) center_first = 0;
    if (center_first >= num_samples) center_first = num_samples - 1;
    if (center_second < 0) center_second = 0;
    if (center_second >= num_samples) center_second = num_samples - 1;

    float phase_first = std::arg(samples[center_first]);
    float phase_second = std::arg(samples[center_second]);
    float phase_diff = compute_phase_diff(phase_first, phase_second);

    // Bit '1': +1.1 -> -1.1 (transition descendante < 0)
    // Bit '0': -1.1 -> +1.1 (transition montante > 0)
    if (phase_diff < -0.5f) {
        return '1';
    } else if (phase_diff > 0.5f) {
        return '0';
    } else {
        // Transition ambiguë - choisir basé sur le signe (meilleure estimation)
        return (phase_diff < 0) ? '1' : '0';
    }
}

// RÉINITIALISATION COMPLETE et GARANTIE
void cospas_sarsat_demodulator_impl::reset_demodulator()
{
    d_state = STATE_CARRIER_SEARCH;
    d_carrier_count = 0;
    d_carrier_start_idx = 0;
    d_sample_count = 0;
    d_bits_demodulated = 0;
    d_total_bit_count = 0;
    d_preamble_ones = 0;
    d_consecutive_carrier = 0;
    d_error_count = 0;
    d_freq_correction_frozen = false;

    // Réinitialiser récupération de timing
    d_transition_positions.clear();
    d_sync_sample_count = 0;
    d_measured_samples_per_bit = static_cast<float>(d_samples_per_bit);

    // Réinitialiser la taille attendue du burst (attendre prochain burst_start tag)
    d_expected_burst_size = 0;

    std::fill(d_bit_buffer.begin(), d_bit_buffer.end(), std::complex<float>(0, 0));
    // NOTE: Ne PAS clear d_sample_accumulator ici car il est géré par process_accumulated_buffer()

    // IMPORTANT: Vider l'historique de phase pour éviter "Carrier lost" sur les bursts suivants
    // La comparaison de phase utilise d_phase_history, si on garde les vieilles phases du burst précédent
    // le nouveau burst sera rejeté car sa phase absolue est différente
    d_phase_history.clear();

    // IMPORTANT: Réinitialiser le verrouillage de frequence pour recalculer l'offset sur chaque burst
    // L'offset peut varier entre bursts (dérive oscillateur RTL-SDR/PlutoSDR)
    d_freq_lock = false;
    d_freq_offset = 0.0f;

    // Réinitialiser la PLL
    d_pll_phase = 0.0f;
    d_pll_integral = 0.0f;

    d_last_phase = 0.0f;
    d_phase_avg = 0.0f;
    d_phase_lpf_state = 0.0f;
    d_timing_error = 0.0f;
    d_mu = -20.0f;  // Bonne valeur par defaut pour la plupart des balises
    d_omega = static_cast<float>(d_samples_per_bit);
    d_pll_integral = 0.0f;
    d_transition_positions.clear();
}

// Méthodes thread-safe
bool cospas_sarsat_demodulator_impl::is_synchronized() const
{
    std::lock_guard<std::mutex> lock(d_mutex);
    return (d_state == STATE_MESSAGE || d_state == STATE_FRAME_SYNC || d_state == STATE_BIT_SYNC);
}

int cospas_sarsat_demodulator_impl::get_frames_decoded() const
{
    std::lock_guard<std::mutex> lock(d_mutex);
    return d_bursts_detected;
}

int cospas_sarsat_demodulator_impl::get_sync_failures() const
{
    return 0;
}

void cospas_sarsat_demodulator_impl::set_debug_mode(bool enable)
{
    std::lock_guard<std::mutex> lock(d_mutex);
    d_debug_mode = enable;
}

void cospas_sarsat_demodulator_impl::reset_statistics()
{
    std::lock_guard<std::mutex> lock(d_mutex);
    d_bursts_detected = 0;
}

void cospas_sarsat_demodulator_impl::handle_burst_message(pmt::pmt_t msg) {
    const gr_complex* samples = nullptr;
    size_t num_samples = 0;
    
    // Format 1: Dictionnaire avec clé "samples" contenant un blob
    if (pmt::is_dict(msg)) {
        pmt::pmt_t samples_pmt = pmt::dict_ref(msg, pmt::mp("samples"), pmt::PMT_NIL);
        
        if (pmt::is_blob(samples_pmt)) {
            const void* blob_data = pmt::blob_data(samples_pmt);
            size_t blob_size = pmt::blob_length(samples_pmt);
            samples = static_cast<const gr_complex*>(blob_data);
            num_samples = blob_size / sizeof(gr_complex);
            
            if (d_debug_mode) {
                std::cout << "[DEMOD] Burst recu: " << num_samples << " echantillons (format blob)" << std::endl;
            }
        }
        else if (pmt::is_c32vector(samples_pmt)) {
            num_samples = pmt::length(samples_pmt);
            samples = pmt::c32vector_elements(samples_pmt, num_samples);
            
            if (d_debug_mode) {
                std::cout << "[DEMOD] Burst recu: " << num_samples << " echantillons (format c32vector)" << std::endl;
            }
        }
    }
    // Format 2: Vecteur complexe direct
    else if (pmt::is_c32vector(msg)) {
        num_samples = pmt::length(msg);
        samples = pmt::c32vector_elements(msg, num_samples);
        
        if (d_debug_mode) {
            std::cout << "[DEMOD] Burst recu: " << num_samples << " echantillons (format c32vector direct)" << std::endl;
        }
    }
    
    // Traiter le burst si on a des echantillons valides
    if (samples && num_samples > 0) {
        process_burst(samples, num_samples);
    } else {
        if (d_debug_mode) {
            std::cout << "[DEMOD] Message invalide" << std::endl;
        }
    }
} 

// La fonction process_burst doit être correctement définie
void cospas_sarsat_demodulator_impl::process_burst(const gr_complex* samples, int num_samples) {
    // Réinitialiser le demodulateur pour un nouveau burst
    reset_demodulator();

    // AJOUT: Garantir qu'on a assez d'echantillons pour le dernier bit
    int padding_samples = 2 * d_samples_per_bit; // 200 samples de marge
    
    // Vider l'accumulateur et copier les echantillons
    d_sample_accumulator.clear();
    d_sample_accumulator.insert(d_sample_accumulator.end(), samples, samples + num_samples);
    
    // Ajouter du padding si nécessaire
    for (int i = 0; i < padding_samples; i++) {
        d_sample_accumulator.push_back(gr_complex(0, 0));
    }

    // Traiter le buffer accumule
    uint8_t output_buffer[2048];
    int bytes_produced = process_accumulated_buffer(output_buffer, sizeof(output_buffer));

    if (d_debug_mode) {
        std::cout << "[DEMOD] Burst traite: " << bytes_produced << " bytes decodes, "
                  << "echantillons d'origine: " << num_samples 
                  << ", apres padding: " << d_sample_accumulator.size() << std::endl;
    }
}

} // namespace cospas
} // namespace gr
