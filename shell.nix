let
  # Update packages with `nixpkgs-update` command
  pkgs = import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/a27871180d30ebee8aa6b11bf7fef8a52f024733.tar.gz") { };

  pythonLibs = with pkgs; [
    zlib.out
    stdenv.cc.cc.lib
  ];
  python' = with pkgs; (symlinkJoin {
    name = "python";
    paths = [ python313 ];
    buildInputs = [ makeWrapper ];
    postBuild = ''
      wrapProgram "$out/bin/python3.13" --prefix LD_LIBRARY_PATH : "${lib.makeLibraryPath pythonLibs}"
    '';
  });

  packages' = with pkgs; [
    python'
    uv

    (writeShellScriptBin "nixpkgs-update" ''
      set -e
      hash=$(
        curl --silent --location \
        https://prometheus.nixos.org/api/v1/query \
        -d "query=channel_revision{channel=\"nixpkgs-unstable\"}" | \
        grep --only-matching --extended-regexp "[0-9a-f]{40}")
      sed -i -E "s|/nixpkgs/archive/[0-9a-f]{40}\.tar\.gz|/nixpkgs/archive/$hash.tar.gz|" shell.nix
      echo "Nixpkgs updated to $hash"
    '')
  ];

  shell' = ''
    export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
    export PYTHONNOUSERSITE=1
    export PYTHONPATH=""
    export TZ=UTC

    current_python=$(readlink -e .venv/bin/python || echo "")
    current_python=''${current_python%/bin/*}
    [ "$current_python" != "${python'}" ] && rm -rf .venv/

    echo "Installing Python dependencies"
    export UV_COMPILE_BYTECODE=1
    export UV_PYTHON="${python'}/bin/python"
    uv sync --frozen

    echo "Activating Python virtual environment"
    source .venv/bin/activate

    if [ -f .env ]; then
      echo "Loading .env file"
      set -o allexport
      source .env set
      set +o allexport
    else
      echo "Skipped loading .env file (not found)"
    fi
  '';
in
pkgs.mkShellNoCC
{
  buildInputs = packages';
  shellHook = shell';
}
