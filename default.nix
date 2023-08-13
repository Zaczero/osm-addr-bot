{ pkgs ? import <nixpkgs> { } }:

with pkgs; let
  shell = import ./shell.nix {
    inherit pkgs;
    isDocker = true;
  };

  python-venv = buildEnv {
    name = "python-venv";
    paths = [
      (runCommand "python-venv" { } ''
        mkdir -p $out/lib
        cp -r "${./.venv/lib/python3.11/site-packages}"/* $out/lib
      '')
    ];
  };
in
dockerTools.buildLayeredImage {
  name = "docker.monicz.pl/osm-addr-bot";
  tag = "latest";
  maxLayers = 10;

  contents = shell.buildInputs ++ [ python-venv ];

  extraCommands = ''
    mkdir app && cd app
    cp "${./.}"/LICENSE .
    cp "${./.}"/*.py .
    ${shell.shellHook}
  '';

  config = {
    WorkingDir = "/app";
    Env = [
      "PYTHONPATH=${python-venv}/lib"
      "PYTHONUNBUFFERED=1"
      "PYTHONDONTWRITEBYTECODE=1"
    ];
    Entrypoint = [ "python" "main.py" ];
    Cmd = [ ];
  };
}
