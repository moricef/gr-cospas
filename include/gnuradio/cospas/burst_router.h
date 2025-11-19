/* -*- c++ -*- */
/*
 * Copyright 2025 COSPAS-SARSAT.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_COSPAS_BURST_ROUTER_H
#define INCLUDED_COSPAS_BURST_ROUTER_H

#include <gnuradio/cospas/api.h>
#include <gnuradio/block.h>

namespace gr {
namespace cospas {

/*!
 * \brief Router automatique pour bursts 1G/2G
 *
 * Analyse les bursts entrants et les route vers le démodulateur approprié:
 * - Port 0: Bursts 1G (FGB - First Generation Beacon)
 * - Port 1: Bursts 2G (SGB - Second Generation Beacon)
 *
 * Détection basée sur:
 * - Taille du burst (< 25000 samples → 1G, >= 25000 → 2G)
 * - Présence de porteuse 160ms (1G uniquement)
 *
 * \ingroup cospas
 */
class COSPAS_API burst_router : virtual public gr::block
{
public:
    typedef std::shared_ptr<burst_router> sptr;

    /*!
     * \brief Créer un router de bursts 1G/2G
     *
     * \param sample_rate Taux d'échantillonnage (Hz)
     * \param debug_mode Active les messages de debug
     */
    static sptr make(float sample_rate = 40000.0f, bool debug_mode = false);

    /*!
     * \brief Obtenir le nombre de bursts 1G routés
     */
    virtual int get_bursts_1g() const = 0;

    /*!
     * \brief Obtenir le nombre de bursts 2G routés
     */
    virtual int get_bursts_2g() const = 0;

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

#endif /* INCLUDED_COSPAS_BURST_ROUTER_H */
