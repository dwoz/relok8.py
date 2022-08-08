Create a relocatable python using pyenv and relok8.py

```sh
PYENV_ROOT=$(pwd) pyenv install 3.9.13
relok8.py --root=versions/3.9.13 --lib=versions/3.9.13/lib --log-level=warn
```

The `versions/3.9.13` directory now has a re-locatable python.

```sh
cp -R versions/3.9.13 ./python
./python/bin/python3 -m test
```
