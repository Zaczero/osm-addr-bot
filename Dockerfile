FROM nixos/nix

RUN nix-channel --add https://channels.nixos.org/nixos-23.05 nixpkgs && \
    nix-channel --update

WORKDIR /app

ENV DOCKER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIPENV_CLEAR=1

COPY Pipfile.lock shell.nix ./
RUN nix-shell --run "true"

COPY LICENSE Makefile *.py ./

ENTRYPOINT [ "nix-shell", "--run" ]
CMD [ "pipenv run python main.py" ]
