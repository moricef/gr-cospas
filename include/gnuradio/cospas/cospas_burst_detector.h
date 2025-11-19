/* -*- c++ -*- */
/*
 * Copyright 2025 COSPAS-SARSAT.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_COSPAS_COSPAS_BURST_DETECTOR_H
#define INCLUDED_COSPAS_COSPAS_BURST_DETECTOR_H

#include <gnuradio/cospas/api.h>
#include <gnuradio/block.h>

namespace gr {
namespace cospas {

/*!
 * \brief Détecteur de bursts COSPAS-SARSAT avec buffer circulaire
 * \ingroup cospas
 *
 * Ce bloc implémente le double buffering circulaire pour capturer
 * les bursts COSPAS-SARSAT de manière déterministe.
 *
 * Architecture:
 * - Buffer circulaire de 1.5 secondes (configurable)
 * - Détection de burst basée sur seuil d'amplitude
 * - Extraction de bursts complets (porteuse + données)
 * - Compatible 1G (BPSK) et 2G (QPSK/DSSS)
 *
 * Entrée: flux IQ continu (gr_complex)
 * Sortie: bursts isolés (gr_complex)
 */
class COSPAS_API cospas_burst_detector : virtual public gr::block
{
public:
    typedef std::shared_ptr<cospas_burst_detector> sptr;

    /*!
     * \brief Créer un détecteur de bursts
     *
     * \param sample_rate Taux d'échantillonnage (Hz)
     * \param buffer_duration_ms Durée du buffer circulaire (ms) - défaut 1500
     * \param threshold Seuil de détection (amplitude) - défaut 0.1
     * \param min_burst_duration_ms Durée minimale d'un burst (ms) - défaut 200
     * \param debug_mode Active les messages de debug
     */
    static sptr make(float sample_rate,
                     int buffer_duration_ms = 1500,
                     float threshold = 0.1f,
                     int min_burst_duration_ms = 200,
                     bool debug_mode = false);

    /*!
     * \brief Obtenir le nombre de bursts détectés
     */
    virtual int get_bursts_detected() const = 0;

    /*!
     * \brief Réinitialiser les statistiques
     */
    virtual void reset_statistics() = 0;

    /*!
     * \brief Activer/désactiver le mode debug
     */
    virtual void set_debug_mode(bool enable) = 0;
};

} // namespace cospas
} // namespace gr

#endif /* INCLUDED_COSPAS_COSPAS_BURST_DETECTOR_H */
