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
    [ ! -f ".venv/bin/activate" ] && pipenv sync --dev
    exec pipenv shell --fancy
  '';
}
