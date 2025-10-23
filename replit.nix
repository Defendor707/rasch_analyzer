{ pkgs }:
{
  deps = [
    pkgs.R
    (pkgs.rWrapper.override {
      packages = with pkgs.rPackages; [
        eRm
        lattice
        MASS
      ];
    })
  ];
}
