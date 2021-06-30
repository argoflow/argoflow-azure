FROM node:alpine

RUN apk add --no-cache tini git \
    && yarn global add git-http-server \
    && adduser -D -g git git

WORKDIR /home/git/argoflow-azure.git

COPY --chown=1000:100 distribution  /home/git/argoflow-azure.git/distribution
COPY --chown=1000:100 secrets       /home/git/argoflow-azure.git/secrets

ENV GIT_USER="argoflow"
ENV GIT_EMAIL="argoflow@argoflow.ca"

RUN find . -name .gitignore -delete \
    && git config --global user.email "$GIT_EMAIL" \
    && git config --global user.namel "$GIT_NAME" \
    && git init \
    && git add . \
    && git commit -m 'Argoflow KIND' \
    && chown -R git .

USER git

EXPOSE 8080
ENTRYPOINT ["tini", "--", "git-http-server", "-p", "8080", "/home/git"]
