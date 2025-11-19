/* -*- c++ -*- */
/*
 * Copyright 2025 COSPAS-SARSAT.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "burst_router_impl.h"
#include <gnuradio/io_signature.h>
#include <pmt/pmt.h>
#include <iostream>
#include <cmath>
#include <algorithm>
#include <cstring>
#include <boost/bind/bind.hpp>

namespace gr {
namespace cospas {

burst_router::sptr
burst_router::make(float sample_rate, bool debug_mode)
{
    return gnuradio::make_block_sptr<burst_router_impl>(sample_rate, debug_mode);
}

burst_router_impl::burst_router_impl(float sample_rate, bool debug_mode)
    : gr::block("burst_router",
                gr::io_signature::make(1, 1, sizeof(gr_complex)),
                gr::io_signature::make(2, 2, sizeof(gr_complex))),  // 2 sorties
      d_sample_rate(sample_rate),
      d_debug_mode(debug_mode),
      d_in_burst(false),
      d_burst_ready_for_output(false),
      d_burst_output_offset(0),
      d_bursts_1g(0),
      d_bursts_2g(0)
{
    // Message ports (asynchrones - prioritaires)
    message_port_register_in(pmt::mp("bursts"));
    message_port_register_out(pmt::mp("bursts_1g"));
    message_port_register_out(pmt::mp("bursts_2g"));

    // Connecter le handler avec boost::bind
    set_msg_handler(pmt::mp("bursts"),
                    boost::bind(&burst_router_impl::handle_burst_message, this, boost::placeholders::_1));

    // IMPORTANT: Desactiver la propagation automatique des tags d'entree
    // Le router génère ses propres tags burst_start/burst_end sur sa sortie
    set_tag_propagation_policy(TPP_DONT);

    // PAS de set_min_noutput_items - gérer la sortie progressive sur plusieurs appels
    // Les bursts peuvent être > 32k samples (limite buffer GNU Radio)

    if (d_debug_mode) {
        std::cout << "[ROUTER] Initialise:" << std::endl;
        std::cout << "  Sample rate: " << d_sample_rate << " Hz" << std::endl;
        std::cout << "  Mode: sortie progressive multi-appels" << std::endl;
        std::cout << "  Stream Port 0: Bursts 1G (FGB - BPSK)" << std::endl;
        std::cout << "  Stream Port 1: Bursts 2G (SGB - OQPSK DSSS)" << std::endl;
        std::cout << "  Message Port 'bursts': entree" << std::endl;
        std::cout << "  Message Port 'bursts_1g': sortie 1G" << std::endl;
        std::cout << "  Message Port 'bursts_2g': sortie 2G" << std::endl;
    }
}

burst_router_impl::~burst_router_impl()
{
}

void
burst_router_impl::handle_burst_message(pmt::pmt_t msg)
{
    // Message ports: optionnel (unreliable delivery avec GNU Radio)
    // Routing principal se fait via stream + tags (fiable)
    // Ce handler peut servir pour monitoring/logging externe si besoin

    if (!pmt::is_dict(msg)) {
        return;
    }

    pmt::pmt_t samples_pmt = pmt::dict_ref(msg, pmt::mp("samples"), pmt::PMT_NIL);
    if (pmt::is_null(samples_pmt)) {
        return;
    }

    std::vector<gr_complex> samples = pmt::c32vector_elements(samples_pmt);
    BurstType type = detect_burst_type(samples);

    // Publier sur les ports de sortie (pour monitoring externe)
    if (type == TYPE_1G) {
        message_port_pub(pmt::mp("bursts_1g"), msg);
    } else {
        message_port_pub(pmt::mp("bursts_2g"), msg);
    }
}

burst_router_impl::BurstType
burst_router_impl::detect_burst_type(const std::vector<gr_complex>& samples)
{
    int size = samples.size();

    // Méthode 1 : Taille du burst (le plus robuste)
    // 1G : ~14k-20k samples (360ms @ 40kHz)
    // 2G : ~38k-40k samples (960ms @ 40kHz)
    const int THRESHOLD_SIZE = 25000;

    if (size < THRESHOLD_SIZE) {
        if (d_debug_mode) {
            std::cout << "[ROUTER] Detection 1G par taille: " << size
                      << " samples < " << THRESHOLD_SIZE << std::endl;
        }
        return TYPE_1G;
    }

    // Méthode 2 : Vérification de porteuse (optionnel, confirmation)
    // 1G a une porteuse non modulée de 160ms = 6400 samples @ 40kHz
    int carrier_window = static_cast<int>(d_sample_rate * 0.160f);

    if (size >= carrier_window) {
        bool has_carrier = detect_unmodulated_carrier(samples, carrier_window);

        if (has_carrier && size < THRESHOLD_SIZE * 2) {
            if (d_debug_mode) {
                std::cout << "[ROUTER] Detection 1G par porteuse: presente" << std::endl;
            }
            return TYPE_1G;
        }
    }

    if (d_debug_mode) {
        std::cout << "[ROUTER] Detection 2G: taille=" << size
                  << " samples >= " << THRESHOLD_SIZE << std::endl;
    }
    return TYPE_2G;
}

bool
burst_router_impl::detect_unmodulated_carrier(const std::vector<gr_complex>& samples,
                                               int window_size)
{
    if (samples.size() < static_cast<size_t>(window_size)) {
        return false;
    }

    // Analyser les variations de phase sur la fenêtre
    // Une porteuse non modulée a une phase stable (faibles variations)
    std::vector<float> phases;
    phases.reserve(window_size);

    for (int i = 0; i < window_size; i++) {
        float phase = std::arg(samples[i]);
        phases.push_back(phase);
    }

    // Calculer les variations de phase
    std::vector<float> phase_diffs;
    for (size_t i = 1; i < phases.size(); i++) {
        float diff = phases[i] - phases[i-1];

        // Normaliser entre -π et +π
        while (diff > M_PI) diff -= 2.0f * M_PI;
        while (diff < -M_PI) diff += 2.0f * M_PI;

        phase_diffs.push_back(std::abs(diff));
    }

    // Calculer l'écart-type des variations de phase
    float mean = 0.0f;
    for (float diff : phase_diffs) {
        mean += diff;
    }
    mean /= phase_diffs.size();

    float variance = 0.0f;
    for (float diff : phase_diffs) {
        float delta = diff - mean;
        variance += delta * delta;
    }
    variance /= phase_diffs.size();
    float stddev = std::sqrt(variance);

    // Seuil : porteuse non modulée a stddev < 0.3 radians
    const float CARRIER_THRESHOLD = 0.3f;
    bool is_carrier = (stddev < CARRIER_THRESHOLD);

    if (d_debug_mode) {
        std::cout << "[ROUTER] Analyse porteuse: stddev=" << stddev
                  << " (seuil=" << CARRIER_THRESHOLD << ") -> "
                  << (is_carrier ? "OUI" : "NON") << std::endl;
    }

    return is_carrier;
}

int burst_router_impl::general_work(int noutput_items,
                                     gr_vector_int& ninput_items,
                                     gr_vector_const_void_star& input_items,
                                     gr_vector_void_star& output_items)
{
    const gr_complex* in = static_cast<const gr_complex*>(input_items[0]);
    gr_complex* out0 = static_cast<gr_complex*>(output_items[0]);  // 1G
    gr_complex* out1 = static_cast<gr_complex*>(output_items[1]);  // 2G

    int ninput = ninput_items[0];
    int produced0 = 0;
    int produced1 = 0;

    // BLOQUER l'entree si un burst est en cours de sortie
    // Sinon le burst suivant arrive avant que le courant soit fini!
    if (d_burst_ready_for_output) {
        // Ne pas consommer d'entree tant que le burst n'est pas completement sorti
        ninput = 0;
    }

    // Lire les tags AVANT d'accumuler pour détecter les debuts/fins de burst
    std::vector<tag_t> tags;
    if (ninput > 0) {
        get_tags_in_range(tags, 0, nitems_read(0), nitems_read(0) + ninput);
    }

    bool was_in_burst = d_in_burst;
    bool burst_start_found = false;
    bool burst_end_found = false;

    for (const auto& tag : tags) {
        if (pmt::eq(tag.key, pmt::intern("burst_start"))) {
            // IMPORTANT: Ne réinitialiser QUE si c'est un NOUVEAU burst
            // Le detector envoie burst_start sur chaque fragment du même burst!
            if (!was_in_burst && !d_in_burst) {
                burst_start_found = true;
                d_in_burst = true;
                d_burst_ready_for_output = false;  // Pas encore pret
                d_current_burst.clear();
                d_burst_output_offset = 0;

                if (d_debug_mode) {
                    long size = pmt::to_long(tag.value);
                    std::cout << "[ROUTER] NOUVEAU burst detecte (taille=" << size << ")" << std::endl;
                }
            } else {
                if (d_debug_mode) {
                    std::cout << "[ROUTER] Tag burst_start ignore (deja dans un burst)" << std::endl;
                }
            }
        }
        else if (pmt::eq(tag.key, pmt::intern("burst_end"))) {
            burst_end_found = true;
            // Ne pas mettre d_in_burst = false ici, on doit d'abord accumuler!
            if (d_debug_mode) {
                std::cout << "[ROUTER] Tag burst_end detecte" << std::endl;
            }
        }
    }

    // ACCUMULER les samples SI on est dans un burst (inclut le premier fragment!)
    if (d_in_burst && ninput > 0) {
        for (int i = 0; i < ninput; i++) {
            d_current_burst.push_back(in[i]);
        }
        if (d_debug_mode && burst_start_found) {
            std::cout << "[ROUTER] Premier fragment accumule: " << ninput << " samples" << std::endl;
        }
    }

    // MAINTENANT gérer burst_end (apres accumulation)
    if (burst_end_found) {
        d_burst_ready_for_output = true;  // Maintenant pret a sortir!
        d_in_burst = false;  // Fin accumulation -> accepter prochain burst!
        if (d_debug_mode) {
            std::cout << "[ROUTER] Burst complet: " << d_current_burst.size()
                      << " samples, pret pour sortie" << std::endl;
        }
    }

    // Sortie progressive du burst (peut prendre plusieurs appels work())
    // IMPORTANT: N'autoriser la sortie QU'APRÈS burst_end (burst complet)
    if (d_burst_ready_for_output && d_burst_output_offset < d_current_burst.size()) {
        BurstType type = detect_burst_type(d_current_burst);

        // INCRÉMENTER LES STATS AU PREMIER APPEL (offset=0)
        // Sinon si flowgraph termine avant sortie complète, stats = 0!
        if (d_burst_output_offset == 0) {
            std::lock_guard<std::mutex> lock(d_mutex);
            if (type == TYPE_1G) {
                d_bursts_1g++;
            } else {
                d_bursts_2g++;
            }

            if (d_debug_mode) {
                std::cout << "[ROUTER] Debut sortie burst type "
                          << (type == TYPE_1G ? "1G" : "2G")
                          << " (" << d_current_burst.size() << " samples)" << std::endl;
            }
        }

        int remaining = d_current_burst.size() - d_burst_output_offset;
        int to_copy = std::min(remaining, noutput_items);
        int port = (type == TYPE_1G) ? 0 : 1;

        if (type == TYPE_1G) {
            // Copier depuis d_burst_output_offset
            std::memcpy(out0, d_current_burst.data() + d_burst_output_offset,
                       to_copy * sizeof(gr_complex));
            produced0 = to_copy;

            if (d_debug_mode) {
                std::cout << "[ROUTER] Sortie 1G: [" << d_burst_output_offset
                          << ", " << (d_burst_output_offset + to_copy) << ") / "
                          << d_current_burst.size() << " samples" << std::endl;
            }
        }
        else {  // TYPE_2G
            std::memcpy(out1, d_current_burst.data() + d_burst_output_offset,
                       to_copy * sizeof(gr_complex));
            produced1 = to_copy;

            if (d_debug_mode) {
                std::cout << "[ROUTER] Sortie 2G: [" << d_burst_output_offset
                          << ", " << (d_burst_output_offset + to_copy) << ") / "
                          << d_current_burst.size() << " samples" << std::endl;
            }
        }

        // Ajouter tag burst_start au PREMIER fragment seulement
        if (d_burst_output_offset == 0) {
            add_item_tag(port, nitems_written(port),
                        pmt::intern("burst_start"),
                        pmt::from_long(d_current_burst.size()));
            if (d_debug_mode) {
                std::cout << "[ROUTER] Tag burst_start ajoute a offset "
                          << nitems_written(port) << " (taille=" << d_current_burst.size() << ")" << std::endl;
            }
        }

        d_burst_output_offset += to_copy;

        // Si tout le burst est sorti, ajouter burst_end et nettoyer
        if (d_burst_output_offset >= d_current_burst.size()) {
            // Ajouter tag burst_end a la fin du burst
            add_item_tag(port, nitems_written(port) + to_copy - 1,
                        pmt::intern("burst_end"),
                        pmt::from_long(d_current_burst.size()));
            if (d_debug_mode) {
                std::cout << "[ROUTER] Tag burst_end ajoute a offset "
                          << (nitems_written(port) + to_copy - 1) << std::endl;
                std::cout << "[ROUTER] Burst completement sorti -> reset" << std::endl;
            }

            d_current_burst.clear();
            d_burst_output_offset = 0;
            d_burst_ready_for_output = false;
            d_in_burst = false;
        }
    }

    consume_each(ninput);

    // Retourner le max des deux sorties pour GNU Radio
    return std::max(produced0, produced1);
}

int burst_router_impl::get_bursts_1g() const
{
    std::lock_guard<std::mutex> lock(d_mutex);
    return d_bursts_1g;
}

int burst_router_impl::get_bursts_2g() const
{
    std::lock_guard<std::mutex> lock(d_mutex);
    return d_bursts_2g;
}

void burst_router_impl::reset_statistics()
{
    std::lock_guard<std::mutex> lock(d_mutex);
    d_bursts_1g = 0;
    d_bursts_2g = 0;
}

void burst_router_impl::set_debug_mode(bool enable)
{
    std::lock_guard<std::mutex> lock(d_mutex);
    d_debug_mode = enable;
}

} // namespace cospas
} // namespace gr
