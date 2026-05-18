Docker build
```
docker build --platform linux/amd64 -t theosotr/sqlite3-reducer .
```

Docker run
```
docker run --rm \                                                
  --platform linux/amd64 \
  -v "$PWD/queries/query1:/work" \
  -w /work \
  theosotr/sqlite3-reducer \
  --query original_test.sql \
  --test test.sh
```