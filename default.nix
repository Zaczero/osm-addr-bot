{ pkgs ? import <nixpkgs> { } }:

let
  shell = import ./shell.nix;

  python-venv = pkgs.buildEnv {
    name = "python-venv";
    paths = [
      (pkgs.runCommand "python-venv" { } ''
        mkdir -p $out/lib
        cp -r "${./.venv/lib/python3.12/site-packages}"/* $out/lib
      '')
    ];
  };
in
with pkgs; dockerTools.buildLayeredImage {
  name = "docker.monicz.dev/osm-addr-bot";
  tag = "latest";

  contents = shell.buildInputs ++ [ python-venv ];

  extraCommands = ''
    mkdir app && cd app
    cp "${./.}"/*.py .
  '';

  config = {
    WorkingDir = "/app";
    Env = [
      "PYTHONPATH=${python-venv}/lib"
      "PYTHONUNBUFFERED=1"
      "PYTHONDONTWRITEBYTECODE=1"
      "TZ=UTC"
    ];
    Entrypoint = [ "python" "main.py" ];
    Cmd = [ ];
  };
}
