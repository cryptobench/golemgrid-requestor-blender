 
IMG   := phillipjensen/requestor
GITHUB_TAG := ${IMG}:${GITHUB_SHA}
 
build:
	@docker buildx create --use	
	@docker buildx build --platform=linux/arm64,linux/amd64 --push -t ${GITHUB_TAG} -t ${IMG}:latest .

 
login:
	@docker login -u ${DOCKER_USER} -p ${DOCKER_PASS}
	