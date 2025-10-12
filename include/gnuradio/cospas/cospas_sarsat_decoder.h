/* -*- c++ -*- */
/*
 * Header public (interface) pour GNU Radio
 */

#ifndef INCLUDED_COSPAS_COSPAS_SARSAT_DECODER_H
#define INCLUDED_COSPAS_COSPAS_SARSAT_DECODER_H

#include <gnuradio/cospas/api.h>
#include <gnuradio/sync_block.h>

namespace gr {
namespace cospas {

/*!
 * \brief Décodeur Cospas-Sarsat biphase-L
 * \ingroup cospas
 *
 * Décode les signaux 406 MHz Cospas-Sarsat
 * - Porteuse 160ms
 * - 15 bits de synchronisation 
 * - Modulation biphase-L ±1.1 rad
 */
class COSPAS_API cospas_sarsat_decoder : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<cospas_sarsat_decoder> sptr;

    /*!
     * \brief Créer une instance du décodeur
     * \param sample_rate Fréquence d'échantillonnage en Hz (défaut: 6400)
     * \param debug_mode Active les messages de debug
     */
    static sptr make(float sample_rate = 6400.0f, bool debug_mode = false);

    /*!
     * \brief Obtenir l'état de synchronisation
     */
    virtual bool is_synchronized() const = 0;

    /*!
     * \brief Obtenir le nombre de trames décodées
     */
    virtual int get_frames_decoded() const = 0;

    /*!
     * \brief Obtenir le nombre d'échecs de synchronisation
     */
    virtual int get_sync_failures() const = 0;

    /*!
     * \brief Activer/désactiver le mode debug
     */
    virtual void set_debug_mode(bool enable) = 0;

    /*!
     * \brief Réinitialiser les statistiques
     */
    virtual void reset_statistics() = 0;
};

} // namespace cospas
} // namespace gr

#endif /* INCLUDED_COSPAS_COSPAS_SARSAT_DECODER_H */
