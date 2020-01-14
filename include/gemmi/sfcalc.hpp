// Copyright 2019 Global Phasing Ltd.
//
// Direct calculation of structure factors
// (see rhogrid.hpp + fourier.hpp for FFT-based calculation)

#ifndef GEMMI_SFCALC_HPP_
#define GEMMI_SFCALC_HPP_

#include <complex>
#include "model.hpp"   // for Structure, ...
#include "smodel.hpp"  // for AtomicStructure
#include "fprime.hpp"  // for cromer_libermann

namespace gemmi {

template <typename Table>
class StructureFactorCalculator {
public:
  StructureFactorCalculator(const UnitCell& cell) : cell_(cell) {}

  void set_hkl(const Miller& hkl) {
    hkl_ = hkl;
    stol2_ = 0.25 * cell_.calculate_1_d2(hkl);
    scattering_factors_.clear();
    scattering_factors_.resize((int) El::END, 0.);
    for (auto const& fprime : fprimes_) {
      El el = fprime.first;
      if (Table::has(el)) {
        double sf = Table::get(el).calculate_sf(stol2_) + fprime.second;
        scattering_factors_[(int)el] = sf;
      }
    }
  }

  double get_scattering_factor(Element element) {
    double& sfactor = scattering_factors_[(int)element.elem];
    if (sfactor == 0.) {
      if (!Table::has(element.elem))
        fail("Missing scattering factor for ", element.name());
      sfactor = Table::get(element.elem).calculate_sf(stol2_);
    }
    return sfactor;
  }

  std::complex<double> get_contribution(Element el, const Fractional& fpos,
                                        double b_iso) {
    double scat_factor = get_scattering_factor(el);
    std::complex<double> part = calculate_sf_part(fpos);
    for (const FTransform& image : cell_.images)
      part += calculate_sf_part(image.apply(fpos));
    return scat_factor * std::exp(-b_iso * stol2_) * part;
  }

  std::complex<double> calculate_sf_from_model(const Model& model,
                                               const Miller& hkl) {
    std::complex<double> sf = 0.;
    set_hkl(hkl);
    for (const Chain& chain : model.chains)
      for (const Residue& res : chain.residues)
        for (const Atom& a : res.atoms)
          sf += (double)a.occ * get_contribution(a.element,
                                                 cell_.fractionalize(a.pos),
                                                 a.b_iso);
    return sf;
  }

  // The occupancy is assumed to take into account symmetry,
  // i.e. to be fractional if the atom is on special position.
  std::complex<double>
  calculate_sf_from_atomic_structure(const AtomicStructure& ast,
                                     const Miller& hkl) {
    std::complex<double> sf = 0.;
    set_hkl(hkl);
    for (const AtomicStructure::Site& site : ast.sites) {
      double b_iso = 8 * pi() * pi() * site.u_iso;
      sf += site.occ * get_contribution(site.element, site.fract, b_iso);
    }
    return sf;
  }

  void set_fprime(El el, double fprime) { fprimes_[el] = fprime; }

  void add_fprimes_from_cl(const AtomicStructure& ast, double energy) {
    for (const AtomicStructure::Site& site : ast.sites)
      if (fprimes_.count(site.element) == 0) {
        int z = site.element.atomic_number();
        double fprime = cromer_libermann(z, energy, nullptr);
        fprimes_.emplace(site.element, fprime);
      }
  }

  void add_fprimes_from_cl(const Model& model, double energy) {
    std::vector<unsigned char> present_elem((int)El::END, 0);
    for (const Chain& chain : model.chains)
      for (const Residue& res : chain.residues)
        for (const Atom& a : res.atoms)
          present_elem[(int)a.element.elem] = 1;
    for (int z = 1; z <= 92; ++z)
      if (present_elem[z]) {
        double fprime = cromer_libermann(z, energy, nullptr);
        fprimes_.emplace((El)z, fprime);
      }
  }

private:
  // calculate part of the structure factor: exp(2 pi i r * s)
  std::complex<double> calculate_sf_part(const Fractional& fpos) const {
    double arg = 2 * pi() * (hkl_[0]*fpos.x + hkl_[1]*fpos.y + hkl_[2]*fpos.z);
    return std::complex<double>{std::cos(arg), std::sin(arg)};
  }

  const UnitCell& cell_;
  Miller hkl_;
  double stol2_;
  std::map<El, double> fprimes_;
  std::vector<double> scattering_factors_;
};


} // namespace gemmi
#endif
