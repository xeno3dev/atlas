{
  description = "atlas. tmux-free project switcher/launcher for developers.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        pythonEnv = pkgs.python313.withPackages (ps: [
          ps.typer
          ps.platformdirs
					ps.nuitka
        ]);
      in {
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "atlas";
          version = "0.2.0";
          src = ./.;

          nativeBuildInputs = [ pythonEnv pkgs.gcc pkgs.makeWrapper pkgs.autoPatchelfHook ];
					buildInputs = [ pkgs.zlib pkgs.stdenv.cc.cc.lib ];

          buildPhase = ''
            PYTHONPATH=src ${pythonEnv}/bin/python -m nuitka --standalone \
							--include-package=atlas \
              --output-dir=build -o atlas src/atlas/__main__.py
          '';

          installPhase = ''
            mkdir -p $out/lib/atlas
            cp -r build/__main__.dist/* $out/lib/atlas/
            makeWrapper $out/lib/atlas/atlas $out/bin/atlas
          '';

          meta = {
            description = "atlas. tmux-free project switcher/launcher for developers.";
            homepage = "https://github.com/xeno3ra/atlas";
            license = pkgs.lib.licenses.mit;
            mainProgram = "atlas";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [ pythonEnv pkgs.gcc pkgs.zlib pkgs.stdenv.cc.cc.lib ];
        };
      }
    );
}