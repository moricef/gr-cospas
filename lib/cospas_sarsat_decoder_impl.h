/* -*- c++ -*- */
/*
 * Header STABLE du décodeur Cospas-Sarsat
 */

#ifndef INCLUDED_COSPAS_COSPAS_SARSAT_DECODER_IMPL_H
#define INCLUDED_COSPAS_COSPAS_SARSAT_DECODER_IMPL_H

#include <gnuradio/cospas/cospas_sarsat_decoder.h>
#include <vector>
#include <complex>
#include <deque>
#include <mutex>

namespace gr {
namespace cospas {

class cospas_sarsat_decoder_impl : public cospas_sarsat_decoder
{
private:
    // Paramètres fixes
    float d_sample_rate;
    static constexpr float BIT_RATE = 400.0f;
    int d_samples_per_bit;
    static constexpr float CARRIER_DURATION = 0.160f;
    int d_carrier_samples;
    
    // Structure réelle Cospas-Sarsat
    static constexpr int PREAMBLE_BITS = 15;
    static constexpr int FRAME_SYNC_BITS = 9;
    static constexpr int SHORT_MESSAGE_BITS = 88;
    static constexpr int LONG_MESSAGE_BITS = 120;
    static constexpr int SHORT_FRAME_TOTAL_BITS = 112;  // 15 + 9 + 88
    static constexpr int LONG_FRAME_TOTAL_BITS = 144;   // 15 + 9 + 120

    // Patterns
    static constexpr uint16_t FRAME_SYNC_NORMAL = 0b000101111;
    static constexpr uint16_t FRAME_SYNC_TEST = 0b011010000;

    // Seuils
    static constexpr float MOD_PHASE = 1.1f;
    static constexpr float PHASE_THRESHOLD = 1.0f;
    static constexpr float CARRIER_THRESHOLD = 0.2f;
    static constexpr float JUMP_THRESHOLD = 0.5f;
    static constexpr int MAX_CONSECUTIVE_ERRORS = 5;

    // États
    enum DecoderState {
        STATE_CARRIER_SEARCH,
        STATE_INITIAL_JUMP, 
        STATE_PREAMBLE_SYNC,
        STATE_FRAME_SYNC,
        STATE_DATA_DECODE
    };
    
    // Variables d'état
    DecoderState d_state;
    int d_carrier_count;
    int d_sample_count;
    int d_bit_count;           // Bits de message
    int d_total_bit_count;     // Tous les bits (préambule + sync + message)
    int d_preamble_ones;
    int d_frame_sync_bits;
    uint16_t d_frame_sync_pattern;
    bool d_is_test_mode;
    int d_error_count;

    // Buffers
    std::vector<std::complex<float>> d_bit_buffer;
    std::deque<uint8_t> d_output_bits;
    std::vector<float> d_phase_history;
    
    // Traitement
    float d_last_phase;
    float d_phase_avg;
    int d_consecutive_carrier;
    bool d_sync_acquired;
    int d_frame_length;
    bool d_is_long_frame;

    // Timing (DÉSACTIVÉ pour signal synthétique)
    float d_timing_error;
    float d_mu;
    float d_omega;
    float d_gain_omega;
    float d_gain_mu;
    float d_pll_integral;

    // Statistiques
    int d_frames_decoded;
    int d_sync_failures;
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
    char decode_bit(const std::complex<float>* samples, int num_samples);
    bool detect_carrier(float phase);
    bool detect_initial_jump(float phase);
    void reset_decoder();
    float average_phase(const std::complex<float>* samples, int start, int count);
    float compute_timing_error(const std::complex<float>* samples, int num_samples);
    void update_timing(float error);
    float low_pass_filter(float phase);

public:
    cospas_sarsat_decoder_impl(float sample_rate, bool debug_mode);
    ~cospas_sarsat_decoder_impl();
    
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
