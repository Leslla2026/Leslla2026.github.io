FROM ruby:3.2

WORKDIR /site

COPY . .

RUN gem install bundler jekyll

EXPOSE 4000

CMD ["jekyll", "serve", "--host", "0.0.0.0", "--livereload"]
``
