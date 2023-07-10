{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    gnumake
    python311
    pipenv
  ];

  shellHook = ''
    export PIPENV_VENV_IN_PROJECT=1
    export PIPENV_VERBOSITY=-1
    [ -v DOCKER ] && [ ! -f .venv/bin/activate ] && pipenv sync
    [ ! -v DOCKER ] && [ ! -f .venv/bin/activate ] && pipenv sync --dev
    [ ! -v DOCKER ] && exec pipenv shell --fancy
  '';
}
