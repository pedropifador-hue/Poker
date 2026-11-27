"""Bloqueio de rede para garantir execucao 100% offline.

Enquanto `rede_bloqueada()` estiver ativo, qualquer tentativa de abrir conexao
(socket, requests, urllib) gera RedeBloqueada. Os testes do simulador ativam esse
bloqueio automaticamente (simulador/tests/conftest.py).
"""

import contextlib
import socket


class RedeBloqueada(RuntimeError):
    pass


def _negar(*_args, **_kwargs):
    raise RedeBloqueada("Ambiente offline: conexao de rede bloqueada pelo simulador")


@contextlib.contextmanager
def rede_bloqueada():
    originais = (socket.socket.connect, socket.socket.connect_ex,
                 socket.create_connection, socket.getaddrinfo)
    socket.socket.connect = _negar
    socket.socket.connect_ex = _negar
    socket.create_connection = _negar
    socket.getaddrinfo = _negar
    try:
        yield
    finally:
        (socket.socket.connect, socket.socket.connect_ex,
         socket.create_connection, socket.getaddrinfo) = originais
