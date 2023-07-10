.PHONY: update

IMAGE_NAME=docker.monicz.pl/osm-addr-bot

update:
	docker buildx build -t $(IMAGE_NAME) --push .
