{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python311
    pipenv
  ];

  shellHook = ''
    export PIPENV_VENV_IN_PROJECT=1
    export PIPENV_VERBOSITY=-1
    [ ! -f ".venv/bin/activate" ] && pipenv install --deploy --ignore-pipfile --keep-outdated --dev
    exec pipenv shell --fancy
  '';
}
