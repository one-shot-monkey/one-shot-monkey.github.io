.PHONY: img
img: ## Converts images from ~/pic/website/Raw into assets/img/
	@poetry shell
	@python scripts/get_images.py
	@python scripts/responsive_images.py

.PHONY: img_response
img_response: ## Converts images from ~/pic/website/Raw into assets/img/
	@poetry shell
	@python scripts/responsive_images.py

.PHONY: test
test: ## Run site on localhost
	@bundle exec jekyll serve

.PHONY: deploy
deploy: ## build and deploy site to 192.168.51.152
	@JEKYLL_ENV=production bundle exec jekyll b
#	@scp -ur _site/* blog:/var/www/localhost/htdocs
	@rsync -avz --delete _site/ blog:/var/www/localhost/htdocs
	@ssh inco@blog chmod 775 -R /var/www/localhost/htdocs


.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

