PyScada SSE Extension
=====================

This is a extension for PyScada to support Server-Sent-Event requests.


What is Working
---------------

 - nothing is test


What is not Working/Missing
---------------------------

 - Test with huge traffic and clients
 - Documentation

Installation
------------

 - pip install pyscada-sse
 - add to `/etc/nginx/sites-enabled/pyscada.conf`

::

    listen   443 default_server ssl http2;
    listen [::]:443 ssl http2;

    ...

    location /events/ {
        proxy_pass http://localhost:7999;
    }

 - install `pushpin <https://pushpin.org/>`_ : `sudo apt install pushpin`
 - add to `/etc/pushpin/routes ` :

::

    *,path_beg=/events localhost:8000
    *,ssl=yes localhost:443
    * localhost:80

 - add to `settings.py` :

::

    INSTALLED_APPS = [
    "daphne",
    ...
    "django_eventstream",
    ]


Contribute
----------

 - Issue Tracker: https://github.com/pyscada/PyScada-SSE/issues
 - Source Code: https://github.com/pyscada/PyScada-SSE


License
-------

The project is licensed under the _GNU General Public License v3 (GPLv3)_.
-
