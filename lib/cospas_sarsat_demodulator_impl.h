/* -*- c++ -*- */
/*
 * Header STABLE du décodeur Cospas-Sarsat
 */

#ifndef INCLUDED_COSPAS_COSPAS_SARSAT_DECODER_IMPL_H
#define INCLUDED_COSPAS_COSPAS_SARSAT_DECODER_IMPL_H

#include <gnuradio/cospas/cospas_sarsat_demodulator.h>
#include <vector>
#include <complex>
#include <deque>
#include <mutex>

namespace gr {
namespace cospas {

class cospas_sarsat_demodulator_impl : public cospas_sarsat_demodulator
{
private:
    // Paramètres fixes
    float d_sample_rate;
    static constexpr float BIT_RATE = 400.0f;
    int d_samples_per_bit;
    static constexpr float CARRIER_DURATION = 0.160f;
    int d_carrier_samples;
    int d_carrier_samples_min;  // Minimum requis avec correction active
    
    // Structure COSPAS-SARSAT (démodulateur)
    static constexpr int BIT_SYNC_BITS = 15;       // Bits 1-15: bit sync (15 bits a '1')
    static constexpr int FRAME_SYNC_BITS = 9;      // Bits 16-24: frame sync pattern (9 bits)
    static constexpr int MESSAGE_BITS = 120;       // Bits 25-144: message (120 bits)
    static constexpr int TOTAL_BITS = 144;         // Total: 15 + 9 + 120

    // Seuils
    static constexpr float MOD_PHASE = 1.1f;
    static constexpr float PHASE_THRESHOLD = 1.0f;
    static constexpr float CARRIER_THRESHOLD = 0.2f;
    static constexpr float JUMP_THRESHOLD = 0.5f;
    static constexpr int MAX_CONSECUTIVE_ERRORS = 5;
    
    void handle_burst_message(pmt::pmt_t msg);  // Handler pour les messages
    void process_burst(const gr_complex* samples, int num_samples);  // Traitement d'un burst

    // États
    enum DemodulatorState {
        STATE_CARRIER_SEARCH,
        STATE_CARRIER_TRACKING,
        STATE_BIT_SYNC,
        STATE_FRAME_SYNC,
        STATE_MESSAGE
    };

    // Variables d'état
    DemodulatorState d_state;
    int d_carrier_count;
    int d_carrier_start_idx;
    int d_sample_count;
    int d_bits_demodulated;    // Bits démodulés (données uniquement)
    int d_total_bit_count;     // Tous les bits (préambule + sync + données)
    int d_preamble_ones;
    int d_error_count;

    // Récupération de timing sur bits de sync
    std::vector<int> d_transition_positions;  // Positions des transitions detectees
    int d_sync_sample_count;                  // Compteur d'échantillons pendant sync
    float d_measured_samples_per_bit;         // Samples/bit mesuré réellement

    // Gestion des bursts (via tags burst_start)
    long d_expected_burst_size;  // Taille attendue du burst (depuis tag burst_start)
    bool d_waiting_for_burst;    // True = ignorer les samples jusqu'au prochain burst_start

    // Buffers
    std::vector<std::complex<float>> d_bit_buffer;
    std::vector<float> d_phase_history;

    // Buffer d'accumulation pour déterminisme
    std::deque<gr_complex> d_sample_accumulator;
    static constexpr int MIN_SAMPLES_FOR_FRAME = 20000;  // Proche de burst réel (20778) mais permet accumulation

    // Traitement phase
    float d_last_phase;
    float d_phase_avg;
    int d_consecutive_carrier;

    // Timing (DÉSACTIVÉ pour signal synthétique)
    float d_timing_error;
    float d_mu;
    float d_omega;
    float d_gain_omega;
    float d_gain_mu;
    float d_pll_integral;
    float d_pll_phase;              // Phase estimée par la PLL
    static constexpr float PLL_ALPHA = 0.1f;   // Gain proportionnel PLL
    static constexpr float PLL_BETA = 0.01f;   // Gain intégral PLL

    // Correction de fréquence automatique
    float d_freq_offset;           // Offset de fréquence estimé (Hz)
    float d_phase_correction;      // Phase accumulee pour la correction
    bool d_freq_lock;              // Indique si l'offset est verrouillé
    bool d_freq_correction_frozen; // Gel de la correction après détection du saut BPSK
    float d_carrier_phase_ref;     // Phase de référence fixe pour détection porteuse

    // Statistiques
    int d_bursts_detected;
    bool d_debug_mode;

    // Thread-safety
    mutable std::mutex d_mutex;

    // Filtre phase
    float d_phase_lpf_state;
    static constexpr float LPF_ALPHA = 0.3f;

    // Méthodes privées
    float normalize_phase(float phase);
    float compute_phase_diff(float phase1, float phase2);
    float compute_phase(std::complex<float> sample);
    int detect_transition_position(const std::complex<float>* samples, int num_samples);
    char decode_bit(const std::complex<float>* samples, int num_samples);
    bool detect_carrier(float phase);
    void reset_demodulator();

    // Correction de fréquence
    gr_complex apply_freq_correction(gr_complex sample);
    void estimate_freq_offset();

    // NOUVEAU: Traitement du buffer accumule
    int process_accumulated_buffer(uint8_t* out, int max_bytes);

public:
    cospas_sarsat_demodulator_impl(float sample_rate, bool debug_mode);
    ~cospas_sarsat_demodulator_impl();
    
    int work(int noutput_items,
             gr_vector_const_void_star &input_items,
             gr_vector_void_star &output_items) override;
    
    bool is_synchronized() const override;
    int get_frames_decoded() const override;
    int get_sync_failures() const override;
    void set_debug_mode(bool enable) override;
    void reset_statistics() override;
};

} // namespace cospas
} // namespace gr

#endif /* INCLUDED_COSPAS_COSPAS_SARSAT_DECODER_IMPL_H */
