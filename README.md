PyGob
=====

[![](https://travis-ci.org/mgeisler/pygob.svg?branch=master)][travis-ci]

PyGob is a libray for reading and writing [Go gob encoded][gob]
values. The gob format is a binary format used for storing and
transmitting Go data structures. The gob format can encode all Go
types:

* primitive types like `bool`, `int`, `float`, etc

* arrays and slices

* struct types


License
-------

PyGob is licensed under the MIT license.


Author
------

PyGob is maintained by Martin Geisler.


[travis-ci]: https://travis-ci.org/mgeisler/pygob
[gob]: https://golang.org/pkg/encoding/gob/
