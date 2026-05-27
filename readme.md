## Docker build
```
docker build --pull --platform linux/amd64 -t ast-reducer .
```

## Docker run reducer
```
docker run --rm \
  --platform linux/amd64 \
  -v "$PWD/queries/query1:/work" \
  -w /work \
  ast-reducer \
  --query original_test.sql \
  --test test.sh
```

## Run ALL queries with Docker
```
docker run --rm \
  --platform linux/amd64 \
  -v "$PWD/queries:/opt/reducer/queries" \
  --entrypoint /usr/bin/run-all-queries \
  ast-reducer
```

The batch script writes each reduced result to `queries/query*/query.sql`.
