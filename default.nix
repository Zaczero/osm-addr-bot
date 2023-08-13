{ pkgs ? import <nixpkgs> { } }:

let
  shell = import ./shell.nix {
    inherit pkgs;
    isDocker = true;
  };

  python-venv-lib = pkgs.buildEnv {
    name = "python-venv-lib";
    paths = [
      (pkgs.runCommand "python-venv-lib" { } ''
        mkdir -p $out/lib
        cp -r "${./.venv/lib/python3.11/site-packages}"/* $out/lib
      '')
    ];
  };
in
pkgs.dockerTools.buildLayeredImage {
  name = "docker.monicz.pl/osm-addr-bot";
  tag = "latest";
  maxLayers = 10;

  contents = shell.buildInputs ++ [ python-venv-lib ];

  extraCommands = ''
    mkdir app && cd app
    cp "${./.}"/LICENSE .
    cp "${./.}"/*.py .
    ${shell.shellHook}
  '';

  config = {
    WorkingDir = "/app";
    Env = [
      "PYTHONPATH=${python-venv-lib}/lib"
      "PYTHONUNBUFFERED=1"
      "PYTHONDONTWRITEBYTECODE=1"
    ];
    Entrypoint = [ "python" "main.py" ];
    Cmd = [ ];
  };
}
